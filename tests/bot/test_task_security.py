import pytest

from app.bot.constants import LOCKED

from .conftest import Harness


@pytest.mark.parametrize(
    "command",
    [
        "/tasks_menu", "/task", "/tasks", "/task_today", "/task_tomorrow",
        "/task_overdue", "/task_done 1", "/task_edit 1 title x",
        "/task_delete 1", "/task_priority 1 HIGH", "/task_calendar 1", "/task_carry",
    ],
)
async def test_task_management_blocked_while_locked(harness: Harness, command: str) -> None:
    await harness.send(command)
    assert harness.replies[-1] == LOCKED
