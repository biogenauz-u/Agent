from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.modules.email.schemas import EmailView


class TelegramEmailDelivery:
    def __init__(self, bot: Bot, owner_id: int) -> None:
        self.bot, self.owner_id = bot, owner_id

    async def send(self, email: EmailView) -> None:
        attachment = f"\n\n📎 {email.attachment_count} ta fayl" if email.attachment_count else ""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 To‘liq o‘qish", callback_data=f"email:read:{email.id}"), InlineKeyboardButton(text="✍️ Javob draft", callback_data=f"email:draft:{email.id}")],
            [InlineKeyboardButton(text="⏰ 10 daqiqada eslatish", callback_data=f"email:remind:10:{email.id}")],
        ])
        await self.bot.send_message(self.owner_id, f"📧 Yangi email\n\nKimdan: {email.from_name or email.from_address}\nMavzu: {email.subject}\n\nQisqacha:\n{email.summary[:1200]}{attachment}", reply_markup=keyboard)
