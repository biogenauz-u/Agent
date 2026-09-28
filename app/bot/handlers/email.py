from datetime import UTC, datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.context import BotContext
from app.bot.keyboards.email import draft_confirmation
from app.modules.email.exceptions import GmailError
from app.modules.email.runtime import EmailRuntime
from app.modules.email.utils import telegram_chunks
from app.modules.reminders.schemas import ReminderCreate


class EmailFlow(StatesGroup):
    read = State()
    search = State()
    draft = State()
    draft_target = State()


def runtime(context: BotContext) -> EmailRuntime:
    if context.email is None:
        raise GmailError("Gmail PostgreSQL, owner ID va encryption key talab qiladi.")
    return context.email


async def menu(message: Message, app_context: BotContext) -> None:
    email = runtime(app_context)
    connected = await email.connected()
    await message.answer(
        f"📧 Email\n\nGmail: {'✅ Connected' if connected else '❌ Not connected'}\nYangi monitoring: {'✅ Active' if email.settings.run_gmail_monitor and connected else '⏸ Disabled'}\n\n/emails\n/email_unread\n/email_read\n/email_search\n/email_reply",
        parse_mode=None,
    )


async def connect(message: Message, app_context: BotContext) -> None:
    await message.answer(
        "Gmail ulash (10 daqiqa):\n" + await runtime(app_context).oauth.connect_url(),
        parse_mode=None,
        disable_web_page_preview=True,
    )


async def disconnect(message: Message, app_context: BotContext) -> None:
    await runtime(app_context).oauth.disconnect()
    await message.answer("Gmail ulanishi uzildi. Calendar credentiali saqlandi.", parse_mode=None)


def listing(rows) -> str:
    if not rows:
        return "Email topilmadi."
    return "📧 Email xabarlari:\n\n" + "\n".join(
        f"{index}. {row.received_at:%d.%m %H:%M} — {row.from_name or row.from_address} — {row.subject} [ID {row.id}]"
        for index, row in enumerate(rows, 1)
    )


async def recent(message: Message, app_context: BotContext) -> None:
    await message.answer(listing(await runtime(app_context).service.list_recent()), parse_mode=None)


async def unread(message: Message, app_context: BotContext) -> None:
    await message.answer(
        listing(await runtime(app_context).service.list_recent(True)), parse_mode=None
    )


async def start_read(message: Message, state: FSMContext, app_context: BotContext) -> None:
    rows = await runtime(app_context).service.list_recent()
    await state.set_state(EmailFlow.read)
    await message.answer(listing(rows) + "\n\nO‘qish uchun ID kiriting.", parse_mode=None)


async def show_email(message: Message, email_id: int, app_context: BotContext) -> None:
    row = await runtime(app_context).service.read(email_id)
    if row is None:
        await message.answer("Email topilmadi.", parse_mode=None)
        return
    text = f"From: {row.from_name or row.from_address}\nSubject: {row.subject}\nDate: {row.received_at:%d.%m.%Y %H:%M}\n\nQisqacha:\n{row.summary}\n\n{row.body_text}"
    for chunk in telegram_chunks(text):
        await message.answer(chunk, parse_mode=None, disable_web_page_preview=True)


async def read_input(message: Message, state: FSMContext, app_context: BotContext) -> None:
    try:
        email_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("Raqamli email ID kiriting.", parse_mode=None)
        return
    await state.clear()
    await show_email(message, email_id, app_context)


async def read_callback(callback: CallbackQuery, app_context: BotContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_email(callback.message, int((callback.data or "").split(":")[-1]), app_context)


async def start_search(message: Message, state: FSMContext) -> None:
    await state.set_state(EmailFlow.search)
    await message.answer(
        "Qidiruv so‘zini kiriting. Gmail query (masalan from:name yoki newer_than:7d) mumkin.",
        parse_mode=None,
    )


async def search_input(message: Message, state: FSMContext, app_context: BotContext) -> None:
    query = (message.text or "").strip()
    if not query or len(query) > 500:
        await message.answer("Qidiruv 1–500 belgi bo‘lsin.", parse_mode=None)
        return
    await state.clear()
    await message.answer(listing(await runtime(app_context).service.search(query)), parse_mode=None)


async def draft_start(event: Message | CallbackQuery, state: FSMContext) -> None:
    if isinstance(event, CallbackQuery):
        await state.update_data(email_id=int((event.data or "").split(":")[-1]))
        await state.set_state(EmailFlow.draft)
        await event.answer()
        message = event.message
    else:
        await state.set_state(EmailFlow.draft_target)
        message = event
    if isinstance(message, Message):
        prompt = (
            "Javob yoziladigan email ID raqamini kiriting."
            if isinstance(event, Message)
            else "Javob matnini kiriting. Yuborishdan oldin draft ko‘rsatiladi."
        )
        await message.answer(prompt, parse_mode=None)


async def draft_target_input(message: Message, state: FSMContext) -> None:
    try:
        email_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("Raqamli email ID kiriting.", parse_mode=None)
        return
    await state.update_data(email_id=email_id)
    await state.set_state(EmailFlow.draft)
    await message.answer(
        "Javob matnini kiriting. Yuborishdan oldin draft ko‘rsatiladi.", parse_mode=None
    )


async def draft_input(message: Message, state: FSMContext, app_context: BotContext) -> None:
    data = await state.get_data()
    draft = await runtime(app_context).drafts.create(int(data["email_id"]), message.text or "")
    await state.clear()
    await message.answer(
        f"✍️ Email draft\n\nKimga: {draft.recipient}\nMavzu: {draft.subject}"
        f"\n\n{draft.body}\n\nYuborishni tasdiqlaysizmi?",
        reply_markup=draft_confirmation(draft.id),
        parse_mode=None,
    )


async def send_draft(callback: CallbackQuery, app_context: BotContext) -> None:
    draft_id = int((callback.data or "").rsplit(":", 1)[-1])
    await runtime(app_context).drafts.confirm_and_send(draft_id)
    await callback.answer("Email yuborildi.")
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("✅ Email muvaffaqiyatli yuborildi.", parse_mode=None)


async def cancel_draft(callback: CallbackQuery, app_context: BotContext) -> None:
    draft_id = int((callback.data or "").rsplit(":", 1)[-1])
    cancelled = await runtime(app_context).drafts.cancel(draft_id)
    await callback.answer("Bekor qilindi." if cancelled else "Draft allaqachon ishlatilgan.")
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)


async def edit_draft(callback: CallbackQuery, state: FSMContext, app_context: BotContext) -> None:
    draft_id = int((callback.data or "").rsplit(":", 1)[-1])
    draft = await runtime(app_context).drafts.get(draft_id)
    if draft is None or not await runtime(app_context).drafts.cancel(draft_id):
        await callback.answer("Draft allaqachon ishlatilgan.", show_alert=True)
        return
    await state.set_data({"email_id": draft.email_id})
    await state.set_state(EmailFlow.draft)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Yangi draft matnini kiriting.", parse_mode=None)


async def remind(callback: CallbackQuery, app_context: BotContext) -> None:
    if app_context.reminders is None:
        await callback.answer("Reminder scheduler o‘chiq.", show_alert=True)
        return
    email_id = int((callback.data or "").split(":")[-1])
    row = await runtime(app_context).service.read(email_id)
    if row is None:
        await callback.answer("Email topilmadi.", show_alert=True)
        return
    await app_context.reminders.service.create_standalone(
        ReminderCreate(
            title=f"Emailga qaytish: {row.from_name or row.from_address} — {row.subject}"[:200],
            remind_at=datetime.now(UTC) + timedelta(minutes=10),
        )
    )
    await callback.answer("10 daqiqaga reminder yaratildi.")


class EmailErrorMiddleware:
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except GmailError as error:
            target = event.message if isinstance(event, CallbackQuery) else event
            if isinstance(target, Message):
                await target.answer(str(error), parse_mode=None)
            return None


def create_router() -> Router:
    router = Router(name="email")
    router.message.middleware(EmailErrorMiddleware())
    router.callback_query.middleware(EmailErrorMiddleware())
    router.message.register(menu, Command("email", "google_gmail_status"))
    router.message.register(connect, Command("gmail_connect"))
    router.message.register(disconnect, Command("gmail_disconnect"))
    router.message.register(recent, Command("emails"))
    router.message.register(unread, Command("email_unread"))
    router.message.register(start_read, Command("email_read"))
    router.message.register(start_search, Command("email_search"))
    router.message.register(draft_start, Command("email_reply"))
    router.message.register(read_input, F.text, StateFilter(EmailFlow.read))
    router.message.register(search_input, F.text, StateFilter(EmailFlow.search))
    router.message.register(draft_target_input, F.text, StateFilter(EmailFlow.draft_target))
    router.message.register(draft_input, F.text, StateFilter(EmailFlow.draft))
    router.callback_query.register(read_callback, F.data.regexp(r"^email:read:\d+$"))
    router.callback_query.register(draft_start, F.data.regexp(r"^email:draft:\d+$"))
    router.callback_query.register(send_draft, F.data.regexp(r"^email:send:\d+$"))
    router.callback_query.register(edit_draft, F.data.regexp(r"^email:edit:\d+$"))
    router.callback_query.register(cancel_draft, F.data.regexp(r"^email:cancel:\d+$"))
    router.callback_query.register(remind, F.data.regexp(r"^email:remind:10:\d+$"))
    return router
