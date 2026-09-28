"""Telegram resources borrowed from a shared application context."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.base import DefaultKeyBuilder
from asyncpg import PostgresError
from sqlalchemy.exc import SQLAlchemyError

from app.bot.constants import COMMANDS
from app.bot.context import BotContext
from app.bot.dispatcher import create_dispatcher
from app.bot.factory import create_bot, require_owner
from app.bot.persistence import BotPersistence
from app.bot.storage import SharedRedisStorage
from app.core.config import Settings
from app.core.logging import report_error
from app.core.runtime import RuntimeState
from app.modules.assistant.runtime import AssistantRuntime
from app.modules.audit.actions import AuditAction
from app.modules.calendar.runtime import CalendarRuntime
from app.modules.daily.runtime import DailyRuntime
from app.modules.email.runtime import EmailRuntime
from app.modules.finance.runtime import FinanceRuntime
from app.modules.notebook.runtime import NotebookRuntime
from app.modules.personal_telegram.runtime import PersonalTelegramRuntime
from app.modules.reminders.runtime import ReminderRuntime
from app.modules.security.lock_service import LockService
from app.modules.security.pin_service import PinService
from app.modules.security.redis_service import RedisSecurityService
from app.modules.security.redis_state import RedisUnlockGuard
from app.modules.security.service import SecurityService
from app.modules.security.unlock_guard import UnlockGuard
from app.modules.tasks.runtime import TaskRuntime
from app.redis.keys import SecurityKeys
from app.redis.manager import RedisManager


class TelegramRuntime:
    def __init__(
        self,
        settings: Settings,
        runtime: RuntimeState,
        persistence: BotPersistence,
        lock: LockService,
        redis: RedisManager | None,
    ) -> None:
        self.settings, self.runtime, self.persistence = settings, runtime, persistence
        self.lock, self.redis = lock, redis
        self.bot: Bot | None = None
        self.dispatcher: Dispatcher | None = None
        self.context: BotContext | None = None
        self.calendar: CalendarRuntime | None = None
        self.reminders: ReminderRuntime | None = None
        self.email: EmailRuntime | None = None
        self.personal_telegram: PersonalTelegramRuntime | None = None
        self.finance: FinanceRuntime | None = None
        self.notebook: NotebookRuntime | None = None
        self.tasks: TaskRuntime | None = None
        self.assistant: AssistantRuntime | None = None
        self.daily: DailyRuntime | None = None
        self._closed = False
        self._started = False
        self._stopping = False
        self._poll_task: asyncio.Task[None] | None = None

    async def audit(self, action: AuditAction) -> None:
        try:
            await self.persistence.audit(action)
        except (SQLAlchemyError, PostgresError) as error:
            # Lifecycle audit failure must not prevent startup or resource cleanup.
            report_error(logging.getLogger(__name__), error)

    async def prepare(self) -> None:
        from aiogram.types import BotCommand, BotCommandScopeChat

        owner = require_owner(self.settings)
        pin = await asyncio.to_thread(PinService.from_settings, self.settings)
        self.bot = create_bot(self.settings)
        storage = None
        isolation = None
        if self.settings.security_state_backend == "redis":
            assert self.redis is not None
            keys = SecurityKeys(self.settings.redis_key_prefix, owner)
            guard = RedisUnlockGuard(
                self.redis.client,
                keys,
                self.settings.bot_unlock_max_attempts,
                self.settings.bot_unlock_lockout_seconds,
            )
            security = RedisSecurityService(self.redis.client, keys, pin, guard)
            security.lock_state = self.lock
            storage = SharedRedisStorage(
                self.redis.client,
                key_builder=DefaultKeyBuilder(
                    prefix=f"{self.settings.redis_key_prefix}:fsm",
                    with_bot_id=True,
                ),
            )
            isolation = storage.create_isolation(lock_kwargs={"timeout": 60, "blocking_timeout": 5})
        else:
            security = SecurityService(
                self.lock,
                pin,
                UnlockGuard(
                    self.settings.bot_unlock_max_attempts,
                    self.settings.bot_unlock_lockout_seconds,
                ),
            )
        self.context = BotContext(
            owner,
            self.settings.app_timezone,
            security,
            self.persistence,
            session_lock_enabled=self.settings.session_lock_enabled,
        )
        self.context.calendar = self.calendar
        self.context.email = self.email
        self.context.personal_telegram = self.personal_telegram
        self.context.finance = self.finance
        self.context.notebook = self.notebook
        self.context.tasks = self.tasks
        self.context.assistant = self.assistant
        self.context.daily = self.daily
        self.dispatcher = create_dispatcher(self.context, storage=storage, isolation=isolation)
        commands = {
            name: text
            for name, text in COMMANDS.items()
            if self.settings.session_lock_enabled or name not in {"lock", "unlock"}
        }
        await self.bot.set_my_commands(
            [BotCommand(command=name, description=text) for name, text in commands.items()],
            scope=BotCommandScopeChat(chat_id=owner),
        )

    async def poll(self, handle_signals: bool = True) -> None:
        assert self.bot is not None and self.dispatcher is not None
        await self.audit(AuditAction.BOT_STARTED)
        self._started = True
        if self._stopping:
            return
        self.runtime.telegram = "running"
        try:
            self._poll_task = asyncio.create_task(
                self.dispatcher.start_polling(
                    self.bot,
                    allowed_updates=["message", "callback_query"],
                    handle_as_tasks=False,
                    close_bot_session=False,
                    handle_signals=handle_signals,
                ),
                name="aiogram-polling",
            )
            await asyncio.shield(self._poll_task)
        except asyncio.CancelledError:
            await self.stop()
            raise
        except Exception:
            self.runtime.telegram = "error"
            raise
        finally:
            if self.runtime.telegram != "error":
                self.runtime.telegram = "stopped"

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self.stop()
            if self._started:
                await self.audit(AuditAction.BOT_STOPPED)
        finally:
            try:
                if self.dispatcher is not None:
                    await self.dispatcher.fsm.close()
            finally:
                if self.bot is not None:
                    await self.bot.session.close()

    async def stop(self) -> None:
        self._stopping = True
        if (
            self.dispatcher is not None
            and self._poll_task is not None
            and not self._poll_task.done()
        ):
            await asyncio.sleep(0)
            try:
                await self.dispatcher.stop_polling()
            except RuntimeError:
                if not self._poll_task.done():
                    self._poll_task.cancel()
            await asyncio.gather(self._poll_task, return_exceptions=True)
