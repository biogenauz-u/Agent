"""Telegram presentation/FSM only. Provider operations live behind CalendarActions."""

import logging
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.context import BotContext
from app.bot.handlers.calendar_flow import CalendarFlow, add, input_step, reset, runtime, show
from app.bot.keyboards.calendar import confirmation
from app.modules.calendar.exceptions import CalendarConfigurationError, CalendarError
from app.modules.calendar.schemas import TimeInterval
from app.modules.calendar.utils import event_label, parse_local


async def calendar_menu(message: Message, app_context: BotContext) -> None:
    if app_context.calendar is None and message.text == "📅 Calendar":
        from app.bot.constants import PLACEHOLDER

        await show(message, PLACEHOLDER)
        return
    calendar = runtime(app_context)
    try:
        connected = await calendar.store.load()
    except CalendarConfigurationError:
        connected = None
    text = (
        "Google Calendar: Connected"
        if connected
        else "Google Calendar hali ulanmagan. /google_connect orqali ulang."
    )
    await show(
        message,
        text + f"\nCalendar: {calendar.settings.google_calendar_id}\n"
        f"Timezone: {app_context.timezone}\n/today /tomorrow /upcoming\n"
        "/event_add /event_update /event_delete\n/free DD.MM.YYYY HH:MM HH:MM\n"
        "/google_connect /google_status /google_disconnect /cancel",
    )


async def connect(message: Message, app_context: BotContext) -> None:
    url = await runtime(app_context).oauth.connect_url()
    await show(message, "Google Calendar ulash (10 daqiqa):\n" + url, disable_web_page_preview=True)


async def events(message: Message, app_context: BotContext) -> None:
    calendar = runtime(app_context)
    command = (message.text or "").split()[0].split("@")[0]
    if command == "/today":
        items = await calendar.service.get_today_events()
    elif command == "/tomorrow":
        items = await calendar.service.get_tomorrow_events()
    else:
        items = await calendar.service.list_upcoming_events()
    if not items:
        await show(message, "Calendar'da reja yo'q.")
    for offset in range(0, len(items), 10):
        await show(
            message,
            "\n".join(
                event_label(item, calendar.settings.timezone)
                for item in items[offset : offset + 10]
            ),
        )


async def free(message: Message, app_context: BotContext) -> None:
    calendar = runtime(app_context)
    try:
        _, day, start, end = (message.text or "").split()
        window = TimeInterval(
            start=parse_local(day, start, calendar.settings.timezone),
            end=parse_local(day, end, calendar.settings.timezone),
        )
    except ValueError:
        await show(message, "Format: /free DD.MM.YYYY HH:MM HH:MM")
        return
    result = await calendar.service.get_free_busy(window)
    await show(
        message,
        "Bo'sh vaqt:\n"
        + (
            "\n".join(
                f"{item.start.astimezone(calendar.settings.timezone):%H:%M}-{item.end.astimezone(calendar.settings.timezone):%H:%M}"
                for item in result.free
            )
            or "Bo'sh vaqt yo'q."
        ),
    )


async def cancel(message: Message, state: FSMContext, app_context: BotContext) -> None:
    data = await state.get_data()
    if data.get("action"):
        await runtime(app_context).actions.cancel(data["action"])
    await state.clear()
    await show(message, "Bekor qilindi.")


async def select(message: Message, state: FSMContext, app_context: BotContext) -> None:
    calendar = runtime(app_context)
    await reset(state, calendar)
    events = await calendar.service.list_upcoming_events()
    if not events:
        await show(message, "Calendar'da reja yo'q.")
        return
    kind = "delete" if (message.text or "").startswith("/event_delete") else "update"
    await state.set_data({"kind": kind, "events": [event.id for event in events]})
    await state.set_state(CalendarFlow.select)
    await show(
        message,
        "Event raqamini kiriting:\n"
        + "\n".join(
            f"{index}. {event_label(event, calendar.settings.timezone)}"
            for index, event in enumerate(events, 1)
        ),
    )


async def disconnect(message: Message, state: FSMContext, app_context: BotContext) -> None:
    calendar = runtime(app_context)
    await reset(state, calendar)
    token = await calendar.actions.prepare("disconnect", {})
    await state.set_data({"action": token})
    await state.set_state(CalendarFlow.confirm)
    await show(message, "Google Calendar ulanishi uzilsinmi?", reply_markup=confirmation(token))


async def confirmed(callback: CallbackQuery, state: FSMContext, app_context: BotContext) -> None:
    calendar = runtime(app_context)
    _, decision, token = (callback.data or "").split(":", 2)
    data = await state.get_data()
    if await state.get_state() != CalendarFlow.confirm.state or data.get("action") != token:
        await callback.answer("Tasdiq eskirgan.")
        return
    await state.clear()
    await callback.answer()
    if decision == "yes":
        text = await calendar.actions.confirm(token)
    else:
        await calendar.actions.cancel(token)
        text = "Bekor qilindi."
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramAPIError:
            logging.getLogger(__name__).warning("calendar_confirmation_markup_not_removed")
        await show(callback.message, text)


class CalendarErrorMiddleware:
    async def __call__(self, handler: Any, event: Any, data: dict[str, Any]) -> Any:
        try:
            return await handler(event, data)
        except CalendarError as error:
            if isinstance(event, CallbackQuery):
                if isinstance(event.message, Message):
                    await show(event.message, str(error))
                else:
                    await event.answer(str(error)[:180])
            else:
                await show(event, str(error))
            return None


def create_router() -> Router:
    router = Router(name="calendar")
    router.message.middleware(CalendarErrorMiddleware())
    router.callback_query.middleware(CalendarErrorMiddleware())
    router.message.register(calendar_menu, Command("calendar", "google_status"))
    router.message.register(calendar_menu, F.text == "📅 Calendar")
    router.message.register(connect, Command("google_connect"))
    router.message.register(events, Command("today", "tomorrow", "upcoming"))
    router.message.register(free, Command("free"))
    router.message.register(add, Command("event_add"))
    router.message.register(select, Command("event_update", "event_delete"))
    router.message.register(disconnect, Command("google_disconnect"))
    router.message.register(cancel, Command("cancel"))
    router.message.register(
        input_step,
        F.text & ~F.text.startswith("/"),
        StateFilter(
            CalendarFlow.title,
            CalendarFlow.date,
            CalendarFlow.time,
            CalendarFlow.duration,
            CalendarFlow.reminders,
            CalendarFlow.select,
            CalendarFlow.field,
            CalendarFlow.edit,
        ),
    )
    router.callback_query.register(confirmed, F.data.regexp(r"^cal:(yes|no):[A-Za-z0-9_-]{32}$"))
    return router
