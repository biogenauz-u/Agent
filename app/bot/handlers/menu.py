from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.constants import MODULE_LABELS, PLACEHOLDER
from app.bot.keyboards.main_menu import main_menu


async def menu(message: Message) -> None:
    await message.answer("Menyu", reply_markup=main_menu())


async def module_placeholder(message: Message) -> None:
    await message.answer(PLACEHOLDER)


async def callback_placeholder(callback: CallbackQuery) -> None:
    await callback.answer(PLACEHOLDER)


def create_router() -> Router:
    router = Router(name="menu")
    router.message.register(menu, Command("menu"))
    router.message.register(module_placeholder, F.text.in_(MODULE_LABELS))
    router.callback_query.register(callback_placeholder)
    return router
