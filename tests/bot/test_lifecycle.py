from unittest.mock import AsyncMock, Mock

import pytest
from aiogram import Bot, Dispatcher

from app.bot import lifecycle, run
from app.core import application
from app.core.config import Settings
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction

from .conftest import TEST_TOKEN, OfflineSession


async def test_polling_failure_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
    pin_hash: str,
) -> None:
    api = OfflineSession()
    bot = Bot(TEST_TOKEN, session=api)
    settings = Settings(
        _env_file=None,
        TELEGRAM_OWNER_ID=42,
        TELEGRAM_BOT_TOKEN=TEST_TOKEN,
        BOT_PIN_HASH=pin_hash,
        DATABASE_URL=None,
    )
    monkeypatch.setattr(run, "get_settings", lambda: settings)
    monkeypatch.setattr(run, "configure_logging", lambda level: None)
    monkeypatch.setattr(lifecycle, "create_bot", lambda settings: bot)
    monkeypatch.setattr(
        Dispatcher, "start_polling", AsyncMock(side_effect=RuntimeError("test stop"))
    )
    with pytest.raises(RuntimeError, match="test stop"):
        await run.main()
    assert api.closed


async def test_registration_failure_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
    pin_hash: str,
) -> None:
    api = OfflineSession()
    bot = Bot(TEST_TOKEN, session=api)
    settings = Settings(
        _env_file=None,
        TELEGRAM_OWNER_ID=42,
        TELEGRAM_BOT_TOKEN=TEST_TOKEN,
        BOT_PIN_HASH=pin_hash,
        DATABASE_URL=None,
    )
    monkeypatch.setattr(run, "get_settings", lambda: settings)
    monkeypatch.setattr(run, "configure_logging", lambda level: None)
    monkeypatch.setattr(lifecycle, "create_bot", lambda settings: bot)
    monkeypatch.setattr(bot, "set_my_commands", AsyncMock(side_effect=RuntimeError("test stop")))
    with pytest.raises(RuntimeError, match="test stop"):
        await run.main()
    assert api.closed


async def test_polling_shutdown_disposes_database(
    monkeypatch: pytest.MonkeyPatch,
    pin_hash: str,
) -> None:
    api = OfflineSession()
    bot = Bot(TEST_TOKEN, session=api)
    settings = Settings(
        _env_file=None,
        TELEGRAM_OWNER_ID=42,
        TELEGRAM_BOT_TOKEN=TEST_TOKEN,
        BOT_PIN_HASH=pin_hash,
        DATABASE_URL="postgresql+asyncpg://localhost/test_only",
    )
    database = Mock(spec=DatabaseManager)
    database.dispose = AsyncMock()
    persistence = Mock()
    persistence.audit = AsyncMock(return_value=True)
    finance = Mock(start=AsyncMock(), close=AsyncMock())
    monkeypatch.setattr(run, "get_settings", lambda: settings)
    monkeypatch.setattr(run, "configure_logging", lambda level: None)
    monkeypatch.setattr(lifecycle, "create_bot", lambda settings: bot)
    monkeypatch.setattr(application, "DatabaseManager", lambda settings: database)
    monkeypatch.setattr(application, "BotPersistence", lambda database: persistence)
    monkeypatch.setattr(application, "FinanceRuntime", lambda *args: finance)
    monkeypatch.setattr(Dispatcher, "start_polling", AsyncMock(return_value=None))
    await run.main()
    database.initialize.assert_called_once()
    database.dispose.assert_awaited_once()
    finance.start.assert_awaited_once()
    finance.close.assert_awaited_once()
    persistence.audit.assert_any_await(AuditAction.BOT_STARTED)
    persistence.audit.assert_any_await(AuditAction.BOT_STOPPED)
    assert api.closed
