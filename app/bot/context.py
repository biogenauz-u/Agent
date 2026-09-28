from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.bot.persistence import BotPersistence
from app.modules.calendar.runtime import CalendarRuntime
from app.modules.email.runtime import EmailRuntime
from app.modules.finance.runtime import FinanceRuntime
from app.modules.notebook.runtime import NotebookRuntime
from app.modules.personal_telegram.runtime import PersonalTelegramRuntime
from app.modules.reminders.runtime import ReminderRuntime
from app.modules.security.service import SecurityService
from app.modules.tasks.runtime import TaskRuntime

if TYPE_CHECKING:
    from app.modules.assistant.runtime import AssistantRuntime
    from app.modules.daily.runtime import DailyRuntime


@dataclass(repr=False)
class BotContext:
    owner_id: int
    timezone: str
    security: SecurityService
    persistence: BotPersistence
    session_lock_enabled: bool = True
    calendar: CalendarRuntime | None = None
    reminders: ReminderRuntime | None = None
    email: EmailRuntime | None = None
    personal_telegram: PersonalTelegramRuntime | None = None
    finance: FinanceRuntime | None = None
    notebook: NotebookRuntime | None = None
    tasks: TaskRuntime | None = None
    assistant: "AssistantRuntime | None" = None
    daily: "DailyRuntime | None" = None
