"""Single-use confirmation boundary; callbacks contain only random action handles."""

from typing import Any
from uuid import uuid4

from app.modules.calendar.exceptions import CalendarError
from app.modules.calendar.oauth import GoogleOAuthService
from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventUpdate
from app.modules.calendar.service import CalendarService
from app.modules.calendar.state import TemporaryStore


class CalendarActions:
    def __init__(
        self,
        service: CalendarService,
        oauth: GoogleOAuthService,
        states: TemporaryStore,
        owner: int | None,
    ) -> None:
        self.service, self.oauth, self.states, self.owner = service, oauth, states, owner

    async def prepare(self, kind: str, data: dict[str, Any]) -> str:
        return await self.states.issue("action", {"kind": kind, "data": data, "owner": self.owner})

    async def confirm(self, token: str) -> str:
        await self.oauth.unlocked()
        action = await self.states.consume("action", token)
        if not action or action["owner"] != self.owner:
            raise CalendarError("Confirmation expired or already processed. Start again.")
        kind, data = action["kind"], action["data"]
        # Consume BEFORE side effects. Ambiguous network failures require inspecting /upcoming.
        if kind == "create":
            event = await self.service.create_event(
                CalendarEventCreate.model_validate(data), uuid4().hex
            )
            return (
                "Event yaratildi. Reminder setup failed; /reminders ni tekshiring."
                if getattr(event, "reminder_warning", False) is True
                else "Event yaratildi."
            )
        if kind == "update":
            event = await self.service.update_event(
                data["id"], CalendarEventUpdate.model_validate(data["event"]), data["etag"]
            )
            return (
                "Event yangilandi. Reminder sync failed; /reminders ni tekshiring."
                if getattr(event, "reminder_warning", False) is True
                else "Event yangilandi."
            )
        if kind == "delete":
            synced = await self.service.delete_event(data["id"], data["etag"])
            return (
                "Event o'chirildi."
                if synced
                else "Event o'chirildi. Reminder cancellation failed; /reminders ni tekshiring."
            )
        if kind == "disconnect":
            revoked = await self.oauth.disconnect()
            return (
                "Google Calendar uzildi."
                if revoked
                else "Stored credentials deleted. Remote revocation failed; remove access in your Google account."
            )
        raise CalendarError("Invalid confirmation.")

    async def cancel(self, token: str) -> None:
        await self.states.consume("action", token)
