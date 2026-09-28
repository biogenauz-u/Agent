from typing import Any

from app.modules.calendar.state import TemporaryStore
from app.modules.reminders.exceptions import ReminderError
from app.modules.reminders.schemas import ReminderCreate
from app.modules.reminders.service import ReminderService


class ReminderActions:
    """Single-use confirmation handles for persistent reminder changes."""

    def __init__(self, service: ReminderService, states: TemporaryStore, owner_id: int) -> None:
        self.service, self.states, self.owner_id = service, states, owner_id

    async def prepare(self, kind: str, data: dict[str, Any]) -> str:
        return await self.states.issue(
            "reminder_action", {"kind": kind, "data": data, "owner": self.owner_id}
        )

    async def cancel_action(self, token: str) -> None:
        await self.states.consume("reminder_action", token)

    async def confirm(self, token: str) -> str:
        action = await self.states.consume("reminder_action", token)
        if not action or action["owner"] != self.owner_id:
            raise ReminderError("Confirmation expired or already processed.")
        if action["kind"] == "create":
            await self.service.create_standalone(ReminderCreate.model_validate(action["data"]))
            return "Reminder saqlandi."
        if action["kind"] == "cancel":
            await self.service.cancel(int(action["data"]["id"]))
            return "Reminder bekor qilindi."
        raise ReminderError("Invalid reminder confirmation.")
