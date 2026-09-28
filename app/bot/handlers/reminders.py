from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.context import BotContext
from app.bot.keyboards.reminders import confirmation
from app.modules.calendar.utils import parse_local
from app.modules.reminders.exceptions import ReminderError
from app.modules.reminders.runtime import ReminderRuntime


class ReminderFlow(StatesGroup):
    text = State()
    date = State()
    time = State()
    select = State()
    confirm = State()


def runtime(context: BotContext) -> ReminderRuntime:
    if context.reminders is None:
        raise ReminderError(
            "Reminder scheduler disabled. PostgreSQL va RUN_REMINDER_SCHEDULER ni sozlang."
        )
    return context.reminders


async def send(message: Message, text: str, **kwargs: Any) -> None:
    await message.answer(text, parse_mode=None, **kwargs)


async def reset(state: FSMContext, reminders: ReminderRuntime) -> None:
    data = await state.get_data()
    if data.get("action"):
        await reminders.actions.cancel_action(data["action"])
    await state.clear()


async def start_create(message: Message, state: FSMContext, app_context: BotContext) -> None:
    reminders = runtime(app_context)
    await reset(state, reminders)
    await state.set_state(ReminderFlow.text)
    await send(message, "Nimani eslatay? Bekor qilish: /cancel")


async def input_step(message: Message, state: FSMContext, app_context: BotContext) -> None:
    reminders = runtime(app_context)
    current, data = await state.get_state(), await state.get_data()
    text = (message.text or "").strip()
    try:
        if current == ReminderFlow.text.state:
            if not 1 <= len(text) <= 200:
                raise ValueError
            await state.update_data(title=text)
            await state.set_state(ReminderFlow.date)
            await send(message, "Sanani kiriting: DD.MM.YYYY")
        elif current == ReminderFlow.date.state:
            parse_local(text, "00:00", reminders.timezone)
            await state.update_data(day=text)
            await state.set_state(ReminderFlow.time)
            await send(message, "Vaqt: HH:MM")
        elif current == ReminderFlow.time.state:
            remind_at = parse_local(data["day"], text, reminders.timezone)
            payload = {"title": data["title"], "remind_at": remind_at.isoformat()}
            token = await reminders.actions.prepare("create", payload)
            await state.set_data({"action": token})
            await state.set_state(ReminderFlow.confirm)
            await send(
                message,
                f"⏰ Reminder\n\n{data['title']}\n{remind_at:%d.%m.%Y %H:%M}\n\nSaqlansinmi?",
                reply_markup=confirmation(token),
            )
        elif current == ReminderFlow.select.state:
            rows = data["reminders"]
            index = int(text) - 1
            if index < 0 or index >= len(rows):
                raise ValueError
            token = await reminders.actions.prepare("cancel", {"id": rows[index]["id"]})
            await state.set_data({"action": token})
            await state.set_state(ReminderFlow.confirm)
            await send(
                message,
                f"{rows[index]['title']} bekor qilinsinmi?",
                reply_markup=confirmation(token),
            )
    except ValueError:
        await send(message, "Format yoki qiymat noto'g'ri. Qayta kiriting yoki /cancel.")


async def list_reminders(message: Message, app_context: BotContext) -> None:
    reminders = runtime(app_context)
    rows = await reminders.service.list_upcoming(10)
    if not rows:
        await send(message, "Pending eslatmalar yo'q.")
        return
    timezone = reminders.timezone
    await send(
        message,
        "⏰ Keyingi eslatmalar:\n\n"
        + "\n".join(
            f"{index}. {row.remind_at.astimezone(timezone):%d.%m.%Y %H:%M} — {row.title}"
            for index, row in enumerate(rows, 1)
        ),
    )


async def start_cancel(message: Message, state: FSMContext, app_context: BotContext) -> None:
    reminders = runtime(app_context)
    await reset(state, reminders)
    rows = await reminders.service.list_upcoming(10)
    if not rows:
        await send(message, "Pending eslatmalar yo'q.")
        return
    timezone = reminders.timezone
    serial = [{"id": row.id, "title": row.title} for row in rows]
    await state.set_data({"reminders": serial})
    await state.set_state(ReminderFlow.select)
    await send(
        message,
        "Bekor qilinadigan reminder raqami:\n"
        + "\n".join(
            f"{index}. {row.remind_at.astimezone(timezone):%d.%m.%Y %H:%M} — {row.title}"
            for index, row in enumerate(rows, 1)
        ),
    )


async def cancel_flow(message: Message, state: FSMContext, app_context: BotContext) -> None:
    await reset(state, runtime(app_context))
    await send(message, "Bekor qilindi.")


async def confirmed(callback: CallbackQuery, state: FSMContext, app_context: BotContext) -> None:
    reminders = runtime(app_context)
    _, decision, token = (callback.data or "").split(":", 2)
    data = await state.get_data()
    if await state.get_state() != ReminderFlow.confirm.state or data.get("action") != token:
        await callback.answer("Tasdiq eskirgan.")
        return
    await state.clear()
    await callback.answer()
    text = await reminders.actions.confirm(token) if decision == "yes" else "Bekor qilindi."
    if decision != "yes":
        await reminders.actions.cancel_action(token)
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramAPIError:
            pass
        await send(callback.message, text)


class ReminderErrorMiddleware:
    async def __call__(self, handler: Any, event: Any, data: dict[str, Any]) -> Any:
        try:
            return await handler(event, data)
        except ReminderError as error:
            if isinstance(event, CallbackQuery):
                await event.answer(str(error)[:180], show_alert=True)
            else:
                await send(event, str(error))
            return None


def create_router() -> Router:
    router = Router(name="reminders")
    router.message.middleware(ReminderErrorMiddleware())
    router.callback_query.middleware(ReminderErrorMiddleware())
    router.message.register(start_create, Command("remind"))
    router.message.register(list_reminders, Command("reminders"))
    router.message.register(start_cancel, Command("reminder_cancel"))
    router.message.register(cancel_flow, Command("cancel"), StateFilter(ReminderFlow))
    router.message.register(
        input_step,
        F.text & ~F.text.startswith("/"),
        StateFilter(ReminderFlow.text, ReminderFlow.date, ReminderFlow.time, ReminderFlow.select),
    )
    router.callback_query.register(confirmed, F.data.regexp(r"^rem:(yes|no):[A-Za-z0-9_-]{32}$"))
    return router
