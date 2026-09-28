import logging

from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message, Update

logger = logging.getLogger(__name__)


def update_event(update: Update) -> Message | CallbackQuery | None:
    return update.message or update.callback_query


async def safe_reply(event: Message | CallbackQuery | None, text: str) -> None:
    try:
        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
    except TelegramAPIError:
        logger.warning("telegram_reply_failed")


async def delete_sensitive_message(message: Message) -> None:
    try:
        await message.delete()
    except TelegramAPIError:
        logger.warning("sensitive_message_delete_failed")
