from app.core.config import Settings
from app.database.models.task import TaskPriority
from app.database.session import DatabaseManager
from app.modules.calendar.runtime import CalendarRuntime
from app.modules.calendar.state import TemporaryStore
from app.modules.reminders.runtime import ReminderRuntime
from app.modules.tasks.actions import TaskActions
from app.modules.tasks.calendar_sync import TaskCalendarAdapter
from app.modules.tasks.reminders import TaskReminderAdapter
from app.modules.tasks.service import TaskService
from app.modules.tasks.utils import parse_local_time


class TaskRuntime:
    def __init__(
        self,
        settings: Settings,
        database: DatabaseManager,
        states: TemporaryStore,
        calendar: CalendarRuntime,
        reminders: ReminderRuntime | None,
    ) -> None:
        assert settings.telegram_owner_id is not None
        reminder = (
            TaskReminderAdapter(
                reminders.service,
                settings.timezone,
                parse_local_time(settings.task_date_only_reminder_time),
            )
            if reminders
            else None
        )
        calendar_sync = TaskCalendarAdapter(
            calendar.service, settings.calendar_default_event_duration_minutes
        )
        self.service = TaskService(
            database,
            settings.telegram_owner_id,
            settings.data_encryption_key,
            settings.timezone,
            settings.task_recent_limit,
            TaskPriority(settings.task_default_priority),
            settings.task_default_reminder_minutes,
            reminder,
            calendar_sync,
        )
        self.actions = TaskActions(self.service, states, settings.telegram_owner_id)

    async def close(self) -> None:
        return None

