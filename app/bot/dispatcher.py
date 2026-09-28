from aiogram import Dispatcher
from aiogram.fsm.storage.base import BaseEventIsolation, BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation

from app.bot.context import BotContext
from app.bot.errors import SafeErrorMiddleware
from app.bot.handlers import (
    assistant,
    calendar,
    common,
    daily,
    email,
    finance,
    menu,
    notebook,
    personal_telegram,
    reminders,
    security,
    tasks,
)
from app.bot.middlewares.lock_state import LockStateMiddleware
from app.bot.middlewares.owner_auth import OwnerAuthMiddleware


def create_dispatcher(
    context: BotContext,
    *,
    storage: BaseStorage | None = None,
    isolation: BaseEventIsolation | None = None,
) -> Dispatcher:
    """Authorize before allocating FSM state; isolate owner updates before lock checks."""
    dispatcher = Dispatcher(
        storage=storage if storage is not None else MemoryStorage(),
        events_isolation=isolation if isolation is not None else SimpleEventIsolation(),
        disable_fsm=True,
        app_context=context,
    )
    dispatcher.update.outer_middleware(SafeErrorMiddleware(context))
    dispatcher.update.outer_middleware(OwnerAuthMiddleware(context))
    dispatcher.update.outer_middleware(dispatcher.fsm)
    if context.session_lock_enabled:
        dispatcher.update.outer_middleware(LockStateMiddleware(context))
        dispatcher.include_router(security.create_router())
    dispatcher.include_routers(
        common.create_router(),
        reminders.create_router(),
        email.create_router(),
        personal_telegram.create_router(),
        finance.create_router(),
        notebook.create_router(),
        tasks.create_router(),
        daily.create_router(),
        calendar.create_router(),
        menu.create_router(),
        assistant.create_router(),
    )
    return dispatcher
