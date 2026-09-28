from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.constants import COMMANDS, HOME, MODULE_LABELS
from app.bot.context import BotContext
from app.bot.keyboards.main_menu import main_menu


async def start(message: Message, app_context: BotContext) -> None:
    user = message.from_user
    if user is not None:
        await app_context.persistence.synchronize(
            user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
    if app_context.session_lock_enabled and await app_context.security.lock_state.is_locked():
        await message.answer(
            "👋 Personal AI Assistant ishga tushdi.\n\n"
            "🔐 Tizim hozir qulflangan.\nOchish uchun /unlock buyrug‘idan foydalaning."
        )
    else:
        await message.answer(
            "👋 Personal AI Assistant ishga tushdi.\n\nTizim tayyor.\n\n"
            + "\n".join(MODULE_LABELS),
            reply_markup=main_menu(include_lock=app_context.session_lock_enabled),
        )


async def help_command(message: Message, app_context: BotContext) -> None:
    commands = (
        COMMANDS.items()
        if app_context.session_lock_enabled
        else ((name, label) for name, label in COMMANDS.items() if name not in {"lock", "unlock"})
    )
    await message.answer("\n".join(f"/{name} - {label}" for name, label in commands))


async def status(message: Message, app_context: BotContext) -> None:
    session = (
        "Locked" if await app_context.security.lock_state.is_locked() else "Unlocked"
    ) if app_context.session_lock_enabled else "Disabled"
    database = await app_context.persistence.status()
    await message.answer(
        "✅ System status\n\nTelegram Bot: Online\nAuthorization: Owner verified\n"
        f"Session: {session}\nTimezone: {app_context.timezone}\nDatabase: {database}"
    )


async def identity(message: Message, app_context: BotContext) -> None:
    await message.answer(f"Telegram User ID: {app_context.owner_id}")


def create_router() -> Router:
    router = Router(name="common")
    router.message.register(start, Command("start"))
    router.message.register(start, F.text == HOME)
    router.message.register(help_command, Command("help"))
    router.message.register(status, Command("status"))
    router.message.register(identity, Command("id"))
    return router
