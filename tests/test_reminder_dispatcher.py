from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.database.models import Reminder, ReminderStatus
from app.database.session import DatabaseManager
from app.modules.reminders.dispatcher import ReminderDispatcher
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.schemas import ReminderDeliveryResult
from app.modules.users.repository import UserRepository

NOW = datetime(2026, 9, 25, 10, tzinfo=UTC)


def database(engine):
    value = DatabaseManager(Settings(_env_file=None))
    value._sessions = async_sessionmaker(engine, expire_on_commit=False)
    return value


async def create_due(database, max_attempts=3, attempts=0):
    async with database.session() as session:
        user = await UserRepository(session).get_by_telegram_user_id(42)
        if not user:
            user = await UserRepository(session).create(42)
        return await ReminderRepository(session).create(
            Reminder(
                user_id=user.id,
                title="Due",
                remind_at=NOW - timedelta(minutes=1),
                max_attempts=max_attempts,
                attempt_count=attempts,
                deduplication_key=f"due-{max_attempts}-{attempts}",
            )
        )


async def test_delivery_success_marks_delivered(engine) -> None:
    db = database(engine)
    reminder = await create_due(db)
    dispatcher = ReminderDispatcher(
        db,
        Mock(deliver=AsyncMock(return_value=ReminderDeliveryResult(success=True))),
        Mock(record=AsyncMock()),
        (60,),
        now=lambda: NOW,
    )
    await dispatcher.dispatch(reminder.id)
    async with db.session() as session:
        stored = await session.get(Reminder, reminder.id)
        assert stored.status == ReminderStatus.DELIVERED
        assert stored.attempt_count == 1


async def test_failure_retries_then_fails(engine) -> None:
    db = database(engine)
    failed = ReminderDeliveryResult(success=False, failure_reason="TelegramNetworkError")
    scheduler = Mock()
    first = await create_due(db)
    dispatcher = ReminderDispatcher(
        db,
        Mock(deliver=AsyncMock(return_value=failed)),
        Mock(record=AsyncMock()),
        (60, 300),
        now=lambda: NOW,
    )
    dispatcher.scheduler = scheduler
    await dispatcher.dispatch(first.id)
    async with db.session() as session:
        stored = await session.get(Reminder, first.id)
        assert stored.status == ReminderStatus.PENDING
        assert stored.retry_at == NOW + timedelta(seconds=60)
    scheduler.schedule_id.assert_called_once_with(first.id, NOW + timedelta(seconds=60))
    last = await create_due(db, max_attempts=3, attempts=2)
    await dispatcher.dispatch(last.id)
    async with db.session() as session:
        stored = await session.get(Reminder, last.id)
        assert stored.status == ReminderStatus.FAILED
        assert stored.failure_reason == "TelegramNetworkError"
