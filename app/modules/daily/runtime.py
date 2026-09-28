from aiogram import Bot

from app.core.config import Settings
from app.database.session import DatabaseManager
from app.modules.daily.repository import DailyRepository
from app.modules.daily.scheduler import DailyScheduler
from app.modules.daily.service import DailyAutomationService


class DailyRuntime:
    def __init__(self, settings: Settings, database: DatabaseManager, bot: Bot, application) -> None:
        assert settings.telegram_owner_id is not None
        self.repository = DailyRepository(database, settings.telegram_owner_id)
        self.service = DailyAutomationService(application, self.repository, bot, settings.telegram_owner_id)
        self.scheduler = DailyScheduler(
            self.service,
            self.repository,
            settings.timezone,
            settings.daily_morning_time,
            settings.daily_evening_time,
            settings.daily_automation_grace_minutes,
            scheduler=(application.reminders.scheduler.scheduler if application.reminders else None),
        )
        self.states = application.calendar.states

    async def start(self) -> None:
        await self.scheduler.start()

    async def close(self) -> None:
        await self.scheduler.shutdown()
