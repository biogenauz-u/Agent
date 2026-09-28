from aiogram import Bot

from app.core.config import Settings
from app.database.session import DatabaseManager
from app.modules.reminders.actions import ReminderActions
from app.modules.reminders.audit import ReminderAudit
from app.modules.reminders.delivery import TelegramReminderDelivery
from app.modules.reminders.dispatcher import ReminderDispatcher
from app.modules.reminders.scheduler import ReminderScheduler
from app.modules.reminders.service import ReminderService


class ReminderRuntime:
    """Composition root for one explicitly enabled scheduler owner."""

    def __init__(
        self, settings: Settings, database: DatabaseManager, bot: Bot, owner_id: int, states
    ) -> None:
        self.timezone = settings.timezone
        self.audit = ReminderAudit(database, owner_id)
        self.service = ReminderService(
            database,
            owner_id,
            settings.reminder_max_attempts,
            settings.reminder_default_offset_minutes,
        )
        self.delivery = TelegramReminderDelivery(bot, owner_id, settings.timezone)
        self.dispatcher = ReminderDispatcher(
            database,
            self.delivery,
            self.audit,
            settings.reminder_retry_delays,
        )
        self.scheduler = ReminderScheduler(
            database,
            self.dispatcher,
            self.audit,
            settings.reminder_overdue_grace_minutes,
            settings.reminder_processing_timeout_minutes,
        )
        self.service.scheduler = self.scheduler
        self.actions = ReminderActions(self.service, states, owner_id)

    async def start(self) -> None:
        await self.scheduler.start()

    async def close(self) -> None:
        await self.scheduler.shutdown()
