"""One owner for shared resources across HTTP and Telegram transports."""

import asyncio
from contextlib import AsyncExitStack

from app.bot.lifecycle import TelegramRuntime
from app.bot.persistence import BotPersistence
from app.core.config import Settings
from app.core.exceptions import RedisConfigurationError, SecurityStateUnavailable
from app.core.runtime import RuntimeState
from app.database.session import DatabaseManager
from app.modules.assistant.runtime import AssistantRuntime
from app.modules.calendar.runtime import CalendarRuntime
from app.modules.daily.runtime import DailyRuntime
from app.modules.email.runtime import EmailRuntime
from app.modules.finance.runtime import FinanceRuntime
from app.modules.notebook.runtime import NotebookRuntime
from app.modules.personal_telegram.runtime import PersonalTelegramRuntime
from app.modules.reminders.exceptions import ReminderConfigurationError
from app.modules.reminders.runtime import ReminderRuntime
from app.modules.security.lock_service import LockService
from app.modules.security.redis_state import RedisLockService
from app.modules.tasks.runtime import TaskRuntime
from app.redis.health import check_redis_health
from app.redis.keys import SecurityKeys
from app.redis.manager import RedisManager


class ApplicationContext:
    """Explicit lifecycle; API-only never constructs Telegram or requires a PIN."""

    def __init__(self, settings: Settings, *, telegram: bool = False) -> None:
        self.settings = settings
        self.runtime = RuntimeState(
            telegram="configured" if settings.is_owner_configured else "not_configured",
            telegram_required=telegram,
            reminder_scheduler_required=telegram and settings.run_reminder_scheduler,
        )
        self.database: DatabaseManager | None = None
        self.redis: RedisManager | None = None
        self.lock = LockService()
        self.persistence = BotPersistence(None)
        self.telegram: TelegramRuntime | None = None
        self.calendar: CalendarRuntime | None = None
        self.reminders: ReminderRuntime | None = None
        self.email: EmailRuntime | None = None
        self.personal_telegram: PersonalTelegramRuntime | None = None
        self.finance: FinanceRuntime | None = None
        self.notebook: NotebookRuntime | None = None
        self.tasks: TaskRuntime | None = None
        self.assistant: AssistantRuntime | None = None
        self.daily: DailyRuntime | None = None
        self._resources: AsyncExitStack | None = None
        self._startup_lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._startup_lock:
            await self._start()

    async def _start(self) -> None:
        if self.runtime.startup_complete:
            return
        resources = AsyncExitStack()
        self._resources = resources
        try:
            if self.settings.database_url:
                self.database = DatabaseManager(self.settings)
                self.database.initialize()
                resources.push_async_callback(self.database.dispose)
            if self.settings.redis_url:
                self.redis = RedisManager(self.settings)
                self.redis.initialize()
                resources.push_async_callback(self.redis.close)
            if self.settings.session_lock_enabled and self.settings.security_state_backend == "redis":
                if self.redis is None:
                    raise RedisConfigurationError("REDIS_URL is required for redis security state.")
                if not await check_redis_health(self.redis.client):
                    raise SecurityStateUnavailable(
                        "Required Redis security service is unavailable."
                    )
                self.lock = RedisLockService(
                    self.redis.client,
                    SecurityKeys(
                        self.settings.redis_key_prefix,
                        self.settings.telegram_owner_id or 0,
                    ),
                )
            if not self.settings.session_lock_enabled:
                await self.lock.unlock()
            self.persistence.database = self.database
            self.calendar = CalendarRuntime(self.settings, self.database, self.redis, self.lock)
            resources.push_async_callback(self.calendar.close)
            if self.runtime.telegram_required:
                self.telegram = TelegramRuntime(
                    self.settings,
                    self.runtime,
                    self.persistence,
                    self.lock,
                    self.redis,
                )
                self.telegram.calendar = self.calendar
                resources.push_async_callback(self.telegram.close)
                await self.telegram.prepare()
            if self.database is not None and self.settings.telegram_owner_id and self.settings.data_encryption_key:
                self.email = EmailRuntime(
                    self.settings,
                    self.database,
                    self.redis,
                    self.lock,
                    self.telegram.bot if self.telegram else None,
                )
                resources.push_async_callback(self.email.close)
                connected = await self.email.connected()
                self.runtime.gmail = "connected" if connected else "not_connected"
                if self.telegram and self.telegram.context:
                    self.telegram.email = self.email
                    self.telegram.context.email = self.email
                if self.settings.run_gmail_monitor and connected:
                    self.email.monitor.start()
                    self.runtime.gmail = "monitoring"
            else:
                self.runtime.gmail = "not_configured"
            if self.settings.run_reminder_scheduler:
                if not self.runtime.telegram_required or self.telegram is None:
                    raise ReminderConfigurationError(
                        "RUN_REMINDER_SCHEDULER requires Telegram or combined run mode."
                    )
                if self.database is None:
                    raise ReminderConfigurationError(
                        "RUN_REMINDER_SCHEDULER requires DATABASE_URL."
                    )
                assert self.telegram.bot is not None
                owner = self.settings.telegram_owner_id
                if owner is None:
                    raise ReminderConfigurationError(
                        "Reminder scheduler requires TELEGRAM_OWNER_ID."
                    )
                self.reminders = ReminderRuntime(
                    self.settings,
                    self.database,
                    self.telegram.bot,
                    owner,
                    self.calendar.states,
                )
                self.calendar.service.reminder_sync = self.reminders.service
                self.telegram.reminders = self.reminders
                assert self.telegram.context is not None
                self.telegram.context.reminders = self.reminders
                resources.push_async_callback(self.reminders.close)
                try:
                    await self.reminders.start()
                    self.runtime.reminder_scheduler = "running"
                except BaseException:
                    self.runtime.reminder_scheduler = "error"
                    raise
            if not self.settings.personal_telegram_enabled:
                self.runtime.personal_telegram = "disabled"
            elif not (
                self.database
                and self.settings.telegram_owner_id
                and self.settings.data_encryption_key
                and self.settings.telegram_api_id
                and self.settings.telegram_api_hash
            ):
                self.runtime.personal_telegram = "not_configured"
            else:
                self.personal_telegram = PersonalTelegramRuntime(
                    self.settings,
                    self.database,
                    self.runtime,
                    self.telegram.bot if self.telegram else None,
                )
                resources.push_async_callback(self.personal_telegram.close)
                await self.personal_telegram.start()
                if self.telegram and self.telegram.context:
                    self.telegram.personal_telegram = self.personal_telegram
                    self.telegram.context.personal_telegram = self.personal_telegram
            if self.database and self.settings.telegram_owner_id:
                self.finance = FinanceRuntime(
                    self.settings, self.database, self.calendar.states
                )
                resources.push_async_callback(self.finance.close)
                await self.finance.start()
                if self.telegram and self.telegram.context:
                    self.telegram.finance = self.finance
                    self.telegram.context.finance = self.finance
            if (
                self.database
                and self.settings.telegram_owner_id
                and self.settings.data_encryption_key
                and self.settings.notebook_storage_path
            ):
                self.notebook = NotebookRuntime(
                    self.settings, self.database, self.calendar.states
                )
                resources.push_async_callback(self.notebook.close)
                try:
                    await self.notebook.start()
                    self.runtime.notebook_storage = "available"
                except BaseException:
                    self.runtime.notebook_storage = "error"
                    raise
                if self.telegram and self.telegram.context:
                    self.telegram.notebook = self.notebook
                    self.telegram.context.notebook = self.notebook
            else:
                self.runtime.notebook_storage = "not_configured"
            if (
                self.database
                and self.settings.telegram_owner_id
                and self.settings.data_encryption_key
            ):
                self.tasks = TaskRuntime(
                    self.settings,
                    self.database,
                    self.calendar.states,
                    self.calendar,
                    self.reminders,
                )
                resources.push_async_callback(self.tasks.close)
                if self.telegram and self.telegram.context:
                    self.telegram.tasks = self.tasks
                    self.telegram.context.tasks = self.tasks
            if (
                self.settings.ai_provider
                and self.settings.ai_model
                and self.settings.ai_api_key
                and self.settings.telegram_owner_id
            ):
                self.assistant = AssistantRuntime(self.settings, self)
                resources.push_async_callback(self.assistant.close)
                if self.telegram and self.telegram.context:
                    self.telegram.assistant = self.assistant
                    self.telegram.context.assistant = self.assistant
            if (
                self.database
                and self.telegram
                and self.telegram.bot
                and self.settings.telegram_owner_id
                and self.tasks
            ):
                self.daily = DailyRuntime(
                    self.settings, self.database, self.telegram.bot, self
                )
                self.telegram.daily = self.daily
                assert self.telegram.context is not None
                self.telegram.context.daily = self.daily
                resources.push_async_callback(self.daily.close)
                if self.settings.run_daily_automation:
                    try:
                        await self.daily.start()
                        self.runtime.daily_automation = "running"
                    except BaseException:
                        self.runtime.daily_automation = "error"
                        raise
            self.runtime.startup_complete = True
        except BaseException:
            await self.close()
            raise

    async def close(self) -> None:
        self.runtime.startup_complete = False
        if self.runtime.reminder_scheduler == "running":
            self.runtime.reminder_scheduler = "stopped"
        if self.runtime.gmail == "monitoring":
            self.runtime.gmail = "stopped"
        if self.runtime.daily_automation == "running":
            self.runtime.daily_automation = "stopped"
        resources, self._resources = self._resources, None
        if resources is not None:
            await resources.aclose()
