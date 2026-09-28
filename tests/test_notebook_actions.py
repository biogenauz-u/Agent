from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.modules.calendar.state import MemoryTemporaryStore
from app.modules.notebook.actions import NotebookActions
from app.modules.notebook.exceptions import NotebookConfirmationError

TODAY = date(2026, 9, 24)


async def test_create_confirmation_is_single_use() -> None:
    service = AsyncMock()
    service.create_note.return_value.id = 9
    actions = NotebookActions(service, MemoryTemporaryStore(), 42)
    token = await actions.prepare(
        "create", {"content": "private", "entry_date": TODAY.isoformat()}
    )
    assert await actions.confirm(token) == ("Yozuv saqlandi.", 9)
    with pytest.raises(NotebookConfirmationError):
        await actions.confirm(token)
    service.create_note.assert_awaited_once()


async def test_cancelled_confirmation_does_not_persist() -> None:
    service = AsyncMock()
    actions = NotebookActions(service, MemoryTemporaryStore(), 42)
    token = await actions.prepare("delete", {"id": 1})
    await actions.cancel(token)
    with pytest.raises(NotebookConfirmationError):
        await actions.confirm(token)
    service.delete_note.assert_not_awaited()
