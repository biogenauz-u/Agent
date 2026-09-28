from datetime import UTC, datetime

from app.bot.constants import LOCKED
from app.modules.personal_telegram.delivery import PersonalTelegramBotDelivery
from app.modules.personal_telegram.schemas import PersonalTelegramMessageView

from .conftest import Harness


async def test_full_read_is_blocked_while_locked(harness: Harness) -> None:
    await harness.send("/tg_read")
    assert harness.replies[-1] == LOCKED


async def test_incoming_preview_delivery_does_not_depend_on_lock(harness: Harness) -> None:
    delivery = PersonalTelegramBotDelivery(harness.bot, harness.context.owner_id)
    await delivery.send(
        PersonalTelegramMessageView(
            id=12,
            peer_id=700,
            sender_id=700,
            sender_display_name="Akmal",
            telegram_message_id=4,
            telegram_chat_id=700,
            direction="INCOMING",
            preview="Meeting tomorrow?",
            received_at=datetime.now(UTC),
            has_media=False,
        )
    )
    assert "Yangi Telegram xabar" in harness.replies[-1]
