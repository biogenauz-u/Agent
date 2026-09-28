from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.modules.calendar.state import MemoryTemporaryStore
from app.modules.tasks.actions import TaskActions
from app.modules.tasks.exceptions import TaskConfirmationError


async def test_create_confirmation_single_use() -> None:
    service = AsyncMock()
    service.create_task.return_value.id = 5
    actions = TaskActions(service, MemoryTemporaryStore(), 42)
    token = await actions.prepare("create", {"title": "task", "due_date": date(2026, 9, 24).isoformat()})
    assert await actions.confirm(token) == "Task saqlandi. ID: 5"
    with pytest.raises(TaskConfirmationError):
        await actions.confirm(token)
    service.create_task.assert_awaited_once()


@pytest.mark.parametrize("kind", ["complete", "delete"])
async def test_mutation_requires_confirmation(kind: str) -> None:
    service = AsyncMock()
    actions = TaskActions(service, MemoryTemporaryStore(), 42)
    token = await actions.prepare(kind, {"id": 1})
    await actions.cancel(token)
    with pytest.raises(TaskConfirmationError):
        await actions.confirm(token)
