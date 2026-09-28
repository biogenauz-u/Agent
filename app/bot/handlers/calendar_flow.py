"""Telegram presentation/FSM only. Provider operations live behind CalendarActions."""

from datetime import timedelta
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from pydantic import ValidationError

from app.bot.context import BotContext
from app.bot.keyboards.calendar import confirmation
from app.modules.calendar.exceptions import CalendarError
from app.modules.calendar.runtime import CalendarRuntime
from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventView
from app.modules.calendar.utils import event_label, parse_local


class CalendarFlow(StatesGroup):
    title = State()
    date = State()
    time = State()
    duration = State()
    reminders = State()
    select = State()
    field = State()
    edit = State()
    confirm = State()


def runtime(context: BotContext) -> CalendarRuntime:
    if context.calendar is None:
        raise CalendarError("Calendar is not available.")
    return context.calendar


async def show(message: Message, text: str, **kwargs: Any) -> None:
    for offset in range(0, len(text), 3500):
        await message.answer(text[offset : offset + 3500], parse_mode=None, **kwargs)


async def reset(state: FSMContext, calendar: CalendarRuntime) -> None:
    data = await state.get_data()
    if data.get("action"):
        await calendar.actions.cancel(data["action"])
    await state.clear()


async def add(message: Message, state: FSMContext, app_context: BotContext) -> None:
    await reset(state, runtime(app_context))
    await state.set_state(CalendarFlow.title)
    await show(message, "Event nomini kiriting. Bekor qilish: /cancel")


async def preview(
    message: Message,
    state: FSMContext,
    calendar: CalendarRuntime,
    kind: str,
    event: CalendarEventCreate,
    identifier: dict[str, str] | None = None,
) -> None:
    payload = event.model_dump(mode="json")
    if identifier:
        payload["fields"] = {
            "title": ["title"],
            "time": ["start", "end"],
            "reminder": ["reminders"],
        }[identifier["field"]]
    token = await calendar.actions.prepare(
        kind, {**identifier, "event": payload} if identifier else payload
    )
    await state.set_data({"action": token})
    await state.set_state(CalendarFlow.confirm)
    reminders = (
        "unchanged" if identifier and identifier["field"] != "reminder" else str(event.reminders)
    )
    start = event.start.astimezone(calendar.settings.timezone)
    end = event.end.astimezone(calendar.settings.timezone)
    await show(
        message,
        f"{event.title}\n{start:%d.%m.%Y %H:%M} - {end:%d.%m.%Y %H:%M}\n"
        f"Reminder (daqiqa): {reminders}\nCalendar'ga saqlansinmi?",
        reply_markup=confirmation(token),
    )


async def input_step(message: Message, state: FSMContext, app_context: BotContext) -> None:
    calendar = runtime(app_context)
    text = (message.text or "").strip()
    current, data = await state.get_state(), await state.get_data()
    try:
        if current == CalendarFlow.title.state:
            if not 1 <= len(text) <= 200:
                raise ValueError
            await state.update_data(title=text)
            await state.set_state(CalendarFlow.date)
            await show(message, "Sana: DD.MM.YYYY")
        elif current == CalendarFlow.date.state:
            parse_local(text, "00:00", calendar.settings.timezone)
            await state.update_data(day=text)
            await state.set_state(CalendarFlow.time)
            await show(message, "Boshlanish vaqti: HH:MM")
        elif current == CalendarFlow.time.state:
            start = parse_local(data["day"], text, calendar.settings.timezone)
            await state.update_data(start=start.isoformat())
            await state.set_state(CalendarFlow.duration)
            await show(
                message,
                f"Davomiylik daqiqada (1-1440); default uchun '-': {calendar.settings.calendar_default_event_duration_minutes}",
            )
        elif current == CalendarFlow.duration.state:
            duration = (
                calendar.settings.calendar_default_event_duration_minutes
                if text == "-"
                else int(text)
            )
            if not 1 <= duration <= 1440:
                raise ValueError
            await state.update_data(duration=duration)
            await state.set_state(CalendarFlow.reminders)
            await show(message, "Reminder: 10 yoki 1440,60,10. Default: '-'. O'chirish: none")
        elif current == CalendarFlow.reminders.state:
            from datetime import datetime

            start = datetime.fromisoformat(data["start"])
            event = CalendarEventCreate(
                title=data["title"],
                start=start,
                end=start + timedelta(minutes=data["duration"]),
                reminders=parse_reminders(text),
            )
            await preview(message, state, calendar, "create", event)
        elif current == CalendarFlow.select.state:
            index = int(text) - 1
            if index < 0 or index >= len(data["events"]):
                raise ValueError
            event = await calendar.service.get_event(data["events"][index])
            await calendar.service.mutable_event(event.id, event.etag)
            if data["kind"] == "delete":
                token = await calendar.actions.prepare(
                    "delete", {"id": event.id, "etag": event.etag}
                )
                await state.set_data({"action": token})
                await state.set_state(CalendarFlow.confirm)
                await show(
                    message,
                    event_label(event, calendar.settings.timezone) + "\nO'chirilsinmi?",
                    reply_markup=confirmation(token),
                )
            else:
                await state.update_data(event=event.model_dump(mode="json"))
                await state.set_state(CalendarFlow.field)
                await show(message, "Nimani o'zgartiramiz? title / time / reminder")
        elif current == CalendarFlow.field.state:
            if text not in {"title", "time", "reminder"}:
                raise ValueError
            await state.update_data(field=text)
            await state.set_state(CalendarFlow.edit)
            await show(
                message,
                {
                    "title": "Yangi nom:",
                    "time": "DD.MM.YYYY HH:MM duration_minutes",
                    "reminder": "10 yoki 1440,60,10; none",
                }[text],
            )
        elif current == CalendarFlow.edit.state:
            existing = CalendarEventView.model_validate(data["event"])
            values = existing.model_dump(
                include={"title", "start", "end", "description", "location", "reminders"}
            )
            if data["field"] == "title":
                values["title"] = text
            elif data["field"] == "reminder":
                values["reminders"] = parse_reminders(text)
            else:
                day, clock, duration_text = text.split()
                duration = int(duration_text)
                if not 1 <= duration <= 1440:
                    raise ValueError
                values["start"] = parse_local(day, clock, calendar.settings.timezone)
                values["end"] = values["start"] + timedelta(minutes=duration)
            await preview(
                message,
                state,
                calendar,
                "update",
                CalendarEventCreate.model_validate(values),
                {"id": existing.id, "etag": existing.etag, "field": data["field"]},
            )
    except (ValueError, ValidationError):
        await show(message, "Format yoki qiymat noto'g'ri. Qayta kiriting yoki /cancel.")


def parse_reminders(text: str) -> list[int]:
    if text == "none":
        return []
    return [10] if text == "-" else [int(value.strip()) for value in text.split(",")]
