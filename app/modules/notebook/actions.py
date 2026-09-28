from datetime import date
from typing import Any

from app.modules.calendar.state import TemporaryStore
from app.modules.notebook.exceptions import NotebookConfirmationError
from app.modules.notebook.schemas import NoteCreate, NoteUpdate
from app.modules.notebook.service import NotebookService


class NotebookActions:
    """Single-use mutation confirmations; note content never enters callback data."""

    def __init__(self, service: NotebookService, states: TemporaryStore, owner_id: int) -> None:
        self.service, self.states, self.owner_id = service, states, owner_id

    async def prepare(self, kind: str, data: dict[str, Any]) -> str:
        return await self.states.issue(
            "notebook_action", {"kind": kind, "data": data, "owner": self.owner_id}
        )

    async def cancel(self, token: str) -> None:
        await self.states.consume("notebook_action", token)

    async def confirm(self, token: str) -> tuple[str, int | None]:
        action = await self.states.consume("notebook_action", token)
        if not action or action.get("owner") != self.owner_id:
            raise NotebookConfirmationError("Confirmation expired or already processed.")
        kind, data = action["kind"], dict(action["data"])
        if kind == "create":
            data["entry_date"] = date.fromisoformat(data["entry_date"])
            note = await self.service.create_note(NoteCreate(**data))
            return "Yozuv saqlandi.", note.id
        if kind == "update":
            note_id = int(data.pop("id"))
            if "entry_date" in data:
                data["entry_date"] = date.fromisoformat(data["entry_date"])
            await self.service.update_note(note_id, NoteUpdate(**data))
            return "Yozuv yangilandi.", note_id
        if kind == "delete":
            note_id = int(data["id"])
            await self.service.delete_note(note_id)
            return "Yozuv o'chirildi.", note_id
        raise NotebookConfirmationError("Invalid notebook confirmation.")

