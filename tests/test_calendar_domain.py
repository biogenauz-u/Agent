from datetime import date, datetime
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.modules.audit.actions import AuditAction
from app.modules.calendar.exceptions import CalendarConflictError, CalendarError
from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventUpdate, TimeInterval
from app.modules.calendar.service import CalendarService
from app.modules.calendar.utils import day_range, event_view, free_intervals, parse_local

TZ = ZoneInfo("Asia/Tashkent")


def event(**overrides: object) -> CalendarEventCreate:
    values = {
        "title": "Meeting",
        "start": "2026-09-25T15:00:00+05:00",
        "end": "2026-09-25T16:00:00+05:00",
    }
    return CalendarEventCreate.model_validate({**values, **overrides})


def raw_event() -> dict:
    return {
        "id": "abc123",
        "etag": '"v1"',
        "summary": "Meeting",
        "start": {"dateTime": "2026-09-25T15:00:00+05:00"},
        "end": {"dateTime": "2026-09-25T16:00:00+05:00"},
    }


def test_defaults_and_payload() -> None:
    service = CalendarService(Mock(), Mock(), TZ)
    payload = service.payload(event())
    assert payload["start"] == {
        "dateTime": "2026-09-25T15:00:00+05:00",
        "timeZone": "Asia/Tashkent",
    }
    assert payload["reminders"] == {
        "useDefault": False,
        "overrides": [{"method": "popup", "minutes": 10}],
    }
    assert event(reminders=[1440, 60, 10]).reminders == [1440, 60, 10]


@pytest.mark.parametrize("values", [[0], [-1], [40321], [10, 10], [1, 2, 3, 4, 5, 6], [True]])
def test_reminders_rejected(values: list[int]) -> None:
    with pytest.raises(ValidationError):
        event(reminders=values)


def test_naive_and_reversed_rejected() -> None:
    with pytest.raises(ValidationError):
        event(start="2026-09-25T15:00:00")
    with pytest.raises(ValidationError):
        event(end="2026-09-25T14:00:00+05:00")


def test_local_boundaries_and_all_day() -> None:
    window = day_range(date(2026, 9, 25), TZ)
    assert window.start.isoformat() == "2026-09-25T00:00:00+05:00"
    assert window.end.isoformat() == "2026-09-26T00:00:00+05:00"
    item = event_view({"id": "all", "start": {"date": "2026-09-25"}, "end": {"date": "2026-09-26"}})
    assert item.all_day and item.start == date(2026, 9, 25)


def interval(start: int, end: int) -> TimeInterval:
    return TimeInterval(
        start=datetime(2026, 9, 25, start, tzinfo=TZ), end=datetime(2026, 9, 25, end, tzinfo=TZ)
    )


@pytest.mark.parametrize(
    ("busy", "expected"),
    [
        ([], [(9, 18)]),
        ([(10, 11)], [(9, 10), (11, 18)]),
        ([(10, 12), (11, 14)], [(9, 10), (14, 18)]),
        ([(10, 12), (12, 14)], [(9, 10), (14, 18)]),
        ([(0, 23)], []),
        ([(9, 18)], []),
        ([(7, 10), (17, 22)], [(10, 17)]),
    ],
)
def test_free_intervals(busy: list, expected: list) -> None:
    result = free_intervals(interval(9, 18), [interval(*pair) for pair in busy])
    assert [(item.start.hour, item.end.hour) for item in result] == expected


def test_dst_invalid_time_rejected() -> None:
    with pytest.raises(ValueError):
        parse_local("08.03.2026", "02:30", ZoneInfo("America/New_York"))


async def test_create_audits_safe_identifier() -> None:
    client, audit = Mock(), Mock()
    client.create_event = AsyncMock(return_value=raw_event())
    audit.record = AsyncMock()
    service = CalendarService(client, audit, TZ)
    created = await service.create_event(event(), "a" * 32)
    assert created.id == "abc123"
    assert client.create_event.call_args.args[0]["id"] == "a" * 32
    audit.record.assert_awaited_once_with(AuditAction.CALENDAR_EVENT_CREATED, "abc123")
    assert "token" not in str(audit.record.call_args)


async def test_today_tomorrow_and_upcoming_sorted(monkeypatch: pytest.MonkeyPatch) -> None:
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 25, 1, tzinfo=TZ).astimezone(tz)

    monkeypatch.setattr("app.modules.calendar.service.datetime", FixedDateTime)
    client = Mock()
    client.list_events = AsyncMock(return_value=[])
    service = CalendarService(client, Mock(), TZ)
    await service.get_today_events()
    assert client.list_events.call_args.args[:2] == (
        "2026-09-25T00:00:00+05:00",
        "2026-09-26T00:00:00+05:00",
    )
    await service.get_tomorrow_events()
    assert client.list_events.call_args.args[:2] == (
        "2026-09-26T00:00:00+05:00",
        "2026-09-27T00:00:00+05:00",
    )
    early = {**raw_event(), "id": "early", "start": {"dateTime": "2026-09-25T09:00:00+05:00"}}
    client.list_events.return_value = [raw_event(), early]
    assert [item.id for item in await service.list_upcoming_events()] == ["early", "abc123"]


async def test_update_refetches_and_only_changes_selected_fields() -> None:
    client = Mock(
        get_event=AsyncMock(return_value=raw_event()),
        update_event=AsyncMock(return_value=raw_event()),
    )
    audit = Mock(record=AsyncMock())
    service = CalendarService(client, audit, TZ)
    update = CalendarEventUpdate(**event().model_dump(), fields={"title"})
    await service.update_event("abc123", update, '"v1"')
    client.get_event.assert_awaited_once_with("abc123")
    client.update_event.assert_awaited_once_with("abc123", {"summary": "Meeting"}, '"v1"')
    audit.record.assert_awaited_once_with(AuditAction.CALENDAR_EVENT_UPDATED, "abc123")


async def test_stale_delete_and_recurring_changes_are_rejected() -> None:
    client = Mock(get_event=AsyncMock(return_value=raw_event()), delete_event=AsyncMock())
    service = CalendarService(client, Mock(record=AsyncMock()), TZ)
    with pytest.raises(CalendarConflictError):
        await service.delete_event("abc123", '"stale"')
    client.delete_event.assert_not_called()
    client.get_event.return_value = {**raw_event(), "recurringEventId": "series"}
    with pytest.raises(CalendarError):
        await service.delete_event("abc123", '"v1"')
    client.delete_event.assert_not_called()


async def test_free_busy_missing_calendar_is_not_fake_free_time() -> None:
    client = Mock(calendar_id="primary", free_busy=AsyncMock(return_value={"calendars": {}}))
    service = CalendarService(client, Mock(), TZ)
    with pytest.raises(CalendarError):
        await service.get_free_busy(interval(9, 18))
