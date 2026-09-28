import subprocess
import sys
from unittest.mock import patch

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from sqlalchemy.schema import CreateTable

from app.core.config import Settings
from app.core.exceptions import DatabaseConfigurationError
from app.database.health import check_database_health
from app.database.models import AuditLog, Reminder, User
from app.database.session import DatabaseManager, database_url
from app.modules.users.repository import UserRepository


def test_import_and_initialization_without_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    code = (
        "from unittest.mock import patch\n"
        "with patch('sqlalchemy.ext.asyncio.create_async_engine') as create:\n"
        "    import app.database.models\n"
        "    import app.database.session\n"
        "    create.assert_not_called()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, timeout=15, check=False
    )
    assert result.returncode == 0
    manager = DatabaseManager(Settings(_env_file=None, DATABASE_URL=None))
    with pytest.raises(DatabaseConfigurationError, match="DATABASE_URL is not configured"):
        manager.initialize()


@pytest.mark.parametrize("url", ["not-a-url", "sqlite:///db", "postgresql+asyncpg://host"])
def test_invalid_url_redacted(url: str) -> None:
    with pytest.raises(DatabaseConfigurationError) as caught:
        database_url(Settings(_env_file=None, DATABASE_URL=url))
    assert url not in str(caught.value)


async def test_lifecycle_and_transactions(engine: AsyncEngine) -> None:
    manager = DatabaseManager(Settings(_env_file=None, DATABASE_URL=None))
    with (
        patch("app.database.session.database_url"),
        patch("app.database.session.create_async_engine", return_value=engine) as create,
    ):
        manager.initialize()
        manager.initialize()
        create.assert_called_once()
    async with manager.session() as session:
        await UserRepository(session).create(42)
    with pytest.raises(RuntimeError):
        async with manager.session() as session:
            await UserRepository(session).create(43)
            raise RuntimeError("rollback")
    async with async_sessionmaker(engine)() as session:
        assert await UserRepository(session).get_by_telegram_user_id(42) is not None
        assert await UserRepository(session).get_by_telegram_user_id(43) is None
    await manager.dispose()
    await manager.dispose()
    with pytest.raises(DatabaseConfigurationError):
        _ = manager.engine


async def test_health(engine: AsyncEngine) -> None:
    assert await check_database_health(engine)
    with patch.object(
        engine.sync_engine,
        "connect",
        side_effect=OperationalError("SELECT 1", {}, Exception("sensitive")),
    ):
        assert not await check_database_health(engine)


async def test_dispose_before_initialize() -> None:
    manager = DatabaseManager(Settings(_env_file=None, DATABASE_URL=None))
    await manager.dispose()
    with pytest.raises(DatabaseConfigurationError):
        async with manager.session():
            pass


def test_postgres_schema() -> None:
    dialect = postgresql.dialect()
    user_sql = str(CreateTable(User.__table__).compile(dialect=dialect))
    audit_sql = str(CreateTable(AuditLog.__table__).compile(dialect=dialect))
    reminder_sql = str(CreateTable(Reminder.__table__).compile(dialect=dialect))
    assert "BIGSERIAL" in user_sql
    assert "UNIQUE (telegram_user_id)" in user_sql
    assert "JSONB" in audit_sql
    assert "TIMESTAMP WITH TIME ZONE" in audit_sql
    assert "ON DELETE SET NULL" in audit_sql
    assert "deduplication_key" in reminder_sql
    assert "UNIQUE (deduplication_key)" in reminder_sql
    assert "TIMESTAMP WITH TIME ZONE" in reminder_sql
    assert "ON DELETE CASCADE" in reminder_sql
