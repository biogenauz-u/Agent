from datetime import datetime
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventUpdate
from app.modules.calendar.service import CalendarService

TZ = ZoneInfo("Asia/Tashkent")


def raw():
    return {
        "id": "event",
        "etag": '"v1"',
        "summary": "Meeting",
        "start": {"dateTime": "2026-09-25T15:00:00+05:00"},
        "end": {"dateTime": "2026-09-25T16:00:00+05:00"},
    }


def event():
    return CalendarEventCreate(
        title="Meeting",
        start="2026-09-25T15:00:00+05:00",
        end="2026-09-25T16:00:00+05:00",
        reminders=[60, 10],
    )


async def test_create_syncs_after_google_success() -> None:
    sequence = []
    client = Mock(
        create_event=AsyncMock(side_effect=lambda payload: sequence.append("google") or raw())
    )
    sync = Mock(
        sync_calendar=AsyncMock(side_effect=lambda *args: sequence.append("reminders") or True)
    )
    service = CalendarService(client, Mock(record=AsyncMock()), TZ, sync)
    result = await service.create_event(event(), "a" * 32)
    assert sequence == ["google", "reminders"]
    sync.sync_calendar.assert_awaited_once_with(
        "event", "Meeting", datetime.fromisoformat("2026-09-25T15:00:00+05:00"), [60, 10]
    )
    assert not result.reminder_warning


async def test_sync_failure_warns_without_repeating_google() -> None:
    client = Mock(create_event=AsyncMock(return_value=raw()))
    sync = Mock(sync_calendar=AsyncMock(return_value=False))
    result = await CalendarService(client, Mock(record=AsyncMock()), TZ, sync).create_event(
        event(), "a" * 32
    )
    assert result.reminder_warning
    client.create_event.assert_awaited_once()


async def test_update_syncs_and_delete_cancels() -> None:
    client = Mock(
        get_event=AsyncMock(return_value=raw()),
        update_event=AsyncMock(return_value=raw()),
        delete_event=AsyncMock(),
    )
    sync = Mock(
        sync_calendar=AsyncMock(return_value=True), cancel_calendar=AsyncMock(return_value=True)
    )
    service = CalendarService(client, Mock(record=AsyncMock()), TZ, sync)
    update = CalendarEventUpdate(**event().model_dump(), fields={"start", "end"})
    await service.update_event("event", update, '"v1"')
    sync.sync_calendar.assert_awaited_once_with(
        "event", "Meeting", datetime.fromisoformat("2026-09-25T15:00:00+05:00"), None
    )
    assert await service.delete_event("event", '"v1"')
    sync.cancel_calendar.assert_awaited_once_with("event")
