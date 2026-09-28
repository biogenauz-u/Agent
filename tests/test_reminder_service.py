from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.database.models import Reminder, ReminderStatus
from app.database.session import DatabaseManager
from app.modules.reminders.exceptions import ReminderNotFoundError, ReminderValidationError
from app.modules.reminders.schemas import CalendarReminderCreate, ReminderCreate
from app.modules.reminders.service import ReminderService

NOW = datetime(2026, 9, 25, 10, tzinfo=UTC)


def manager(engine) -> DatabaseManager:
    database = DatabaseManager(Settings(_env_file=None))
    database._sessions = async_sessionmaker(engine, expire_on_commit=False)
    return database


def service(engine) -> ReminderService:
    result = ReminderService(manager(engine), 42, 3, now=lambda: NOW)
    result.audit.record = Mock(return_value=None)

    async def audit(*args, **kwargs):
        return None

    result.audit.record = audit
    return result


async def test_standalone_creation_and_past_rejected(engine) -> None:
    reminders = service(engine)
    created = await reminders.create_standalone(
        ReminderCreate(title="Call broker", remind_at=NOW + timedelta(hours=1))
    )
    assert created.title == "Call broker"
    assert created.status == ReminderStatus.PENDING
    with pytest.raises(ReminderValidationError):
        await reminders.create_standalone(ReminderCreate(title="Past", remind_at=NOW))


async def test_calendar_multiple_offsets_default_and_duplicate(engine) -> None:
    reminders = service(engine)
    request = CalendarReminderCreate(
        external_calendar_event_id="event-1",
        title="Meeting",
        event_start_at=NOW + timedelta(days=2),
        offsets=[1440, 60, 10],
    )
    first = await reminders.create_for_calendar(request)
    second = await reminders.create_for_calendar(request)
    assert len(first) == len(second) == 3
    assert {row.offset_minutes for row in first} == {1440, 60, 10}
    assert {row.id for row in first} == {row.id for row in second}
    default = await reminders.create_for_calendar(
        CalendarReminderCreate(
            external_calendar_event_id="event-2",
            title="Default",
            event_start_at=NOW + timedelta(hours=2),
        )
    )
    assert [row.offset_minutes for row in default] == [10]


async def test_calendar_update_cancels_pending_keeps_delivered(engine) -> None:
    reminders = service(engine)
    original = await reminders.create_for_calendar(
        CalendarReminderCreate(
            external_calendar_event_id="event",
            title="Meeting",
            event_start_at=NOW + timedelta(days=2),
            offsets=[60, 10],
        )
    )
    async with reminders.database.session() as session:
        delivered = await session.get(Reminder, original[0].id)
        delivered.status = ReminderStatus.DELIVERED
    assert await reminders.sync_calendar("event", "Moved", NOW + timedelta(days=3), [60, 10])
    async with reminders.database.session() as session:
        rows = (
            await __import__("app.modules.reminders.repository", fromlist=["ReminderRepository"])
            .ReminderRepository(session)
            .list_for_calendar_event(1, "event")
        )
    assert sum(row.status == ReminderStatus.DELIVERED for row in rows) == 1
    assert sum(row.status == ReminderStatus.CANCELLED for row in rows) == 1
    assert sum(row.status == ReminderStatus.PENDING for row in rows) == 2


async def test_calendar_delete_cancels_only_pending(engine) -> None:
    reminders = service(engine)
    rows = await reminders.create_for_calendar(
        CalendarReminderCreate(
            external_calendar_event_id="event",
            title="Meeting",
            event_start_at=NOW + timedelta(days=1),
            offsets=[60, 10],
        )
    )
    assert await reminders.cancel_calendar("event")
    assert await reminders.list_upcoming() == []
    with pytest.raises(ReminderNotFoundError):
        await reminders.cancel(rows[0].id)


async def test_calendar_empty_offsets_disable_pending(engine) -> None:
    reminders = service(engine)
    await reminders.create_for_calendar(
        CalendarReminderCreate(
            external_calendar_event_id="event",
            title="Meeting",
            event_start_at=NOW + timedelta(days=1),
            offsets=[10],
        )
    )
    assert await reminders.sync_calendar("event", "Meeting", NOW + timedelta(days=1), [])
    assert await reminders.list_upcoming() == []


async def test_list_upcoming_and_scheduler_hooks(engine) -> None:
    reminders = service(engine)
    scheduler = Mock()
    reminders.scheduler = scheduler
    later = await reminders.create_standalone(
        ReminderCreate(title="Later", remind_at=NOW + timedelta(hours=2))
    )
    early = await reminders.create_standalone(
        ReminderCreate(title="Early", remind_at=NOW + timedelta(hours=1))
    )
    assert [row.id for row in await reminders.list_upcoming()] == [early.id, later.id]
    scheduler.schedule_id.assert_any_call(early.id, early.remind_at)
    await reminders.cancel(early.id)
    scheduler.remove_reminder.assert_called_once_with(early.id)


async def test_reschedule_updates_pending_and_scheduler(engine) -> None:
    reminders = service(engine)
    scheduler = Mock()
    reminders.scheduler = scheduler
    created = await reminders.create_standalone(
        ReminderCreate(title="Move me", remind_at=NOW + timedelta(hours=1))
    )
    moved = await reminders.reschedule(created.id, NOW + timedelta(hours=3))
    assert moved.remind_at == NOW + timedelta(hours=3)
    scheduler.schedule_id.assert_called_with(moved.id, moved.remind_at)


async def test_audit_payload_excludes_content_and_token(engine) -> None:
    reminders = ReminderService(manager(engine), 42, 3, now=lambda: NOW)
    reminders.audit.record = AsyncMock()
    await reminders.create_standalone(
        ReminderCreate(
            title="Sensitive reminder text",
            message="private body token=secret",
            remind_at=NOW + timedelta(hours=1),
        )
    )
    payload = repr(reminders.audit.record.call_args)
    assert "Sensitive reminder text" not in payload
    assert "private body" not in payload
    assert "token=secret" not in payload
