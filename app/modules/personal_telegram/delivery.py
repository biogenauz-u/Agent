from aiogram import Bot

from app.bot.keyboards.personal_telegram import incoming_message_actions
from app.modules.personal_telegram.schemas import PersonalTelegramMessageView


class PersonalTelegramBotDelivery:
    """Incoming previews may be delivered while locked; callbacks remain lock-protected."""

    def __init__(self, bot: Bot, owner_id: int) -> None:
        self.bot, self.owner_id = bot, owner_id

    async def send(self, message: PersonalTelegramMessageView) -> None:
        media = f"\n📎 {message.media_type}" if message.has_media else ""
        preview = message.preview or "(matnsiz xabar)"
        await self.bot.send_message(
            self.owner_id,
            f"💬 Yangi Telegram xabar\n\nKimdan: {message.sender_display_name}\n\n“{preview}”{media}",
            reply_markup=incoming_message_actions(message.id),
        )
