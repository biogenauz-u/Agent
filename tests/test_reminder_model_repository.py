from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Reminder, ReminderStatus
from app.modules.reminders.repository import ReminderRepository
from app.modules.users.repository import UserRepository

NOW = datetime(2026, 9, 25, 10, tzinfo=UTC)


def row(user_id: int, key: str = "key", **values) -> Reminder:
    defaults = {
        "user_id": user_id,
        "title": "Test",
        "remind_at": NOW + timedelta(hours=1),
        "max_attempts": 3,
        "deduplication_key": key,
    }
    return Reminder(**{**defaults, **values})


async def test_model_creation_utc_and_defaults(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    reminder = await ReminderRepository(session).create(row(user.id))
    await session.commit()
    assert reminder.status == ReminderStatus.PENDING
    assert reminder.remind_at == NOW + timedelta(hours=1)
    assert reminder.attempt_count == 0


async def test_model_rejects_naive_datetime(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    with pytest.raises((StatementError, ValueError)):
        await ReminderRepository(session).create(
            Reminder(
                user_id=user.id,
                title="Test",
                remind_at=datetime(2026, 9, 25, 11),  # noqa: DTZ001
                max_attempts=3,
                deduplication_key="naive",
            )
        )


async def test_deduplication_unique(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    await ReminderRepository(session).create(row(user.id))
    with pytest.raises(IntegrityError):
        await ReminderRepository(session).create(row(user.id))


async def test_claim_is_atomic_and_cancel_preserves_row(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    reminder = await ReminderRepository(session).create(
        row(user.id, remind_at=NOW - timedelta(minutes=1))
    )
    first = await ReminderRepository(session).claim(reminder.id, NOW)
    second = await ReminderRepository(session).claim(reminder.id, NOW)
    assert first is not None and first.attempt_count == 1
    assert second is None
    await session.rollback()
    user = await UserRepository(session).create(42)
    reminder = await ReminderRepository(session).create(row(user.id, "cancel"))
    assert await ReminderRepository(session).cancel(reminder.id, user.id, NOW)
    stored = await session.scalar(select(Reminder).where(Reminder.id == reminder.id))
    assert stored is not None and stored.status == ReminderStatus.CANCELLED
    assert stored.cancelled_at == NOW


async def test_stale_processing_recovery(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    reminder = await ReminderRepository(session).create(
        row(
            user.id,
            status=ReminderStatus.PROCESSING,
            processing_started_at=NOW - timedelta(minutes=20),
        )
    )
    ids, failed = await ReminderRepository(session).recover_stale(NOW - timedelta(minutes=10), NOW)
    assert ids == [reminder.id]
    assert failed == []
    await session.refresh(reminder)
    assert reminder.status == ReminderStatus.PENDING and reminder.retry_at == NOW
