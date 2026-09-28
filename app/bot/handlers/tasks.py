from datetime import date, timedelta

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.context import BotContext
from app.bot.keyboards.tasks import confirmation, priorities, yes_no
from app.database.models.task import TaskPriority
from app.modules.tasks.exceptions import TaskError
from app.modules.tasks.runtime import TaskRuntime
from app.modules.tasks.utils import due_at_utc, parse_local_time


class TaskFlow(StatesGroup):
    title = State()
    description = State()
    due_date = State()
    due_time = State()
    priority = State()
    reminder = State()
    calendar = State()


def runtime(context: BotContext) -> TaskRuntime:
    if context.tasks is None:
        raise TaskError("Tasks PostgreSQL, owner ID va encryption key talab qiladi.")
    return context.tasks


def task_list(rows) -> str:
    if not rows:
        return "Tasklar topilmadi."
    icons = {"LOW": "LOW", "NORMAL": "NORMAL", "HIGH": "HIGH", "URGENT": "URGENT"}
    lines = []
    for index, row in enumerate(rows, 1):
        due = row.due_at.strftime("%d.%m %H:%M UTC") if row.due_at else (
            row.due_date.strftime("%d.%m.%Y") if row.due_date else "Muddat yo'q"
        )
        lines.append(f"{index}. [{icons[row.priority.value]}] {row.title}\n   {due} [ID {row.id}]")
    return "Vazifalar:\n\n" + "\n\n".join(lines)


async def menu(message: Message, app_context: BotContext) -> None:
    runtime(app_context)
    await message.answer(
        "Tasks\n\n/task - yangi task\n/tasks\n/task_today\n/task_tomorrow\n"
        "/task_overdue\n/task_done ID\n/task_edit ID FIELD VALUE\n"
        "/task_delete ID\n/task_priority ID PRIORITY\n/task_calendar ID\n/task_carry"
    )


async def start_create(message: Message, state: FSMContext, app_context: BotContext) -> None:
    runtime(app_context)
    title = (message.text or "").partition(" ")[2].strip()
    if title:
        await state.update_data(title=title)
        await state.set_state(TaskFlow.description)
        await message.answer("Description yoki /skip.")
    else:
        await state.set_state(TaskFlow.title)
        await message.answer("Task nomini kiriting.")


async def capture_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Task nomi bo'sh bo'lmaydi.")
        return
    await state.update_data(title=title)
    await state.set_state(TaskFlow.description)
    await message.answer("Description yoki /skip.")


async def capture_description(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    await state.update_data(description=None if raw.startswith("/skip") else raw)
    await state.set_state(TaskFlow.due_date)
    await message.answer("Due date DD.MM.YYYY yoki /skip.")


async def capture_date(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if raw.startswith("/skip"):
        await state.update_data(due_date=None)
    else:
        try:
            day, month, year = (int(item) for item in raw.split("."))
            await state.update_data(due_date=date(year, month, day).isoformat())
        except (TypeError, ValueError):
            await message.answer("Format: DD.MM.YYYY yoki /skip.")
            return
    await state.set_state(TaskFlow.due_time)
    await message.answer("Due time HH:MM yoki /skip.")


async def capture_time(message: Message, state: FSMContext, app_context: BotContext) -> None:
    raw = (message.text or "").strip()
    data = await state.get_data()
    due_date = date.fromisoformat(data["due_date"]) if data.get("due_date") else None
    if raw.startswith("/skip"):
        due_at = None
    elif due_date:
        try:
            due_at = due_at_utc(due_date, parse_local_time(raw), runtime(app_context).service.timezone)
        except (TypeError, ValueError):
            await message.answer("Format: HH:MM yoki /skip.")
            return
    else:
        await message.answer("Vaqt uchun avval sana kerak. /skip yuboring.")
        return
    await state.update_data(due_at=due_at.isoformat() if due_at else None)
    await state.set_state(TaskFlow.priority)
    await message.answer("Priority tanlang.", reply_markup=priorities())


async def choose_priority(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(priority=(callback.data or "").rsplit(":", 1)[-1])
    await state.set_state(TaskFlow.reminder)
    await callback.answer()
    if callback.message:
        await callback.message.edit_text("Reminder yoqilsinmi?", reply_markup=yes_no("reminder"))


async def choose_reminder(callback: CallbackQuery, state: FSMContext) -> None:
    enabled = (callback.data or "").endswith(":yes")
    data = await state.get_data()
    if enabled and not data.get("due_date"):
        await callback.answer("Reminder uchun due date kerak.", show_alert=True)
        return
    await state.update_data(reminder_enabled=enabled)
    await state.set_state(TaskFlow.calendar)
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            "Calendar'ga qo'shilsinmi?", reply_markup=yes_no("calendar")
        )


async def choose_calendar(
    callback: CallbackQuery, state: FSMContext, app_context: BotContext
) -> None:
    enabled = (callback.data or "").endswith(":yes")
    data = await state.get_data()
    if enabled and not data.get("due_at"):
        await callback.answer("Calendar uchun due time kerak.", show_alert=True)
        return
    data["calendar_sync"] = enabled
    token = await runtime(app_context).actions.prepare("create", data)
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            f"Yangi task\nNomi: {data['title']}\nSana: {data.get('due_date') or '-'}\n"
            f"Priority: {data['priority']}\nReminder: {data.get('reminder_enabled')}\n"
            f"Calendar: {enabled}\n\nSaqlansinmi?",
            reply_markup=confirmation(token),
        )


async def confirm_action(callback: CallbackQuery, app_context: BotContext) -> None:
    tasks = runtime(app_context)
    token = (callback.data or "").rsplit(":", 1)[-1]
    if ":no:" in (callback.data or ""):
        await tasks.actions.cancel(token)
        result = "Bekor qilindi."
    else:
        result = await tasks.actions.confirm(token)
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(result)


async def list_open(message: Message, app_context: BotContext) -> None:
    await message.answer(task_list(await runtime(app_context).service.list_tasks()))


async def list_today(message: Message, app_context: BotContext) -> None:
    await message.answer(task_list(await runtime(app_context).service.today()))


async def list_tomorrow(message: Message, app_context: BotContext) -> None:
    await message.answer(task_list(await runtime(app_context).service.tomorrow()))


async def list_overdue(message: Message, app_context: BotContext) -> None:
    await message.answer(task_list(await runtime(app_context).service.overdue()))


async def mutation(message: Message, app_context: BotContext) -> None:
    command, _, rest = (message.text or "").partition(" ")
    parts = rest.split(maxsplit=2)
    if not parts or not parts[0].isdigit():
        await message.answer("Task ID kerak.")
        return
    task_id = int(parts[0])
    tasks = runtime(app_context)
    if command.startswith("/task_done"):
        kind, data = "complete", {"id": task_id}
    elif command.startswith("/task_delete"):
        kind, data = "delete", {"id": task_id}
    elif command.startswith("/task_priority") and len(parts) >= 2:
        try:
            priority = TaskPriority(parts[1].upper())
        except ValueError:
            await message.answer("Priority: LOW, NORMAL, HIGH, URGENT")
            return
        kind, data = "update", {"id": task_id, "priority": priority.value}
    elif command.startswith("/task_calendar"):
        kind, data = "update", {"id": task_id, "calendar_sync": True}
    elif command.startswith("/task_edit") and len(parts) == 3:
        field, value = parts[1], parts[2]
        if field not in {"title", "description", "due_date", "due_at", "priority", "reminder_enabled"}:
            await message.answer("Unsupported field.")
            return
        data = {"id": task_id, field: value}
        kind = "update"
    else:
        await message.answer("Buyruq formati noto'g'ri.")
        return
    token = await tasks.actions.prepare(kind, data)
    await message.answer("Amal tasdiqlansinmi?", reply_markup=confirmation(token))


async def carry(message: Message, app_context: BotContext) -> None:
    tasks = runtime(app_context)
    today = tasks.service.now().astimezone(tasks.service.timezone).date()
    rows = await tasks.service.list_unfinished_for_date(today)
    if not rows:
        await message.answer("Ko'chiriladigan task yo'q.")
        return
    new_date = today + timedelta(days=1)
    token = await tasks.actions.prepare(
        "carry", {"ids": [row.id for row in rows], "date": new_date.isoformat()}
    )
    await message.answer(
        task_list(rows) + f"\n\n{new_date:%d.%m.%Y} sanaga ko'chirilsinmi?",
        reply_markup=confirmation(token),
    )


async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.")


def create_router() -> Router:
    router = Router(name="tasks")
    router.message.register(menu, Command("tasks_menu"))
    router.message.register(start_create, Command("task"))
    router.message.register(list_open, Command("tasks"))
    router.message.register(list_today, Command("task_today"))
    router.message.register(list_tomorrow, Command("task_tomorrow"))
    router.message.register(list_overdue, Command("task_overdue"))
    router.message.register(mutation, Command("task_done", "task_edit", "task_delete", "task_priority", "task_calendar"))
    router.message.register(carry, Command("task_carry"))
    router.callback_query.register(choose_priority, F.data.startswith("task:priority:"))
    router.callback_query.register(choose_reminder, F.data.startswith("task:reminder:"))
    router.callback_query.register(choose_calendar, F.data.startswith("task:calendar:"))
    router.callback_query.register(confirm_action, F.data.startswith("task:yes:"))
    router.callback_query.register(confirm_action, F.data.startswith("task:no:"))
    router.message.register(cancel, Command("cancel"), StateFilter(TaskFlow))
    router.message.register(capture_title, StateFilter(TaskFlow.title))
    router.message.register(capture_description, StateFilter(TaskFlow.description))
    router.message.register(capture_date, StateFilter(TaskFlow.due_date))
    router.message.register(capture_time, StateFilter(TaskFlow.due_time))
    return router
