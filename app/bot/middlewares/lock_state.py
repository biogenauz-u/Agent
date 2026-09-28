from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update

from app.bot.constants import LOCK, LOCKED, LOCKED_ALLOWED_COMMANDS, command_name
from app.bot.context import BotContext
from app.bot.states import UnlockFlow
from app.bot.transport import safe_reply, update_event
from app.modules.audit.actions import AuditAction


class LockStateMiddleware(BaseMiddleware):
    def __init__(self, context: BotContext) -> None:
        self.context = context

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        incoming = update_event(event) if isinstance(event, Update) else None
        text = incoming.text if isinstance(incoming, Message) else None
        command = command_name(text)
        waiting = data.get("raw_state") == UnlockFlow.waiting_for_pin.state
        # Only the dedicated FSM handler may receive non-command PIN input.
        pin_input = waiting and isinstance(incoming, Message) and command is None
        if not pin_input:
            await self.context.persistence.audit(
                AuditAction.COMMAND_RECEIVED if command else AuditAction.AUTHORIZED_ACCESS,
                self.context.owner_id,
                command,
            )
        permitted = command in LOCKED_ALLOWED_COMMANDS or text == LOCK or pin_input
        if await self.context.security.lock_state.is_locked() and not permitted:
            await safe_reply(incoming, LOCKED)
            return None
        return await handler(event, data)
