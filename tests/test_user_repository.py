from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.repository import UserRepository


async def test_create_and_lookup(session: AsyncSession) -> None:
    repository = UserRepository(session)
    user = await repository.create(2**40, first_name="Owner")
    assert user.id is not None
    assert user.is_active
    assert user.created_at.utcoffset() == timedelta(0)
    assert user.updated_at.tzinfo is not None
    assert await repository.get_by_id(user.id) is user
    assert await repository.get_by_telegram_user_id(2**40) is user
    assert await repository.get_by_telegram_user_id(42) is None
    await session.rollback()
    assert await repository.get_by_telegram_user_id(2**40) is None


async def test_unique_telegram_id(session: AsyncSession) -> None:
    repository = UserRepository(session)
    await repository.create(42)
    with pytest.raises(IntegrityError):
        await repository.create(42)
    await session.rollback()


async def test_update_last_seen(session: AsyncSession) -> None:
    repository = UserRepository(session)
    user = await repository.create(42)
    at = datetime(2026, 9, 23, 15, tzinfo=timezone(timedelta(hours=5)))
    assert await repository.update_last_seen(user.id, at)
    await session.refresh(user)
    assert user.last_seen_at == at.astimezone(UTC)
    assert user.last_seen_at.utcoffset() == timedelta(0)
    assert not await repository.update_last_seen(999)
    with pytest.raises(ValueError, match="Timezone-aware"):
        await repository.update_last_seen(user.id, datetime(2026, 1, 1))  # noqa: DTZ001
