from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from app.bot.constants import LOCK, LOCKOUT, PIN_PROMPT, UNLOCKED, WRONG_PIN, command_name
from app.bot.context import BotContext
from app.bot.states import UnlockFlow
from app.bot.transport import delete_sensitive_message
from app.modules.audit.actions import AuditAction
from app.modules.security.service import UnlockResult


async def lock(message: Message, state: FSMContext, app_context: BotContext) -> None:
    await app_context.security.lock()
    await state.clear()
    await app_context.persistence.audit(AuditAction.SESSION_LOCKED, app_context.owner_id)
    await message.answer("🔐 Tizim qulflandi.", reply_markup=ReplyKeyboardRemove())


async def begin_unlock(message: Message, state: FSMContext, app_context: BotContext) -> None:
    await state.clear()
    if await app_context.security.guard.blocked():
        await message.answer(LOCKOUT)
        return
    await state.set_state(UnlockFlow.waiting_for_pin)
    await message.answer(PIN_PROMPT, reply_markup=ReplyKeyboardRemove())


async def receive_pin(message: Message, state: FSMContext, app_context: BotContext) -> None:
    await state.clear()
    await delete_sensitive_message(message)
    result = await app_context.security.unlock(message.text or "")
    action = (
        AuditAction.LOGIN_SUCCESS if result == UnlockResult.SUCCESS else AuditAction.LOGIN_FAILED
    )
    await app_context.persistence.audit(action, app_context.owner_id)
    if result == UnlockResult.SUCCESS:
        await app_context.persistence.audit(AuditAction.SESSION_UNLOCKED, app_context.owner_id)
    await message.answer(
        {
            UnlockResult.SUCCESS: UNLOCKED,
            UnlockResult.FAILED: WRONG_PIN,
            UnlockResult.BLOCKED: LOCKOUT,
        }[result]
    )


def create_router() -> Router:
    router = Router(name="security")
    router.message.register(lock, Command("lock"))
    router.message.register(begin_unlock, Command("unlock"))
    router.message.register(lock, F.text == LOCK)
    # This handler precedes all menu handlers; pending PIN text cannot invoke a module.
    router.message.register(receive_pin, UnlockFlow.waiting_for_pin, is_pin_input)
    return router


def is_pin_input(message: Message) -> bool:
    return command_name(message.text) is None
