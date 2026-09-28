from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.bot.persistence import BotPersistence
from app.database.models import AuditLog, User
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService


async def test_owner_profile_upsert(engine: AsyncEngine) -> None:
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions.begin() as session:
        service = UserService(UserRepository(session))
        first = await service.synchronize(42, username="first", first_name="Test", last_name=None)
        second = await service.synchronize(
            42, username=None, first_name="Updated", last_name="Owner"
        )
        assert first.id == second.id
    async with sessions() as session:
        user = await UserRepository(session).get_by_telegram_user_id(42)
        assert user.telegram_username is None
        assert user.first_name == "Updated"
        assert user.last_seen_at.tzinfo is not None
        assert await session.scalar(select(func.count()).select_from(User)) == 1


async def test_facade_persists_audit(engine: AsyncEngine) -> None:
    database = Mock(spec=DatabaseManager)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    database.session = sessions.begin
    facade = BotPersistence(database)
    assert await facade.synchronize(42, username=None, first_name="Owner", last_name=None)
    assert await facade.audit(AuditAction.COMMAND_RECEIVED, 42, "start")
    async with sessions() as session:
        event = await session.scalar(select(AuditLog))
        assert event.user_id is not None
        assert event.details == {"telegram_user_id": 42, "command": "start"}


async def test_unconfigured_not_silent(caplog: pytest.LogCaptureFixture) -> None:
    facade = BotPersistence()
    assert not await facade.audit(AuditAction.BOT_STARTED)
    assert "not_persisted" in caplog.text
    assert await facade.status() == "Not configured"


async def test_connection_outage_and_programming_error(caplog: pytest.LogCaptureFixture) -> None:
    database = Mock(spec=DatabaseManager)

    @asynccontextmanager
    async def unavailable() -> AsyncIterator[AsyncSession]:
        raise OSError("test-sensitive-connection-data")
        yield  # pragma: no cover

    database.session = unavailable
    facade = BotPersistence(database)
    assert not await facade.audit(AuditAction.BOT_STARTED)
    assert not await facade.synchronize(42, username=None, first_name="Owner", last_name=None)
    assert "test-sensitive" not in caplog.text
    database.session = Mock(side_effect=TypeError("programming bug"))
    with pytest.raises(TypeError):
        await facade.audit(AuditAction.BOT_STARTED)


async def test_status_checks_real_helper() -> None:
    database = Mock(spec=DatabaseManager)
    facade = BotPersistence(database)
    with patch("app.bot.persistence.check_database_health", new=AsyncMock(return_value=False)):
        assert await facade.status() == "Unavailable"
    with patch("app.bot.persistence.check_database_health", new=AsyncMock(return_value=True)):
        assert await facade.status() == "Connected"
