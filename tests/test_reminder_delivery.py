from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

from app.database.models import Reminder
from app.modules.reminders.delivery import TelegramReminderDelivery
from app.modules.security.lock_service import LockService


def reminder(offset=None):
    return Reminder(
        id=1,
        user_id=999,
        title="Private title",
        message=None,
        remind_at=datetime(2026, 9, 25, 10, tzinfo=UTC),
        event_start_at=datetime(2026, 9, 25, 11, tzinfo=UTC) if offset else None,
        offset_minutes=offset,
        max_attempts=3,
        deduplication_key="key",
    )


async def test_delivery_targets_configured_owner_only() -> None:
    bot = Mock(send_message=AsyncMock())
    delivery = TelegramReminderDelivery(bot, 42, ZoneInfo("Asia/Tashkent"))
    assert (await delivery.deliver(reminder(10))).success
    bot.send_message.assert_awaited_once()
    assert bot.send_message.call_args.args[0] == 42
    assert "10 daqiqadan keyin" in bot.send_message.call_args.args[1]


async def test_delivery_failure_is_sanitized() -> None:
    bot = Mock(send_message=AsyncMock(side_effect=OSError("token=private")))
    result = await TelegramReminderDelivery(bot, 42, ZoneInfo("Asia/Tashkent")).deliver(reminder())
    assert not result.success
    assert result.failure_reason == "OSError"
    assert "private" not in result.model_dump_json()


async def test_scheduled_delivery_ignores_interactive_lock() -> None:
    lock = LockService()
    assert await lock.is_locked()
    bot = Mock(send_message=AsyncMock())
    result = await TelegramReminderDelivery(bot, 42, ZoneInfo("Asia/Tashkent")).deliver(reminder())
    assert result.success
    bot.send_message.assert_awaited_once()
