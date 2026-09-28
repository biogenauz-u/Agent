import pytest
from aiogram.methods import DeleteMessage

from app.bot.constants import LOCKED, LOCKOUT, PIN_PROMPT, UNLOCKED, WRONG_PIN
from app.bot.states import UnlockFlow
from app.modules.audit.actions import AuditAction

from .conftest import Harness


async def test_unlock_flow(harness: Harness) -> None:
    await harness.send("/unlock")
    assert harness.replies[-1] == PIN_PROMPT
    state = harness.dispatcher.fsm.get_context(bot=harness.bot, chat_id=42, user_id=42)
    assert await state.get_state() == UnlockFlow.waiting_for_pin.state
    await harness.send("test-pin-only")
    assert harness.replies[-1] == UNLOCKED
    assert not await harness.context.security.lock_state.is_locked()
    assert await state.get_state() is None
    assert any(isinstance(call, DeleteMessage) for call in harness.api.calls)
    assert "test-pin-only" not in repr(harness.audit.await_args_list)
    assert "test-pin-only" not in "\n".join(harness.replies)
    harness.audit.assert_any_await(AuditAction.LOGIN_SUCCESS, 42)
    harness.audit.assert_any_await(AuditAction.SESSION_UNLOCKED, 42)


async def test_wrong_pin(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send("wrong-test-only")
    assert harness.replies[-1] == WRONG_PIN
    assert await harness.context.security.lock_state.is_locked()
    assert harness.context.security.guard.failed_attempts == 1
    harness.audit.assert_any_await(AuditAction.LOGIN_FAILED, 42)
    state = harness.dispatcher.fsm.get_context(bot=harness.bot, chat_id=42, user_id=42)
    assert await state.get_state() is None


async def test_lockout(harness: Harness) -> None:
    for _ in range(5):
        await harness.send("/unlock")
        await harness.send("wrong-test-only")
    assert harness.replies[-1] == LOCKOUT
    assert harness.context.security.guard.is_blocked()
    await harness.send("/unlock")
    assert harness.replies[-1] == LOCKOUT
    assert harness.context.security.guard.failed_attempts == 5


async def test_lock(harness: Harness) -> None:
    await harness.context.security.lock_state.unlock()
    await harness.send("/lock")
    assert await harness.context.security.lock_state.is_locked()
    harness.audit.assert_any_await(AuditAction.SESSION_LOCKED, 42)


async def test_lock_menu_protected(harness: Harness) -> None:
    await harness.send("/menu")
    assert harness.replies[-1] == LOCKED


async def test_delete_failure_safe(harness: Harness, caplog: pytest.LogCaptureFixture) -> None:
    harness.api.fail_delete = True
    await harness.send("/unlock")
    await harness.send("test-pin-only")
    assert harness.replies[-1] == UNLOCKED
    assert "sensitive_message_delete_failed" in caplog.text
    assert "test-pin-only" not in caplog.text


async def test_nonowner_cannot_supply_pin(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send("test-pin-only", 99)
    assert await harness.context.security.lock_state.is_locked()
    assert harness.context.security.guard.failed_attempts == 0


async def test_pending_pin_cannot_dispatch_menu(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send("📅 Calendar")
    assert harness.replies[-1] == WRONG_PIN


async def test_lock_button_clears_pending_pin(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send("🔐 Lock")
    assert harness.replies[-1] == "🔐 Tizim qulflandi."
    state = harness.dispatcher.fsm.get_context(bot=harness.bot, chat_id=42, user_id=42)
    assert await state.get_state() is None


async def test_error_id_no_payload(harness: Harness, caplog: pytest.LogCaptureFixture) -> None:
    harness.sync.side_effect = RuntimeError("test-pin-only test-secret-token")
    await harness.send("/start")
    assert "Error ID:" in harness.replies[-1]
    assert "test-secret-token" not in caplog.text
    assert "test-pin-only" not in caplog.text
    assert await harness.context.security.lock_state.is_locked()


async def test_nontext_pin_clears_state(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send(None)
    assert harness.replies[-1] == WRONG_PIN
    state = harness.dispatcher.fsm.get_context(bot=harness.bot, chat_id=42, user_id=42)
    assert await state.get_state() is None


async def test_unknown_slash_pin_is_deleted(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send("/test-not-a-command")
    assert harness.replies[-1] == WRONG_PIN
    assert any(isinstance(call, DeleteMessage) for call in harness.api.calls)


async def test_help_during_pin_flow(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send("/help")
    assert "/unlock" in harness.replies[-1]
    assert harness.context.security.guard.failed_attempts == 0
