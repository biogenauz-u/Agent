from datetime import time

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.context import BotContext
from app.bot.keyboards.daily import carry_forward, daily_menu, period_settings
from app.modules.audit.actions import AuditAction
from app.modules.daily.runtime import DailyRuntime


class DailyFlow(StatesGroup):
    morning_time = State()
    evening_time = State()


def runtime(context: BotContext) -> DailyRuntime:
    if context.daily is None:
        raise RuntimeError("Daily automation PostgreSQL va Telegram rejimini talab qiladi.")
    return context.daily


async def overview(message: Message, app_context: BotContext) -> None:
    daily = runtime(app_context)
    settings = await daily.repository.get_or_create(
        daily.scheduler.default_morning, daily.scheduler.default_evening
    )
    await message.answer(
        f"Morning Briefing: {'ON' if settings.morning_enabled else 'OFF'} — {settings.morning_time:%H:%M}\n"
        f"Evening Summary: {'ON' if settings.evening_enabled else 'OFF'} — {settings.evening_time:%H:%M}\n"
        f"Timezone: {app_context.timezone}",
        reply_markup=daily_menu(),
    )


async def morning_now(message: Message, app_context: BotContext) -> None:
    await message.answer(await runtime(app_context).service.morning_text())


async def evening_now(message: Message, app_context: BotContext) -> None:
    daily = runtime(app_context)
    text, task_ids = await daily.service.evening_text()
    markup = None
    if task_ids:
        token = await daily.states.issue("daily_carry", {"task_ids": task_ids})
        markup = carry_forward(token)
    await message.answer(text, reply_markup=markup)


async def now_callback(callback: CallbackQuery, app_context: BotContext) -> None:
    if (callback.data or "").endswith("morning"):
        text = await runtime(app_context).service.morning_text()
        markup = None
    else:
        daily = runtime(app_context)
        text, task_ids = await daily.service.evening_text()
        markup = carry_forward(await daily.states.issue("daily_carry", {"task_ids": task_ids})) if task_ids else None
    await callback.answer()
    if callback.message:
        await callback.message.answer(text, reply_markup=markup)


async def settings_callback(callback: CallbackQuery, app_context: BotContext) -> None:
    kind = (callback.data or "").rsplit(":", 1)[-1]
    daily = runtime(app_context)
    settings = await daily.repository.get_or_create(daily.scheduler.default_morning, daily.scheduler.default_evening)
    enabled = settings.morning_enabled if kind == "morning" else settings.evening_enabled
    await callback.answer()
    if callback.message:
        await callback.message.answer(kind.title(), reply_markup=period_settings(kind, enabled))


async def toggle(callback: CallbackQuery, app_context: BotContext) -> None:
    _, action, kind = (callback.data or "").split(":")
    daily = runtime(app_context)
    enabled = action == "enable"
    if kind == "morning":
        await daily.repository.update_morning(enabled)
    else:
        await daily.repository.update_evening(enabled)
    await daily.scheduler.reload()
    await daily.service.audit(AuditAction.DAILY_SETTINGS_UPDATED, {"period": kind, "enabled": enabled})
    await callback.answer("Saqlandi")
    if callback.message:
        await callback.message.edit_text(f"{kind.title()}: {'ON' if enabled else 'OFF'}")


async def ask_time(callback: CallbackQuery, state: FSMContext) -> None:
    kind = (callback.data or "").rsplit(":", 1)[-1]
    await state.set_state(DailyFlow.morning_time if kind == "morning" else DailyFlow.evening_time)
    await callback.answer()
    if callback.message:
        await callback.message.answer("Vaqtni HH:MM formatida kiriting.")


async def save_time(message: Message, state: FSMContext, app_context: BotContext) -> None:
    try:
        value = time.fromisoformat((message.text or "").strip())
    except ValueError:
        await message.answer("Noto'g'ri format. HH:MM kiriting.")
        return
    daily = runtime(app_context)
    current = await state.get_state()
    kind = "morning" if current == DailyFlow.morning_time.state else "evening"
    if kind == "morning":
        await daily.repository.update_morning(True, value)
    else:
        await daily.repository.update_evening(True, value)
    await daily.scheduler.reload()
    await daily.service.audit(AuditAction.DAILY_SETTINGS_UPDATED, {"period": kind})
    await state.clear()
    await message.answer(f"{kind.title()} vaqti {value:%H:%M} ga o'zgartirildi.")


async def carry(callback: CallbackQuery, app_context: BotContext) -> None:
    token = (callback.data or "").rsplit(":", 1)[-1]
    if token == "select":
        await callback.answer()
        if callback.message:
            await callback.message.answer("Tanlab ko'chirish uchun /task_carry buyrug'idan foydalaning.")
        return
    data = await runtime(app_context).states.consume("daily_carry", token)
    if not data:
        await callback.answer("Tasdiq eskirgan yoki ishlatilgan.", show_alert=True)
        return
    count = await runtime(app_context).service.carry_forward(data["task_ids"])
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(f"{count} ta task ertangi kunga ko'chirildi.")


async def cancel(callback: CallbackQuery, app_context: BotContext) -> None:
    token = (callback.data or "").rsplit(":", 1)[-1]
    await runtime(app_context).states.consume("daily_carry", token)
    await callback.answer()
    if callback.message:
        await callback.message.edit_text("Tasklar ko'chirilmadi.")


def create_router() -> Router:
    router = Router(name="daily")
    router.message.register(overview, Command("daily", "daily_settings"), StateFilter(None))
    router.message.register(morning_now, Command("morning_now"), StateFilter(None))
    router.message.register(evening_now, Command("evening_now"), StateFilter(None))
    router.callback_query.register(now_callback, F.data.startswith("daily:now:"))
    router.callback_query.register(settings_callback, F.data.startswith("daily:settings:"))
    router.callback_query.register(toggle, F.data.startswith("daily:enable:") | F.data.startswith("daily:disable:"))
    router.callback_query.register(ask_time, F.data.startswith("daily:time:"))
    router.callback_query.register(carry, F.data.startswith("daily:carry:"))
    router.callback_query.register(cancel, F.data.startswith("daily:cancel:"))
    router.message.register(save_time, DailyFlow.morning_time)
    router.message.register(save_time, DailyFlow.evening_time)
    return router
