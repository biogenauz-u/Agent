import logging
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.context import BotContext
from app.bot.keyboards.personal_telegram import (
    disconnect_confirmation,
    draft_confirmation,
)
from app.modules.email.utils import telegram_chunks
from app.modules.personal_telegram.exceptions import PersonalTelegramError
from app.modules.personal_telegram.runtime import PersonalTelegramRuntime


class PersonalTelegramFlow(StatesGroup):
    phone = State()
    code = State()
    password = State()
    read = State()
    search = State()
    reply_target = State()
    reply_text = State()


def runtime(context: BotContext) -> PersonalTelegramRuntime:
    if context.personal_telegram is None:
        raise PersonalTelegramError(
            "Personal Telegram o‘chiq yoki sozlanmagan. API ID/hash, PostgreSQL va encryption keyni tekshiring."
        )
    return context.personal_telegram


async def delete_sensitive(message: Message) -> None:
    try:
        await message.delete()
    except TelegramAPIError:
        logging.getLogger(__name__).warning("sensitive_login_message_not_deleted")


async def menu(message: Message, app_context: BotContext) -> None:
    personal = runtime(app_context)
    connected = await personal.service.connected()
    account = await personal.service._client().get_me() if connected else None
    monitoring = personal.monitor.running
    await message.answer(
        "💬 Personal Telegram\n\n"
        f"Status: {'✅ Connected' if connected else '❌ Not connected'}\n"
        f"Monitoring: {'✅ Active' if monitoring else '⏸ Disabled'}\n"
        f"Account: {'@' + account.username if account and account.username else '—'}\n\n"
        "/tg_recent\n/tg_read\n/tg_search\n/tg_reply\n"
        "/telegram_connect\n/telegram_disconnect",
        parse_mode=None,
    )


async def start_connect(message: Message, state: FSMContext, app_context: BotContext) -> None:
    personal = runtime(app_context)
    if await personal.service.connected():
        await message.answer("Personal Telegram allaqachon ulangan.", parse_mode=None)
        return
    await state.clear()
    await state.set_state(PersonalTelegramFlow.phone)
    await message.answer(
        "Telegram hisob telefon raqamini xalqaro formatda kiriting. Xabar qayta ishlangach o‘chiriladi.",
        parse_mode=None,
    )


async def phone_input(message: Message, state: FSMContext, app_context: BotContext) -> None:
    phone = (message.text or "").strip()
    await delete_sensitive(message)
    delivery = await runtime(app_context).service.start_login(phone)
    await state.set_state(PersonalTelegramFlow.code)
    await message.answer(
        "Telegram yuborgan login kodini kiriting. Kod saqlanmaydi va xabar o‘chiriladi.\n\n"
        f"Yetkazish kanali: {delivery}\n"
        "Kod kelmasa /telegram_resend_code buyrug‘ini bir marta yuboring.",
        parse_mode=None,
    )


async def resend_code(message: Message, app_context: BotContext) -> None:
    delivery = await runtime(app_context).service.resend_code()
    await message.answer(
        f"Yangi kod so‘raldi. Yetkazish kanali: {delivery}. Eng oxirgi kodni kiriting.",
        parse_mode=None,
    )


async def code_input(message: Message, state: FSMContext, app_context: BotContext) -> None:
    code = (message.text or "").strip()
    await delete_sensitive(message)
    result = await runtime(app_context).service.submit_code(code)
    if result.password_required:
        await state.set_state(PersonalTelegramFlow.password)
        await message.answer(
            "🔐 Telegram ikki bosqichli parolini kiriting. Parol saqlanmaydi.", parse_mode=None
        )
        return
    await state.clear()
    await runtime(app_context).activate_monitor()
    await message.answer("✅ Personal Telegram ulandi.", parse_mode=None)


async def password_input(message: Message, state: FSMContext, app_context: BotContext) -> None:
    password = message.text or ""
    await delete_sensitive(message)
    await runtime(app_context).service.submit_password(password)
    password = ""
    await state.clear()
    await runtime(app_context).activate_monitor()
    await message.answer("✅ Personal Telegram ulandi.", parse_mode=None)


async def cancel_flow(message: Message, state: FSMContext, app_context: BotContext) -> None:
    current = await state.get_state()
    if current in {
        PersonalTelegramFlow.phone.state,
        PersonalTelegramFlow.code.state,
        PersonalTelegramFlow.password.state,
    }:
        await runtime(app_context).service.abort_login()
    await state.clear()
    await message.answer("Bekor qilindi.", parse_mode=None)


async def request_disconnect(message: Message) -> None:
    await message.answer(
        "Assistant saqlagan personal Telegram session o‘chirilsinmi? Bu boshqa Telegram qurilmalaridan chiqarmaydi.",
        reply_markup=disconnect_confirmation(),
        parse_mode=None,
    )


async def disconnect_callback(callback: CallbackQuery, app_context: BotContext) -> None:
    decision = (callback.data or "").rsplit(":", 1)[-1]
    await callback.answer()
    if decision == "yes":
        await runtime(app_context).disconnect()
        text = "Personal Telegram assistantdan uzildi. Boshqa Telegram sessionlar saqlandi."
    else:
        text = "Bekor qilindi."
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(text, parse_mode=None)


def format_list(rows) -> str:
    if not rows:
        return "Personal Telegram xabarlari topilmadi."
    return "💬 Oxirgi xabarlar:\n\n" + "\n".join(
        f"{index}. {row.received_at:%d.%m %H:%M} — {row.sender_display_name} — "
        f"{row.preview or '[' + (row.media_type or 'media') + ']'} [ID {row.id}]"
        for index, row in enumerate(rows, 1)
    )


async def recent(message: Message, app_context: BotContext) -> None:
    await message.answer(
        format_list(await runtime(app_context).service.list_recent()), parse_mode=None
    )


async def start_read(message: Message, state: FSMContext, app_context: BotContext) -> None:
    rows = await runtime(app_context).service.list_recent()
    await state.set_state(PersonalTelegramFlow.read)
    await message.answer(format_list(rows) + "\n\nO‘qish uchun ID kiriting.", parse_mode=None)


async def show_message(message: Message, message_id: int, app_context: BotContext) -> None:
    row = await runtime(app_context).service.read(message_id)
    if row is None:
        await message.answer("Xabar topilmadi.", parse_mode=None)
        return
    media = f"\n📎 {row.media_type}" if row.has_media else ""
    text = (
        f"Kimdan: {row.sender_display_name}\n"
        f"Vaqt: {row.received_at:%d.%m.%Y %H:%M}{media}\n\n"
        f"{row.text or '(matnsiz xabar)'}"
    )
    for chunk in telegram_chunks(text):
        await message.answer(chunk, parse_mode=None, disable_web_page_preview=True)


async def read_input(message: Message, state: FSMContext, app_context: BotContext) -> None:
    try:
        message_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("Raqamli ichki ID kiriting.", parse_mode=None)
        return
    await state.clear()
    await show_message(message, message_id, app_context)


async def read_callback(callback: CallbackQuery, app_context: BotContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_message(
            callback.message, int((callback.data or "").rsplit(":", 1)[-1]), app_context
        )


async def start_search(message: Message, state: FSMContext) -> None:
    await state.set_state(PersonalTelegramFlow.search)
    await message.answer("Qidiruv matnini kiriting.", parse_mode=None)


async def search_input(message: Message, state: FSMContext, app_context: BotContext) -> None:
    query = (message.text or "").strip()
    rows = await runtime(app_context).service.search(query)
    await state.clear()
    await message.answer(format_list(rows), parse_mode=None)


async def start_reply(message: Message, state: FSMContext, app_context: BotContext) -> None:
    rows = await runtime(app_context).service.list_recent()
    await state.set_state(PersonalTelegramFlow.reply_target)
    await message.answer(
        format_list(rows) + "\n\nJavob beriladigan xabar ID sini kiriting.", parse_mode=None
    )


async def reply_target_input(message: Message, state: FSMContext) -> None:
    try:
        message_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("Raqamli ichki ID kiriting.", parse_mode=None)
        return
    await state.set_data({"target_message_id": message_id})
    await state.set_state(PersonalTelegramFlow.reply_text)
    await message.answer(
        "Yubormoqchi bo‘lgan aniq javob matnini kiriting. AI qayta yozmaydi.", parse_mode=None
    )


async def draft_callback(callback: CallbackQuery, state: FSMContext) -> None:
    message_id = int((callback.data or "").rsplit(":", 1)[-1])
    await state.set_data({"target_message_id": message_id})
    await state.set_state(PersonalTelegramFlow.reply_text)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            "Yubormoqchi bo‘lgan aniq javob matnini kiriting. AI qayta yozmaydi.",
            parse_mode=None,
        )


async def draft_text_input(message: Message, state: FSMContext, app_context: BotContext) -> None:
    data = await state.get_data()
    target = int(data["target_message_id"])
    draft = await runtime(app_context).service.create_draft(target, message.text or "")
    await state.clear()
    await message.answer(
        f"✍️ Javob draft:\n\n{draft.text}\n\nYuborilsinmi?",
        reply_markup=draft_confirmation(draft.id),
        parse_mode=None,
    )


async def send_draft(callback: CallbackQuery, app_context: BotContext) -> None:
    draft_id = int((callback.data or "").rsplit(":", 1)[-1])
    await runtime(app_context).service.confirm_and_send(draft_id)
    await callback.answer("Yuborildi.")
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("✅ Javob yuborildi.", parse_mode=None)


async def cancel_draft(callback: CallbackQuery, app_context: BotContext) -> None:
    draft_id = int((callback.data or "").rsplit(":", 1)[-1])
    cancelled = await runtime(app_context).service.cancel_draft(draft_id)
    await callback.answer("Bekor qilindi." if cancelled else "Draft allaqachon ishlatilgan.")
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)


async def edit_draft(callback: CallbackQuery, state: FSMContext, app_context: BotContext) -> None:
    draft_id = int((callback.data or "").rsplit(":", 1)[-1])
    draft = await runtime(app_context).service.get_draft(draft_id)
    if draft is None or not await runtime(app_context).service.cancel_draft(draft_id):
        await callback.answer("Draft allaqachon ishlatilgan.", show_alert=True)
        return
    await state.set_data({"target_message_id": draft.target_message_id})
    await state.set_state(PersonalTelegramFlow.reply_text)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Yangi draft matnini kiriting.", parse_mode=None)


async def ignore(callback: CallbackQuery) -> None:
    await callback.answer("E'tiborsiz qoldirildi.")
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)


class PersonalTelegramErrorMiddleware:
    async def __call__(self, handler: Any, event: Any, data: dict[str, Any]) -> Any:
        try:
            return await handler(event, data)
        except (PersonalTelegramError, ValueError) as error:
            target = event.message if isinstance(event, CallbackQuery) else event
            if isinstance(target, Message):
                await target.answer(str(error), parse_mode=None)
            elif isinstance(event, CallbackQuery):
                await event.answer(str(error)[:180], show_alert=True)
            return None


def create_router() -> Router:
    router = Router(name="personal_telegram")
    router.message.middleware(PersonalTelegramErrorMiddleware())
    router.callback_query.middleware(PersonalTelegramErrorMiddleware())
    router.message.register(menu, Command("telegram", "telegram_status"))
    router.message.register(menu, F.text == "💬 Telegram")
    router.message.register(start_connect, Command("telegram_connect"))
    router.message.register(request_disconnect, Command("telegram_disconnect"))
    router.message.register(recent, Command("tg_recent"))
    router.message.register(start_read, Command("tg_read"))
    router.message.register(start_search, Command("tg_search"))
    router.message.register(start_reply, Command("tg_reply"))
    router.message.register(
        cancel_flow,
        Command("cancel"),
        StateFilter(
            PersonalTelegramFlow.phone,
            PersonalTelegramFlow.code,
            PersonalTelegramFlow.password,
            PersonalTelegramFlow.read,
            PersonalTelegramFlow.search,
            PersonalTelegramFlow.reply_target,
            PersonalTelegramFlow.reply_text,
        ),
    )
    router.message.register(phone_input, F.text, StateFilter(PersonalTelegramFlow.phone))
    router.message.register(
        resend_code,
        Command("telegram_resend_code"),
        StateFilter(PersonalTelegramFlow.code),
    )
    router.message.register(code_input, F.text, StateFilter(PersonalTelegramFlow.code))
    router.message.register(password_input, F.text, StateFilter(PersonalTelegramFlow.password))
    router.message.register(read_input, F.text, StateFilter(PersonalTelegramFlow.read))
    router.message.register(search_input, F.text, StateFilter(PersonalTelegramFlow.search))
    router.message.register(
        reply_target_input, F.text, StateFilter(PersonalTelegramFlow.reply_target)
    )
    router.message.register(draft_text_input, F.text, StateFilter(PersonalTelegramFlow.reply_text))
    router.callback_query.register(disconnect_callback, F.data.regexp(r"^ptg:disconnect:(yes|no)$"))
    router.callback_query.register(read_callback, F.data.regexp(r"^ptg:read:\d+$"))
    router.callback_query.register(draft_callback, F.data.regexp(r"^ptg:draft:\d+$"))
    router.callback_query.register(send_draft, F.data.regexp(r"^ptg:send:\d+$"))
    router.callback_query.register(edit_draft, F.data.regexp(r"^ptg:edit:\d+$"))
    router.callback_query.register(cancel_draft, F.data.regexp(r"^ptg:cancel:\d+$"))
    router.callback_query.register(ignore, F.data.regexp(r"^ptg:ignore:\d+$"))
    return router
