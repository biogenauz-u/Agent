from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.constants import LOCKED

from .conftest import Harness


@pytest.mark.parametrize("command", ["/daily", "/daily_settings", "/morning_now", "/evening_now"])
async def test_daily_commands_blocked_while_locked(harness: Harness, command: str) -> None:
    harness.context.daily = SimpleNamespace(service=SimpleNamespace(morning_text=AsyncMock()))
    await harness.send(command)
    assert harness.replies[-1] == LOCKED
    harness.context.daily.service.morning_text.assert_not_awaited()


async def test_manual_morning_and_evening_work_unlocked(harness: Harness) -> None:
    service = SimpleNamespace(
        morning_text=AsyncMock(return_value="morning"),
        evening_text=AsyncMock(return_value=("evening", [])),
    )
    harness.context.daily = SimpleNamespace(service=service)
    await harness.context.security.lock_state.unlock()
    await harness.send("/morning_now")
    await harness.send("/evening_now")
    assert harness.replies[-2:] == ["morning", "evening"]
    service.morning_text.assert_awaited_once()
    service.evening_text.assert_awaited_once()
