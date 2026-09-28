import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.bot.constants import DENIED
from app.bot.context import BotContext
from app.bot.transport import safe_reply, update_event
from app.core.logging import report_error

logger = logging.getLogger(__name__)


class SafeErrorMiddleware(BaseMiddleware):
    """Last-resort boundary: safe stack locations, error ID and fail-closed lock state."""

    def __init__(self, context: BotContext) -> None:
        self.context = context

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as error:  # noqa: BLE001 - central transport error boundary
            error_id = report_error(logger, error)
            try:
                if self.context.session_lock_enabled:
                    await self.context.security.lock()
                if state := data.get("state"):
                    await state.clear()
            except Exception as cleanup_error:  # noqa: BLE001 - Redis may also be unavailable
                report_error(logger, cleanup_error)
            incoming = update_event(event) if isinstance(event, Update) else None
            text = (
                f"⚠️ Xatolik yuz berdi.\n\nError ID: {error_id}"
                if data.get("owner_authorized")
                else DENIED
            )
            await safe_reply(incoming, text)
            return None
