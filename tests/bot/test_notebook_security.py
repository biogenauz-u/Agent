import pytest

from app.bot.constants import LOCKED, LOCKED_ALLOWED_COMMANDS

from .conftest import Harness


@pytest.mark.parametrize(
    "command",
    [
        "notebook",
        "note",
        "notes",
        "note_today",
        "note_date",
        "note_project",
        "note_tag",
        "note_search",
        "note_edit",
        "note_delete",
        "note_attach",
        "notebook_projects",
        "notebook_tags",
    ],
)
async def test_locked_session_blocks_notebook_commands(
    harness: Harness, command: str
) -> None:
    await harness.send(f"/{command}")
    assert harness.replies[-1] == LOCKED
    assert command not in LOCKED_ALLOWED_COMMANDS
