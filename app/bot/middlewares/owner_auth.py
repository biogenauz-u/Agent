from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from app.bot.constants import DENIED
from app.bot.context import BotContext
from app.bot.transport import safe_reply, update_event
from app.core.exceptions import TelegramConfigurationError
from app.modules.audit.actions import AuditAction


class OwnerAuthMiddleware(BaseMiddleware):
    """Authorize only supported updates from the owner in their own private chat."""

    def __init__(self, context: BotContext) -> None:
        if not context.owner_id or context.owner_id <= 0:
            raise TelegramConfigurationError("TELEGRAM_OWNER_ID is not configured.")
        self.context = context

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        incoming = update_event(event) if isinstance(event, Update) else None
        user = incoming.from_user if incoming is not None else None
        message = incoming.message if isinstance(incoming, CallbackQuery) else incoming
        authorized = (
            user is not None
            and not user.is_bot
            and user.id == self.context.owner_id
            and isinstance(message, Message)
            and message.chat.type == "private"
            and message.chat.id == self.context.owner_id
            and message.sender_chat is None
            and message.business_connection_id is None
        )
        if not authorized:
            await safe_reply(incoming, DENIED)
            await self.context.persistence.audit(
                AuditAction.UNAUTHORIZED_ACCESS, user.id if user else None
            )
            return None
        data["owner_authorized"] = True
        return await handler(event, data)
