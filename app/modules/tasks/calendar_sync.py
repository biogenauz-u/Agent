import hashlib
from datetime import timedelta
from typing import Protocol

from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventUpdate
from app.modules.calendar.service import CalendarService
from app.modules.tasks.exceptions import TaskValidationError


class TaskCalendarPort(Protocol):
    async def create(self, task_id: int, title: str, due_at) -> str: ...
    async def update(self, event_id: str, title: str, due_at) -> None: ...


class TaskCalendarAdapter:
    def __init__(self, service: CalendarService, duration_minutes: int) -> None:
        self.service, self.duration_minutes = service, duration_minutes

    def event(self, title: str, due_at) -> CalendarEventCreate:
        if due_at is None:
            raise TaskValidationError("Calendar sync currently requires a due time.")
        return CalendarEventCreate(
            title=title,
            start=due_at,
            end=due_at + timedelta(minutes=self.duration_minutes),
            description="Personal AI Assistant task",
            reminders=[],
        )

    async def create(self, task_id: int, title: str, due_at) -> str:
        action_id = hashlib.sha256(f"task:{task_id}".encode()).hexdigest()[:32]
        result = await self.service.create_event(self.event(title, due_at), action_id)
        return result.id

    async def update(self, event_id: str, title: str, due_at) -> None:
        current = await self.service.get_event(event_id)
        event = self.event(title, due_at)
        await self.service.update_event(
            event_id,
            CalendarEventUpdate(**event.model_dump(), fields={"title", "start", "end"}),
            current.etag,
        )

