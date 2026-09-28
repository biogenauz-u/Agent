import pytest

from app.bot.constants import LOCKED, PLACEHOLDER

from .conftest import Harness


@pytest.mark.parametrize("command", ["/help", "/status", "/start"])
async def test_public_owner_commands_while_locked(harness: Harness, command: str) -> None:
    await harness.send(command)
    assert harness.replies
    assert harness.replies[-1] != LOCKED
    assert "Error ID" not in harness.replies[-1]


async def test_status_reports_unconfigured(harness: Harness) -> None:
    await harness.send("/status")
    assert "Database: Not configured" in harness.replies[-1]
    assert "Session: Locked" in harness.replies[-1]
    assert "Connected" not in harness.replies[-1]


async def test_start_sync(harness: Harness) -> None:
    await harness.send("/start")
    harness.sync.assert_awaited_once_with(42, username=None, first_name="Test", last_name=None)


async def test_start_unlocked(harness: Harness) -> None:
    await harness.context.security.lock_state.unlock()
    await harness.send("/start")
    assert "Tizim tayyor" in harness.replies[-1]


async def test_menu_unlocked(harness: Harness) -> None:
    await harness.context.security.lock_state.unlock()
    await harness.send("/menu")
    assert harness.replies[-1] == "Menyu"


async def test_module_unlocked(harness: Harness) -> None:
    await harness.context.security.lock_state.unlock()
    await harness.send("📅 Calendar")
    assert harness.replies[-1] == PLACEHOLDER


async def test_module_locked(harness: Harness) -> None:
    await harness.send("📅 Calendar")
    assert harness.replies[-1] == LOCKED
