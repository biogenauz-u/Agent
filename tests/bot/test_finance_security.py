import pytest

from app.bot.constants import LOCKED

from .conftest import Harness


@pytest.mark.parametrize(
    "command",
    [
        "/finance",
        "/expense",
        "/income",
        "/transactions",
        "/finance_today",
        "/finance_edit",
        "/finance_delete",
    ],
)
async def test_finance_commands_blocked_while_locked(harness: Harness, command: str) -> None:
    await harness.send(command)
    assert harness.replies[-1] == LOCKED
