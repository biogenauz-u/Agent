from datetime import date
from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.context import BotContext
from app.bot.keyboards.finance import (
    category_keyboard,
    category_menu,
    confirmation,
    currency_keyboard,
    edit_fields,
)
from app.modules.finance.exceptions import FinanceError
from app.modules.finance.runtime import FinanceRuntime
from app.modules.finance.schemas import FinancePeriodReport, FinanceTransactionView
from app.modules.finance.utils import format_money, parse_amount, parse_transaction_date


class FinanceFlow(StatesGroup):
    amount = State()
    description = State()
    confirm = State()
    category_name = State()
    edit_select = State()
    edit_value = State()
    delete_select = State()


def runtime(context: BotContext) -> FinanceRuntime:
    if context.finance is None:
        raise FinanceError("Finance PostgreSQL va TELEGRAM_OWNER_ID talab qiladi.")
    return context.finance


async def reset(state: FSMContext, finance: FinanceRuntime) -> None:
    data = await state.get_data()
    if data.get("action"):
        await finance.actions.cancel(data["action"])
    await state.clear()


def transaction_line(row: FinanceTransactionView) -> str:
    sign = "➖" if row.transaction_type.value == "EXPENSE" else "➕"
    return (
        f"{sign} {format_money(row.amount, row.currency)} — {row.category_name}\n"
        f"   {row.transaction_date:%d.%m.%Y} [ID {row.id}]"
    )


def transaction_list(rows: list[FinanceTransactionView]) -> str:
    if not rows:
        return "Operatsiyalar topilmadi."
    return "💰 Oxirgi operatsiyalar:\n\n" + "\n\n".join(
        f"{index}. {transaction_line(row)}" for index, row in enumerate(rows, 1)
    )


async def menu(message: Message, app_context: BotContext) -> None:
    finance = runtime(app_context)
    await message.answer(
        "💰 Finance\n\n"
        "➖ /expense — Xarajat\n"
        "➕ /income — Daromad\n"
        "📋 /transactions\n"
        "📅 /finance_today\n📆 /finance_week\n🗓 /finance_month\n📊 /finance_year\n"
        "🏷 /finance_categories\n/finance_edit\n/finance_delete\n\n"
        f"Default currency: {finance.settings.finance_default_currency}",
        parse_mode=None,
    )


async def start_create(
    message: Message, state: FSMContext, app_context: BotContext
) -> None:
    finance = runtime(app_context)
    await reset(state, finance)
    transaction_type = (
        "EXPENSE" if (message.text or "").split()[0].startswith("/expense") else "INCOME"
    )
    await state.set_data({"transaction_type": transaction_type})
    await state.set_state(FinanceFlow.amount)
    await message.answer("Summani kiriting. Masalan: 85000 yoki 1,250.50", parse_mode=None)


async def amount_input(message: Message, state: FSMContext) -> None:
    amount = parse_amount(message.text or "")
    data = await state.get_data()
    await state.update_data(amount=str(amount))
    await message.answer(
        "Valyutani tanlang:",
        reply_markup=currency_keyboard(data["transaction_type"]),
        parse_mode=None,
    )


async def currency_selected(
    callback: CallbackQuery, state: FSMContext, app_context: BotContext
) -> None:
    _, _, transaction_type, currency = (callback.data or "").split(":")
    data = await state.get_data()
    if data.get("transaction_type") != transaction_type or "amount" not in data:
        await callback.answer("Flow eskirgan.", show_alert=True)
        return
    categories = await runtime(app_context).service.list_categories(transaction_type)
    await state.update_data(currency=currency)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            "Kategoriyani tanlang:", reply_markup=category_keyboard(categories), parse_mode=None
        )


async def category_selected(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int((callback.data or "").rsplit(":", 1)[-1])
    await state.update_data(category_id=category_id)
    await state.set_state(FinanceFlow.description)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer("Izoh yozing yoki '-' yuboring.", parse_mode=None)


async def description_input(
    message: Message, state: FSMContext, app_context: BotContext
) -> None:
    finance = runtime(app_context)
    data = await state.get_data()
    description = None if (message.text or "").strip() in {"-", "/skip"} else message.text
    category = next(
        (
            item
            for item in await finance.service.list_categories(data["transaction_type"])
            if item.id == data["category_id"]
        ),
        None,
    )
    if category is None:
        raise FinanceError("Kategoriya topilmadi.")
    payload = {
        "transaction_type": data["transaction_type"],
        "category_id": data["category_id"],
        "amount": data["amount"],
        "currency": data["currency"],
        "description": description,
        "transaction_date": finance.service.today().isoformat(),
    }
    token = await finance.actions.prepare("create_transaction", payload)
    await state.set_data({"action": token})
    await state.set_state(FinanceFlow.confirm)
    sign = "➖ Xarajat" if data["transaction_type"] == "EXPENSE" else "➕ Daromad"
    await message.answer(
        f"{sign}\n\n{format_money(Decimal(data['amount']), data['currency'])}\n"
        f"Kategoriya: {category.name}\nIzoh: {description or '—'}\n"
        f"Sana: {finance.service.today():%d.%m.%Y}\n\nSaqlansinmi?",
        reply_markup=confirmation(token),
        parse_mode=None,
    )


async def confirmed(
    callback: CallbackQuery, state: FSMContext, app_context: BotContext
) -> None:
    _, decision, token = (callback.data or "").split(":", 2)
    data = await state.get_data()
    if data.get("action") != token:
        await callback.answer("Tasdiq eskirgan.", show_alert=True)
        return
    await state.clear()
    if decision == "yes":
        text = await runtime(app_context).actions.confirm(token)
    else:
        await runtime(app_context).actions.cancel(token)
        text = "Bekor qilindi."
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(text, parse_mode=None)


async def recent(message: Message, app_context: BotContext) -> None:
    await message.answer(
        transaction_list(await runtime(app_context).service.list_recent()), parse_mode=None
    )


def report_text(report: FinancePeriodReport) -> str:
    labels = {"today": "Bugun", "week": "Shu hafta", "month": "Shu oy", "year": "Shu yil"}
    lines = [f"💰 {labels[report.period]}"]
    if not report.currencies:
        return lines[0] + "\n\nOperatsiyalar yo‘q."
    for item in report.currencies:
        sign = "+" if item.balance >= 0 else "-"
        lines.extend(
            [
                "",
                f"{item.currency}:",
                f"Daromad: {format_money(item.income, item.currency)}",
                f"Xarajat: {format_money(item.expense, item.currency)}",
                f"Balans: {sign}{format_money(abs(item.balance), item.currency)}",
                f"Operatsiyalar: {item.transaction_count}",
            ]
        )
    if report.top_expense_categories:
        lines.append("\nTop xarajat kategoriyalari:")
        lines.extend(
            f"{index}. {item.category_name} — {format_money(item.amount, item.currency)}"
            for index, item in enumerate(report.top_expense_categories, 1)
        )
    return "\n".join(lines)


async def report(message: Message, app_context: BotContext) -> None:
    command = (message.text or "").split()[0].split("@")[0]
    period = {
        "/finance_today": "today",
        "/finance_week": "week",
        "/finance_month": "month",
        "/finance_year": "year",
    }[command]
    await message.answer(
        report_text(await runtime(app_context).service.reports.report(period)), parse_mode=None
    )


async def categories(message: Message, app_context: BotContext) -> None:
    rows = await runtime(app_context).service.list_categories()
    text = "🏷 Kategoriyalar:\n\n" + "\n".join(
        f"{item.id}. {item.name} ({item.transaction_type.value})" for item in rows
    )
    await message.answer(text, reply_markup=category_menu(), parse_mode=None)


async def category_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    category_type = (callback.data or "").rsplit(":", 1)[-1]
    await state.set_data({"category_type": category_type})
    await state.set_state(FinanceFlow.category_name)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer("Yangi kategoriya nomini kiriting.", parse_mode=None)


async def category_name_input(
    message: Message, state: FSMContext, app_context: BotContext
) -> None:
    data = await state.get_data()
    token = await runtime(app_context).actions.prepare(
        "create_category",
        {"name": message.text or "", "category_type": data["category_type"]},
    )
    await state.set_data({"action": token})
    await state.set_state(FinanceFlow.confirm)
    await message.answer(
        f"Kategoriya yaratilsinmi: {message.text}?",
        reply_markup=confirmation(token),
        parse_mode=None,
    )


async def category_deactivate_start(
    callback: CallbackQuery, app_context: BotContext
) -> None:
    rows = await runtime(app_context).service.list_categories()
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            "O‘chiriladigan kategoriyani tanlang:",
            reply_markup=category_keyboard(rows, prefix="fin:catdisable"),
            parse_mode=None,
        )


async def category_deactivate_selected(
    callback: CallbackQuery, state: FSMContext, app_context: BotContext
) -> None:
    category_id = int((callback.data or "").rsplit(":", 1)[-1])
    token = await runtime(app_context).actions.prepare(
        "deactivate_category", {"id": category_id}
    )
    await state.set_data({"action": token})
    await state.set_state(FinanceFlow.confirm)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            "Kategoriya soft-disable qilinsinmi?",
            reply_markup=confirmation(token),
            parse_mode=None,
        )


async def start_edit(message: Message, state: FSMContext, app_context: BotContext) -> None:
    rows = await runtime(app_context).service.list_recent()
    await state.set_state(FinanceFlow.edit_select)
    await message.answer(transaction_list(rows) + "\n\nID kiriting.", parse_mode=None)


async def edit_select_input(
    message: Message, state: FSMContext, app_context: BotContext
) -> None:
    transaction_id = int((message.text or "").strip())
    row = await runtime(app_context).service.get_transaction(transaction_id)
    await state.set_data({"transaction_id": transaction_id})
    await message.answer(
        "Nimani o‘zgartiramiz?\n\n" + transaction_line(row),
        reply_markup=edit_fields(transaction_id),
        parse_mode=None,
    )


async def edit_field_selected(
    callback: CallbackQuery, state: FSMContext, app_context: BotContext
) -> None:
    _, _, field, identifier = (callback.data or "").split(":")
    transaction_id = int(identifier)
    row = await runtime(app_context).service.get_transaction(transaction_id)
    await callback.answer()
    if field == "category":
        categories = await runtime(app_context).service.list_categories(row.transaction_type)
        if isinstance(callback.message, Message):
            await callback.message.answer(
                "Yangi kategoriya:",
                reply_markup=category_keyboard(
                    categories, prefix=f"fin:editcat:{transaction_id}"
                ),
                parse_mode=None,
            )
        return
    await state.set_data({"transaction_id": transaction_id, "field": field})
    await state.set_state(FinanceFlow.edit_value)
    prompt = {
        "amount": "Yangi summa:",
        "description": "Yangi izoh yoki '-' (tozalash):",
        "date": "Yangi sana DD.MM.YYYY:",
    }[field]
    if isinstance(callback.message, Message):
        await callback.message.answer(prompt, parse_mode=None)


async def prepare_update(
    message: Message,
    state: FSMContext,
    finance: FinanceRuntime,
    transaction_id: int,
    values: dict[str, object],
) -> None:
    serial = {
        key: (value.isoformat() if isinstance(value, date) else str(value) if isinstance(value, Decimal) else value)
        for key, value in values.items()
    }
    token = await finance.actions.prepare(
        "update_transaction", {"id": transaction_id, "values": serial}
    )
    before = await finance.service.get_transaction(transaction_id)
    await state.set_data({"action": token})
    await state.set_state(FinanceFlow.confirm)
    await message.answer(
        "O‘zgarish tasdiqlansinmi?\n\nOldin:\n"
        + transaction_line(before)
        + f"\n\nYangi qiymat: {next(iter(serial.values()))}",
        reply_markup=confirmation(token),
        parse_mode=None,
    )


async def edit_value_input(
    message: Message, state: FSMContext, app_context: BotContext
) -> None:
    data = await state.get_data()
    field = data["field"]
    text = (message.text or "").strip()
    if field == "amount":
        values = {"amount": parse_amount(text)}
    elif field == "date":
        values = {"transaction_date": parse_transaction_date(text, runtime(app_context).settings.timezone)}
    else:
        values = {"description": None if text == "-" else text}
    await prepare_update(
        message, state, runtime(app_context), int(data["transaction_id"]), values
    )


async def edit_category_selected(
    callback: CallbackQuery, state: FSMContext, app_context: BotContext
) -> None:
    parts = (callback.data or "").split(":")
    transaction_id, category_id = int(parts[-2]), int(parts[-1])
    await callback.answer()
    if isinstance(callback.message, Message):
        await prepare_update(
            callback.message,
            state,
            runtime(app_context),
            transaction_id,
            {"category_id": category_id},
        )


async def start_delete(message: Message, state: FSMContext, app_context: BotContext) -> None:
    rows = await runtime(app_context).service.list_recent()
    await state.set_state(FinanceFlow.delete_select)
    await message.answer(transaction_list(rows) + "\n\nO‘chirish uchun ID kiriting.", parse_mode=None)


async def delete_select_input(
    message: Message, state: FSMContext, app_context: BotContext
) -> None:
    transaction_id = int((message.text or "").strip())
    row = await runtime(app_context).service.get_transaction(transaction_id)
    token = await runtime(app_context).actions.prepare(
        "delete_transaction", {"id": transaction_id}
    )
    await state.set_data({"action": token})
    await state.set_state(FinanceFlow.confirm)
    await message.answer(
        transaction_line(row) + "\n\nSoft-delete qilinsinmi?",
        reply_markup=confirmation(token),
        parse_mode=None,
    )


async def cancel(message: Message, state: FSMContext, app_context: BotContext) -> None:
    await reset(state, runtime(app_context))
    await message.answer("Bekor qilindi.", parse_mode=None)


class FinanceErrorMiddleware:
    async def __call__(self, handler: Any, event: Any, data: dict[str, Any]) -> Any:
        try:
            return await handler(event, data)
        except (FinanceError, ValueError) as error:
            target = event.message if isinstance(event, CallbackQuery) else event
            if isinstance(target, Message):
                await target.answer(str(error), parse_mode=None)
            return None


def create_router() -> Router:
    router = Router(name="finance")
    router.message.middleware(FinanceErrorMiddleware())
    router.callback_query.middleware(FinanceErrorMiddleware())
    router.message.register(menu, Command("finance"))
    router.message.register(menu, F.text == "💰 Finance")
    router.message.register(start_create, Command("expense", "income"))
    router.message.register(recent, Command("transactions"))
    router.message.register(
        report, Command("finance_today", "finance_week", "finance_month", "finance_year")
    )
    router.message.register(categories, Command("finance_categories"))
    router.message.register(start_edit, Command("finance_edit"))
    router.message.register(start_delete, Command("finance_delete"))
    router.message.register(
        cancel,
        Command("cancel"),
        StateFilter(
            FinanceFlow.amount,
            FinanceFlow.description,
            FinanceFlow.confirm,
            FinanceFlow.category_name,
            FinanceFlow.edit_select,
            FinanceFlow.edit_value,
            FinanceFlow.delete_select,
        ),
    )
    router.message.register(amount_input, F.text, StateFilter(FinanceFlow.amount))
    router.message.register(description_input, F.text, StateFilter(FinanceFlow.description))
    router.message.register(category_name_input, F.text, StateFilter(FinanceFlow.category_name))
    router.message.register(edit_select_input, F.text, StateFilter(FinanceFlow.edit_select))
    router.message.register(edit_value_input, F.text, StateFilter(FinanceFlow.edit_value))
    router.message.register(delete_select_input, F.text, StateFilter(FinanceFlow.delete_select))
    router.callback_query.register(currency_selected, F.data.regexp(r"^fin:currency:(EXPENSE|INCOME):(UZS|USD|EUR)$"))
    router.callback_query.register(category_selected, F.data.regexp(r"^fin:category:\d+$"))
    router.callback_query.register(confirmed, F.data.regexp(r"^fin:(yes|no):[A-Za-z0-9_-]{32}$"))
    router.callback_query.register(category_add_start, F.data.regexp(r"^fin:catadd:(EXPENSE|INCOME)$"))
    router.callback_query.register(category_deactivate_start, F.data == "fin:catdeactivate")
    router.callback_query.register(category_deactivate_selected, F.data.regexp(r"^fin:catdisable:\d+$"))
    router.callback_query.register(edit_field_selected, F.data.regexp(r"^fin:edit:(amount|category|description|date):\d+$"))
    router.callback_query.register(edit_category_selected, F.data.regexp(r"^fin:editcat:\d+:\d+$"))
    return router
