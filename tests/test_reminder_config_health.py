from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError

from app.api.routes.health import snapshot
from app.core.application import ApplicationContext
from app.core.config import Settings
from app.modules.reminders.exceptions import ReminderConfigurationError


def settings(**values):
    defaults = {
        "DATABASE_URL": None,
        "REDIS_URL": None,
        "TELEGRAM_BOT_TOKEN": None,
        "TELEGRAM_OWNER_ID": None,
        "RUN_REMINDER_SCHEDULER": False,
    }
    return Settings(_env_file=None, **{**defaults, **values})


def test_reminder_settings_and_retry_validation() -> None:
    value = settings()
    assert value.reminder_default_offset_minutes == 10
    assert value.reminder_retry_delays == (60, 300, 900)
    with pytest.raises(ValidationError):
        settings(REMINDER_RETRY_DELAYS_SECONDS="60,secret")
    with pytest.raises(ValidationError):
        settings(REMINDER_MAX_ATTEMPTS=0)


async def test_scheduler_requires_telegram_mode_and_database() -> None:
    context = ApplicationContext(settings(RUN_REMINDER_SCHEDULER=True))
    with pytest.raises(ReminderConfigurationError, match="Telegram"):
        await context.start()
    context = ApplicationContext(
        settings(
            RUN_REMINDER_SCHEDULER=True,
            TELEGRAM_BOT_TOKEN="123456789:TEST_ONLY_FAKE_TOKEN_abc",
            TELEGRAM_OWNER_ID=42,
        ),
        telegram=True,
    )
    with patch("app.core.application.TelegramRuntime") as runtime:
        instance = runtime.return_value
        instance.prepare = AsyncMock()
        instance.close = AsyncMock()
        instance.bot = Mock()
        instance.context = Mock()
        with pytest.raises(ReminderConfigurationError, match="DATABASE_URL"):
            await context.start()


async def test_health_reports_scheduler_state() -> None:
    context = ApplicationContext(settings())
    await context.start()
    assert (await snapshot(context)).services.reminder_scheduler == "disabled"
    context.runtime.reminder_scheduler_required = True
    context.runtime.reminder_scheduler = "error"
    assert (await snapshot(context)).status == "error"
    await context.close()


async def test_lifecycle_starts_once_and_stops_scheduler_first() -> None:
    calls = []
    database = Mock(initialize=Mock(), dispose=AsyncMock(side_effect=lambda: calls.append("db")))
    calendar = Mock(close=AsyncMock(side_effect=lambda: calls.append("calendar")))
    telegram = Mock(
        prepare=AsyncMock(), close=AsyncMock(side_effect=lambda: calls.append("telegram"))
    )
    telegram.bot, telegram.context = Mock(), Mock()
    reminders = Mock(
        start=AsyncMock(), close=AsyncMock(side_effect=lambda: calls.append("reminders"))
    )
    reminders.service = Mock()
    finance = Mock(
        start=AsyncMock(), close=AsyncMock(side_effect=lambda: calls.append("finance"))
    )
    configured = settings(
        RUN_REMINDER_SCHEDULER=True,
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        TELEGRAM_BOT_TOKEN="123456789:TEST_ONLY_FAKE_TOKEN_abc",
        TELEGRAM_OWNER_ID=42,
        BOT_PIN="test-pin",
    )
    with (
        patch("app.core.application.DatabaseManager", return_value=database),
        patch("app.core.application.CalendarRuntime", return_value=calendar),
        patch("app.core.application.TelegramRuntime", return_value=telegram),
        patch("app.core.application.ReminderRuntime", return_value=reminders),
        patch("app.core.application.FinanceRuntime", return_value=finance),
    ):
        context = ApplicationContext(configured, telegram=True)
        await context.start()
        await context.start()
        reminders.start.assert_awaited_once()
        assert context.runtime.reminder_scheduler == "running"
        await context.close()
        assert calls == ["finance", "reminders", "telegram", "calendar", "db"]
