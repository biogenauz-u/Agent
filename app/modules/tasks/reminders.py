from datetime import datetime, time
from typing import Protocol
from zoneinfo import ZoneInfo

from app.modules.reminders.schemas import ReminderCreate
from app.modules.reminders.service import ReminderService
from app.modules.tasks.exceptions import TaskValidationError
from app.modules.tasks.utils import reminder_moment


class TaskReminderPort(Protocol):
    async def create(
        self,
        task_id: int,
        title: str,
        due_date,
        due_at: datetime | None,
        offset: int,
        now: datetime,
    ) -> int: ...
    async def cancel(self, reminder_id: int) -> None: ...
    async def reschedule(
        self,
        reminder_id: int,
        due_date,
        due_at: datetime | None,
        offset: int,
        now: datetime,
    ) -> None: ...


class TaskReminderAdapter:
    def __init__(
        self, service: ReminderService, timezone: ZoneInfo, date_only_time: time
    ) -> None:
        self.service, self.timezone, self.date_only_time = service, timezone, date_only_time

    def moment(self, due_date, due_at, offset: int, now: datetime) -> datetime:
        moment = reminder_moment(
            due_date, due_at, offset, self.date_only_time, self.timezone
        )
        if moment is None or moment <= now:
            raise TaskValidationError("Task reminder would be in the past.")
        return moment

    async def create(self, task_id, title, due_date, due_at, offset, now) -> int:
        moment = self.moment(due_date, due_at, offset, now)
        reminder = await self.service.create_standalone(
            ReminderCreate(
                title=f"Task eslatmasi: {title}",
                message=f"Task ID: {task_id}",
                remind_at=moment,
            )
        )
        return reminder.id

    async def cancel(self, reminder_id: int) -> None:
        await self.service.cancel(reminder_id)

    async def reschedule(self, reminder_id, due_date, due_at, offset, now) -> None:
        await self.service.reschedule(
            reminder_id, self.moment(due_date, due_at, offset, now)
        )

