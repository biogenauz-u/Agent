import base64
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.database.models import AuditLog, Task
from app.database.models.task import TaskPriority, TaskStatus
from app.database.session import DatabaseManager
from app.modules.tasks.exceptions import TaskConflictError, TaskNotFoundError
from app.modules.tasks.schemas import TaskCreate, TaskUpdate
from app.modules.tasks.service import TaskService

NOW = datetime(2026, 9, 24, 7, tzinfo=UTC)
TODAY = date(2026, 9, 24)


def key() -> SecretStr:
    return SecretStr(base64.urlsafe_b64encode(b"t" * 32).decode())


def manager(engine) -> DatabaseManager:
    database = DatabaseManager(Settings(_env_file=None))
    database._sessions = async_sessionmaker(engine, expire_on_commit=False)
    return database


def service(engine, reminder=None, calendar=None) -> TaskService:
    return TaskService(
        manager(engine), 42, key(), Settings(_env_file=None).timezone, 10,
        TaskPriority.NORMAL, 60, reminder, calendar, now=lambda: NOW
    )


def request(**values) -> TaskCreate:
    data = {"title": "Neurocit payment", "due_date": TODAY}
    data.update(values)
    return TaskCreate(**data)


def test_status_priority_enums_and_default() -> None:
    assert {item.value for item in TaskStatus} == {"TODO", "IN_PROGRESS", "DONE", "CANCELLED"}
    assert {item.value for item in TaskPriority} == {"LOW", "NORMAL", "HIGH", "URGENT"}
    assert request().priority == TaskPriority.NORMAL


def test_naive_due_datetime_rejected() -> None:
    with pytest.raises(ValidationError):
        request(due_at=datetime(2026, 9, 24, 15))  # noqa: DTZ001


async def test_create_encrypts_description_and_supports_date_only(engine) -> None:
    tasks = service(engine)
    view = await tasks.create_task(request(description="private task detail"))
    assert view.description == "private task detail"
    assert view.due_at is None and view.due_date == TODAY
    async with async_sessionmaker(engine)() as session:
        row = await session.scalar(select(Task).where(Task.id == view.id))
        assert row and b"private task detail" not in row.description_encrypted


async def test_timed_task_stores_utc(engine) -> None:
    due = datetime(2026, 9, 24, 15, tzinfo=Settings(_env_file=None).timezone)
    view = await service(engine).create_task(request(due_at=due))
    assert view.due_at == datetime(2026, 9, 24, 10, tzinfo=UTC)


async def test_today_tomorrow_and_open_order(engine) -> None:
    tasks = service(engine)
    today = await tasks.create_task(request(title="today"))
    tomorrow = await tasks.create_task(TaskCreate(title="tomorrow", due_date=TODAY + timedelta(days=1)))
    assert [item.id for item in await tasks.today()] == [today.id]
    assert [item.id for item in await tasks.tomorrow()] == [tomorrow.id]


async def test_overdue_excludes_today_done_and_cancelled(engine) -> None:
    tasks = service(engine)
    old = await tasks.create_task(TaskCreate(title="old", due_date=TODAY - timedelta(days=1)))
    timed = await tasks.create_task(request(title="timed", due_at=NOW - timedelta(minutes=1)))
    done = await tasks.create_task(TaskCreate(title="done", due_date=TODAY - timedelta(days=2)))
    deleted = await tasks.create_task(TaskCreate(title="deleted", due_date=TODAY - timedelta(days=2)))
    await tasks.complete_task(done.id)
    await tasks.delete_task(deleted.id)
    assert {item.id for item in await tasks.overdue()} == {old.id, timed.id}


async def test_completion_sets_timestamp_cancels_reminder_and_guards_repeat(engine) -> None:
    reminder = AsyncMock()
    tasks = service(engine, reminder)
    item = await tasks.create_task(request())
    async with tasks.database.session() as session:
        row = await session.get(Task, item.id)
        row.reminder_id = 77
    done = await tasks.complete_task(item.id)
    assert done.status == TaskStatus.DONE and done.completed_at == NOW
    reminder.cancel.assert_awaited_once_with(77)
    with pytest.raises(TaskConflictError):
        await tasks.complete_task(item.id)


async def test_edit_priority_and_audit_without_description(engine) -> None:
    tasks = service(engine)
    item = await tasks.create_task(request(description="SECRET DESCRIPTION"))
    updated = await tasks.update_task(item.id, TaskUpdate(title="Changed", priority=TaskPriority.URGENT))
    assert updated.title == "Changed" and updated.priority == TaskPriority.URGENT
    async with async_sessionmaker(engine)() as session:
        audits = list(await session.scalars(select(AuditLog)))
        assert "SECRET DESCRIPTION" not in repr([item.details for item in audits])


async def test_delete_soft_cancels_and_excludes(engine) -> None:
    tasks = service(engine)
    item = await tasks.create_task(request())
    await tasks.delete_task(item.id)
    assert await tasks.list_tasks() == []
    with pytest.raises(TaskNotFoundError):
        await tasks.get_task(item.id)


async def test_create_integrates_reminder_and_calendar_once(engine) -> None:
    reminder, calendar = AsyncMock(), AsyncMock()
    reminder.create.return_value, calendar.create.return_value = 7, "event-1"
    tasks = service(engine, reminder, calendar)
    due = datetime(2026, 9, 25, 15, tzinfo=Settings(_env_file=None).timezone)
    item = await tasks.create_task(TaskCreate(
        title="integrated", due_date=date(2026, 9, 25), due_at=due,
        reminder_enabled=True, calendar_sync=True,
    ))
    assert item.reminder_enabled and item.calendar_linked
    reminder.create.assert_awaited_once()
    calendar.create.assert_awaited_once()


async def test_edit_resyncs_integrations_without_duplicate(engine) -> None:
    reminder, calendar = AsyncMock(), AsyncMock()
    reminder.create.return_value, calendar.create.return_value = 7, "event-1"
    tasks = service(engine, reminder, calendar)
    due = datetime(2026, 9, 25, 15, tzinfo=Settings(_env_file=None).timezone)
    item = await tasks.create_task(TaskCreate(
        title="integrated", due_date=date(2026, 9, 25), due_at=due,
        reminder_enabled=True, calendar_sync=True,
    ))
    await tasks.update_task(item.id, TaskUpdate(title="updated"))
    reminder.reschedule.assert_awaited_once()
    calendar.update.assert_awaited_once()
    assert reminder.create.await_count == 1 and calendar.create.await_count == 1


async def test_carry_forward_updates_integrations(engine) -> None:
    reminder, calendar = AsyncMock(), AsyncMock()
    reminder.create.return_value, calendar.create.return_value = 7, "event-1"
    tasks = service(engine, reminder, calendar)
    due = datetime(2026, 9, 24, 15, tzinfo=Settings(_env_file=None).timezone)
    item = await tasks.create_task(TaskCreate(
        title="carry", due_date=TODAY, due_at=due, reminder_enabled=True, calendar_sync=True
    ))
    carried = (await tasks.carry_forward_tasks([item.id], TODAY + timedelta(days=1)))[0]
    assert carried.due_date == TODAY + timedelta(days=1)
    assert carried.due_at.astimezone(tasks.timezone).hour == 15
    reminder.reschedule.assert_awaited_once()
    calendar.update.assert_awaited_once()


async def test_daily_summary_and_unfinished(engine) -> None:
    tasks = service(engine)
    urgent = await tasks.create_task(request(title="urgent", priority=TaskPriority.URGENT))
    done = await tasks.create_task(request(title="done"))
    await tasks.complete_task(done.id)
    summary = await tasks.get_daily_summary(TODAY)
    assert summary.model_dump() == {"total": 2, "done": 1, "remaining": 1, "overdue": 0, "urgent": 1}
    assert [item.id for item in await tasks.list_unfinished_for_date(TODAY)] == [urgent.id]
