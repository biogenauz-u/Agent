# Stage 1 Step 3 - Complete File Contents

Repository: C:/Users/USER/Documents/Agent

## Summary

Private Aiogram polling bot with central owner/private-chat authorization, default-locked sessions, Argon2id PIN verification, FSM input cleanup, bounded failed-attempt policy, commands and placeholder menus. Persistence adapts existing Step 2 services and reports unavailable audits explicitly. Structured logs omit raw exception strings and payloads. Resources close on startup and polling failures. Step 4 is not implemented.

## Verification Results

- PASS: 89 tests, including all 37 prior Step 1/2 tests and 52 Step 3 tests.
- PASS: compileall app scripts tests.
- PASS: Ruff app scripts tests.
- PASS: pip check (no broken requirements).
- PASS: startup without owner configuration returns exit code 1 and a safe explicit message; no Telegram request is made.
- BLOCKED: live Telegram runtime: TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID and BOT_PIN/BOT_PIN_HASH are unset.
- BLOCKED: live PostgreSQL integration: DATABASE_URL is unset; prior live database verification remains outstanding.
- BLOCKED: full live runtime verification. All executable offline checks passed.

Tests use an offline Telegram session and isolated SQLite databases. No live Telegram API calls were made. PostgreSQL migrations were not changed or applied in this step. Audit enum storage remains strings, so new action names need no schema migration.

## Important Limits

One process only. Restart clears failed attempts and FSM, and restarts locked. No idle lock or PIN prompt expiry yet. The lock store is replaceable; Redis sharing is future work. Telegram bot chats are not end-to-end encrypted and PIN deletion is best-effort. Use a strong PIN/passphrase; prefer BOT_PIN_HASH. Never paste credentials into logs or review reports. The generated hash helper uses a hidden terminal prompt. Existing configuration and database layers are preserved; the existing audit enum test now includes the two new session actions.

## Changed Files

- `.env.example`
- `app/bot/__init__.py`
- `app/bot/constants.py`
- `app/bot/context.py`
- `app/bot/dispatcher.py`
- `app/bot/errors.py`
- `app/bot/factory.py`
- `app/bot/handlers/__init__.py`
- `app/bot/handlers/common.py`
- `app/bot/handlers/menu.py`
- `app/bot/handlers/security.py`
- `app/bot/keyboards/__init__.py`
- `app/bot/keyboards/main_menu.py`
- `app/bot/middlewares/__init__.py`
- `app/bot/middlewares/lock_state.py`
- `app/bot/middlewares/owner_auth.py`
- `app/bot/persistence.py`
- `app/bot/run.py`
- `app/bot/states.py`
- `app/bot/transport.py`
- `app/core/config.py`
- `app/core/exceptions.py`
- `app/core/logging.py`
- `app/modules/audit/actions.py`
- `app/modules/security/__init__.py`
- `app/modules/security/lock_service.py`
- `app/modules/security/pin_service.py`
- `app/modules/security/service.py`
- `app/modules/security/unlock_guard.py`
- `app/modules/users/service.py`
- `README.md`
- `scripts/hash_pin.py`
- `tests/bot/__init__.py`
- `tests/bot/conftest.py`
- `tests/bot/test_bot_commands.py`
- `tests/bot/test_bot_factory.py`
- `tests/bot/test_lifecycle.py`
- `tests/bot/test_lock_service.py`
- `tests/bot/test_owner_authorization.py`
- `tests/bot/test_persistence.py`
- `tests/bot/test_security_handlers.py`
- `tests/test_audit_service.py`

## Complete Final Contents

### C:/Users/USER/Documents/Agent/.env.example

````text
APP_ENV=development
APP_DEBUG=true
APP_TIMEZONE=Asia/Tashkent
LOG_LEVEL=INFO

TELEGRAM_BOT_TOKEN=
TELEGRAM_OWNER_ID=
TELEGRAM_API_ID=
TELEGRAM_API_HASH=

# PostgreSQL format (placeholders only):
# postgresql+asyncpg://USER:PASSWORD@localhost:5432/personal_ai
# Percent-encode special characters in credentials. Never commit real credentials.
DATABASE_URL=
# Redis will be configured in a later step.
REDIS_URL=

# Supply a cryptographically random secret before enabling authentication.
SECRET_KEY=
# Configure a strong private PIN when the lock feature is implemented.
BOT_PIN=
# Preferred Argon2id hash. Plain BOT_PIN is accepted only in development.
BOT_PIN_HASH=
BOT_UNLOCK_MAX_ATTEMPTS=5
BOT_UNLOCK_LOCKOUT_SECONDS=300
````

### C:/Users/USER/Documents/Agent/app/bot/__init__.py

````python
"""Private Telegram transport; imports never start polling."""
````

### C:/Users/USER/Documents/Agent/app/bot/constants.py

````python
"""Public commands and labels; never derive audit fields from arbitrary message text."""

COMMANDS = {
    "start": "Bosh sahifa",
    "help": "Yordam",
    "status": "Tizim holati",
    "id": "Telegram ID",
    "menu": "Menyu",
    "lock": "Qulflash",
    "unlock": "Ochish",
}
LOCKED_ALLOWED_COMMANDS = frozenset({"start", "help", "status", "id", "unlock", "lock"})
HOME = "🏠 Bosh sahifa"
LOCK = "🔐 Lock"
MODULE_LABELS = (
    "📅 Calendar",
    "✅ Tasks",
    "⏰ Reminders",
    "📧 Email",
    "💬 Telegram",
    "💰 Finance",
    "📝 Notebook",
    "🔎 Search",
    "⚙️ Settings",
)
DENIED = "⛔ Access denied."
LOCKED = "🔐 Tizim qulflangan. Davom etish uchun /unlock buyrug‘idan foydalaning."
PLACEHOLDER = "🚧 Bu modul keyingi bosqichda ishga tushiriladi."
PIN_PROMPT = "🔐 PIN kodni kiriting."
UNLOCKED = "🔓 Tizim ochildi."
WRONG_PIN = "❌ PIN noto‘g‘ri."
LOCKOUT = "⏳ Urinishlar vaqtincha bloklandi. Keyinroq /unlock orqali qayta urinib ko‘ring."


def command_name(text: str | None) -> str | None:
    if not text or not text.startswith("/"):
        return None
    name = text.split(maxsplit=1)[0][1:].split("@", maxsplit=1)[0]
    return name if name in COMMANDS else None
````

### C:/Users/USER/Documents/Agent/app/bot/context.py

````python
from dataclasses import dataclass

from app.bot.persistence import BotPersistence
from app.modules.security.service import SecurityService


@dataclass(repr=False)
class BotContext:
    owner_id: int
    timezone: str
    security: SecurityService
    persistence: BotPersistence
````

### C:/Users/USER/Documents/Agent/app/bot/dispatcher.py

````python
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation

from app.bot.context import BotContext
from app.bot.errors import SafeErrorMiddleware
from app.bot.handlers import common, menu, security
from app.bot.middlewares.lock_state import LockStateMiddleware
from app.bot.middlewares.owner_auth import OwnerAuthMiddleware


def create_dispatcher(context: BotContext) -> Dispatcher:
    """Authorize before allocating FSM state; isolate owner updates before lock checks."""
    dispatcher = Dispatcher(
        storage=MemoryStorage(),
        events_isolation=SimpleEventIsolation(),
        disable_fsm=True,
        app_context=context,
    )
    dispatcher.update.outer_middleware(SafeErrorMiddleware(context))
    dispatcher.update.outer_middleware(OwnerAuthMiddleware(context))
    dispatcher.update.outer_middleware(dispatcher.fsm)
    dispatcher.update.outer_middleware(LockStateMiddleware(context))
    dispatcher.include_routers(
        security.create_router(), common.create_router(), menu.create_router()
    )
    return dispatcher
````

### C:/Users/USER/Documents/Agent/app/bot/errors.py

````python
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.bot.constants import DENIED
from app.bot.context import BotContext
from app.bot.transport import safe_reply, update_event
from app.core.logging import report_error

logger = logging.getLogger(__name__)


class SafeErrorMiddleware(BaseMiddleware):
    """Last-resort boundary: safe stack locations, error ID and fail-closed lock state."""

    def __init__(self, context: BotContext) -> None:
        self.context = context

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as error:  # noqa: BLE001 - central transport error boundary
            error_id = report_error(logger, error)
            await self.context.security.lock()
            if state := data.get("state"):
                await state.clear()
            incoming = update_event(event) if isinstance(event, Update) else None
            text = (
                f"⚠️ Xatolik yuz berdi.\n\nError ID: {error_id}"
                if data.get("owner_authorized")
                else DENIED
            )
            await safe_reply(incoming, text)
            return None
````

### C:/Users/USER/Documents/Agent/app/bot/factory.py

````python
from aiogram import Bot
from aiogram.utils.token import TokenValidationError

from app.core.config import Settings
from app.core.exceptions import TelegramConfigurationError


def require_owner(settings: Settings) -> int:
    if settings.telegram_owner_id is None:
        raise TelegramConfigurationError("TELEGRAM_OWNER_ID is not configured.")
    return settings.telegram_owner_id


def create_bot(settings: Settings) -> Bot:
    """Create without network calls; reveal the token only at the Aiogram boundary."""
    if not settings.telegram_bot_token:
        raise TelegramConfigurationError("TELEGRAM_BOT_TOKEN is not configured.")
    require_owner(settings)
    try:
        return Bot(token=settings.telegram_bot_token.get_secret_value())
    except TokenValidationError:
        raise TelegramConfigurationError("TELEGRAM_BOT_TOKEN is invalid.") from None
````

### C:/Users/USER/Documents/Agent/app/bot/handlers/__init__.py

````python
"""Small Telegram command adapters; services own business/security behavior."""
````

### C:/Users/USER/Documents/Agent/app/bot/handlers/common.py

````python
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.constants import COMMANDS, HOME, MODULE_LABELS
from app.bot.context import BotContext
from app.bot.keyboards.main_menu import main_menu


async def start(message: Message, app_context: BotContext) -> None:
    user = message.from_user
    if user is not None:
        await app_context.persistence.synchronize(
            user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
    if await app_context.security.lock_state.is_locked():
        await message.answer(
            "👋 Personal AI Assistant ishga tushdi.\n\n"
            "🔐 Tizim hozir qulflangan.\nOchish uchun /unlock buyrug‘idan foydalaning."
        )
    else:
        await message.answer(
            "👋 Personal AI Assistant ishga tushdi.\n\nTizim tayyor.\n\n"
            + "\n".join(MODULE_LABELS),
            reply_markup=main_menu(),
        )


async def help_command(message: Message) -> None:
    await message.answer("\n".join(f"/{name} - {label}" for name, label in COMMANDS.items()))


async def status(message: Message, app_context: BotContext) -> None:
    session = "Locked" if await app_context.security.lock_state.is_locked() else "Unlocked"
    database = await app_context.persistence.status()
    await message.answer(
        "✅ System status\n\nTelegram Bot: Online\nAuthorization: Owner verified\n"
        f"Session: {session}\nTimezone: {app_context.timezone}\nDatabase: {database}"
    )


async def identity(message: Message, app_context: BotContext) -> None:
    await message.answer(f"Telegram User ID: {app_context.owner_id}")


def create_router() -> Router:
    router = Router(name="common")
    router.message.register(start, Command("start"))
    router.message.register(start, F.text == HOME)
    router.message.register(help_command, Command("help"))
    router.message.register(status, Command("status"))
    router.message.register(identity, Command("id"))
    return router
````

### C:/Users/USER/Documents/Agent/app/bot/handlers/menu.py

````python
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.constants import MODULE_LABELS, PLACEHOLDER
from app.bot.keyboards.main_menu import main_menu


async def menu(message: Message) -> None:
    await message.answer("Menyu", reply_markup=main_menu())


async def module_placeholder(message: Message) -> None:
    await message.answer(PLACEHOLDER)


async def callback_placeholder(callback: CallbackQuery) -> None:
    await callback.answer(PLACEHOLDER)


def create_router() -> Router:
    router = Router(name="menu")
    router.message.register(menu, Command("menu"))
    router.message.register(module_placeholder, F.text.in_(MODULE_LABELS))
    router.callback_query.register(callback_placeholder)
    return router
````

### C:/Users/USER/Documents/Agent/app/bot/handlers/security.py

````python
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from app.bot.constants import LOCK, LOCKOUT, PIN_PROMPT, UNLOCKED, WRONG_PIN, command_name
from app.bot.context import BotContext
from app.bot.states import UnlockFlow
from app.bot.transport import delete_sensitive_message
from app.modules.audit.actions import AuditAction
from app.modules.security.service import UnlockResult


async def lock(message: Message, state: FSMContext, app_context: BotContext) -> None:
    await app_context.security.lock()
    await state.clear()
    await app_context.persistence.audit(AuditAction.SESSION_LOCKED, app_context.owner_id)
    await message.answer("🔐 Tizim qulflandi.", reply_markup=ReplyKeyboardRemove())


async def begin_unlock(message: Message, state: FSMContext, app_context: BotContext) -> None:
    await state.clear()
    if app_context.security.guard.is_blocked():
        await message.answer(LOCKOUT)
        return
    await state.set_state(UnlockFlow.waiting_for_pin)
    await message.answer(PIN_PROMPT, reply_markup=ReplyKeyboardRemove())


async def receive_pin(message: Message, state: FSMContext, app_context: BotContext) -> None:
    await state.clear()
    await delete_sensitive_message(message)
    result = await app_context.security.unlock(message.text or "")
    action = (
        AuditAction.LOGIN_SUCCESS if result == UnlockResult.SUCCESS else AuditAction.LOGIN_FAILED
    )
    await app_context.persistence.audit(action, app_context.owner_id)
    if result == UnlockResult.SUCCESS:
        await app_context.persistence.audit(AuditAction.SESSION_UNLOCKED, app_context.owner_id)
    await message.answer(
        {
            UnlockResult.SUCCESS: UNLOCKED,
            UnlockResult.FAILED: WRONG_PIN,
            UnlockResult.BLOCKED: LOCKOUT,
        }[result]
    )


def create_router() -> Router:
    router = Router(name="security")
    router.message.register(lock, Command("lock"))
    router.message.register(begin_unlock, Command("unlock"))
    router.message.register(lock, F.text == LOCK)
    # This handler precedes all menu handlers; pending PIN text cannot invoke a module.
    router.message.register(receive_pin, UnlockFlow.waiting_for_pin, is_pin_input)
    return router


def is_pin_input(message: Message) -> bool:
    return command_name(message.text) is None
````

### C:/Users/USER/Documents/Agent/app/bot/keyboards/__init__.py

````python
"""Telegram presentation layouts."""
````

### C:/Users/USER/Documents/Agent/app/bot/keyboards/main_menu.py

````python
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.bot.constants import HOME, LOCK, MODULE_LABELS


def main_menu() -> ReplyKeyboardMarkup:
    labels = (HOME, *MODULE_LABELS, LOCK)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=label) for label in labels[index : index + 2]]
            for index in range(0, len(labels), 2)
        ],
        resize_keyboard=True,
    )
````

### C:/Users/USER/Documents/Agent/app/bot/middlewares/__init__.py

````python
"""Central transport security boundaries."""
````

### C:/Users/USER/Documents/Agent/app/bot/middlewares/lock_state.py

````python
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update

from app.bot.constants import LOCK, LOCKED, LOCKED_ALLOWED_COMMANDS, command_name
from app.bot.context import BotContext
from app.bot.states import UnlockFlow
from app.bot.transport import safe_reply, update_event
from app.modules.audit.actions import AuditAction


class LockStateMiddleware(BaseMiddleware):
    def __init__(self, context: BotContext) -> None:
        self.context = context

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        incoming = update_event(event) if isinstance(event, Update) else None
        text = incoming.text if isinstance(incoming, Message) else None
        command = command_name(text)
        waiting = data.get("raw_state") == UnlockFlow.waiting_for_pin.state
        # Only the dedicated FSM handler may receive non-command PIN input.
        pin_input = waiting and isinstance(incoming, Message) and command is None
        if not pin_input:
            await self.context.persistence.audit(
                AuditAction.COMMAND_RECEIVED if command else AuditAction.AUTHORIZED_ACCESS,
                self.context.owner_id,
                command,
            )
        permitted = command in LOCKED_ALLOWED_COMMANDS or text == LOCK or pin_input
        if await self.context.security.lock_state.is_locked() and not permitted:
            await safe_reply(incoming, LOCKED)
            return None
        return await handler(event, data)
````

### C:/Users/USER/Documents/Agent/app/bot/middlewares/owner_auth.py

````python
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from app.bot.constants import DENIED
from app.bot.context import BotContext
from app.bot.transport import safe_reply, update_event
from app.core.exceptions import TelegramConfigurationError
from app.modules.audit.actions import AuditAction


class OwnerAuthMiddleware(BaseMiddleware):
    """Authorize only supported updates from the owner in their own private chat."""

    def __init__(self, context: BotContext) -> None:
        if not context.owner_id or context.owner_id <= 0:
            raise TelegramConfigurationError("TELEGRAM_OWNER_ID is not configured.")
        self.context = context

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        incoming = update_event(event) if isinstance(event, Update) else None
        user = incoming.from_user if incoming is not None else None
        message = incoming.message if isinstance(incoming, CallbackQuery) else incoming
        authorized = (
            user is not None
            and not user.is_bot
            and user.id == self.context.owner_id
            and isinstance(message, Message)
            and message.chat.type == "private"
            and message.chat.id == self.context.owner_id
            and message.sender_chat is None
            and message.business_connection_id is None
        )
        if not authorized:
            await safe_reply(incoming, DENIED)
            await self.context.persistence.audit(
                AuditAction.UNAUTHORIZED_ACCESS, user.id if user else None
            )
            return None
        data["owner_authorized"] = True
        return await handler(event, data)
````

### C:/Users/USER/Documents/Agent/app/bot/persistence.py

````python
"""Optional persistence; expected connection failures degrade with explicit warnings."""

import asyncio
import logging

from asyncpg import InvalidAuthorizationSpecificationError, PostgresConnectionError
from sqlalchemy.exc import InterfaceError, OperationalError

from app.database.health import check_database_health
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService

logger = logging.getLogger(__name__)
CONNECTION_ERRORS = (
    OperationalError,
    InterfaceError,
    PostgresConnectionError,
    InvalidAuthorizationSpecificationError,
    OSError,
    TimeoutError,
)


class BotPersistence:
    """Uses existing repositories without storing Telegram objects or raw text."""

    def __init__(self, database: DatabaseManager | None = None) -> None:
        self.database = database

    async def audit(
        self,
        action: AuditAction,
        telegram_user_id: int | None = None,
        command: str | None = None,
    ) -> bool:
        if self.database is None:
            logger.warning(
                "audit_not_persisted_database_unconfigured", extra={"action": action.value}
            )
            return False
        details: dict[str, object] = {}
        if telegram_user_id is not None:
            details["telegram_user_id"] = telegram_user_id
        if command is not None:
            details["command"] = command
        try:
            async with asyncio.timeout(5), self.database.session() as session:
                user = (
                    await UserRepository(session).get_by_telegram_user_id(telegram_user_id)
                    if telegram_user_id is not None
                    else None
                )
                await AuditService(AuditRepository(session)).log_event(
                    action,
                    user_id=user.id if user else None,
                    details=details,
                )
            return True
        except CONNECTION_ERRORS:
            logger.warning(
                "audit_not_persisted_database_unavailable", extra={"action": action.value}
            )
            return False

    async def synchronize(
        self,
        telegram_user_id: int,
        *,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> bool:
        if self.database is None:
            logger.warning("user_not_persisted_database_unconfigured")
            return False
        try:
            async with asyncio.timeout(5), self.database.session() as session:
                await UserService(UserRepository(session)).synchronize(
                    telegram_user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                )
            return True
        except CONNECTION_ERRORS:
            logger.warning("user_not_persisted_database_unavailable")
            return False

    async def status(self) -> str:
        if self.database is None:
            return "Not configured"
        return "Connected" if await check_database_health(self.database.engine) else "Unavailable"
````

### C:/Users/USER/Documents/Agent/app/bot/run.py

````python
"""Run explicitly with python -m app.bot.run. No network activity occurs on import."""

import asyncio
import logging
from contextlib import AsyncExitStack

from aiogram.types import BotCommand, BotCommandScopeChat

from app.bot.constants import COMMANDS
from app.bot.context import BotContext
from app.bot.dispatcher import create_dispatcher
from app.bot.factory import create_bot, require_owner
from app.bot.persistence import BotPersistence
from app.core.config import get_settings
from app.core.exceptions import TelegramConfigurationError
from app.core.logging import configure_logging, report_error
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.security.lock_service import LockService
from app.modules.security.pin_service import PinService
from app.modules.security.service import SecurityService
from app.modules.security.unlock_guard import UnlockGuard

logger = logging.getLogger("app.bot.run")


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    owner_id = require_owner(settings)
    pin = await asyncio.to_thread(PinService.from_settings, settings)
    async with AsyncExitStack() as resources:
        bot = create_bot(settings)
        resources.push_async_callback(bot.session.close)
        database = None
        if settings.database_url:
            database = DatabaseManager(settings)
            database.initialize()
            resources.push_async_callback(database.dispose)
        persistence = BotPersistence(database)
        context = BotContext(
            owner_id,
            settings.app_timezone,
            SecurityService(
                LockService(),
                pin,
                UnlockGuard(
                    settings.bot_unlock_max_attempts,
                    settings.bot_unlock_lockout_seconds,
                ),
            ),
            persistence,
        )
        dispatcher = create_dispatcher(context)
        resources.push_async_callback(dispatcher.fsm.close)
        await bot.set_my_commands(
            [
                BotCommand(command=name, description=description)
                for name, description in COMMANDS.items()
            ],
            scope=BotCommandScopeChat(chat_id=owner_id),
        )
        await persistence.audit(AuditAction.BOT_STARTED)
        try:
            # Sequential polling avoids leaving detached PIN/DB handlers during shutdown.
            await dispatcher.start_polling(
                bot,
                allowed_updates=["message", "callback_query"],
                handle_as_tasks=False,
                close_bot_session=False,
            )
        finally:
            await context.security.lock()
            await persistence.audit(AuditAction.BOT_STOPPED)


def run() -> int:
    configure_logging()
    try:
        asyncio.run(main())
    except TelegramConfigurationError as error:
        # These messages are authored by our configuration validators, never SDK errors.
        logger.error("telegram_configuration_invalid")
        print(str(error))
        return 1
    except KeyboardInterrupt:
        return 0
    except Exception as error:  # noqa: BLE001 - executable boundary prevents secret tracebacks
        error_id = report_error(logger, error)
        print(f"Bot stopped. Error ID: {error_id}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
````

### C:/Users/USER/Documents/Agent/app/bot/states.py

````python
from aiogram.fsm.state import State, StatesGroup


class UnlockFlow(StatesGroup):
    waiting_for_pin = State()
````

### C:/Users/USER/Documents/Agent/app/bot/transport.py

````python
import logging

from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message, Update

logger = logging.getLogger(__name__)


def update_event(update: Update) -> Message | CallbackQuery | None:
    return update.message or update.callback_query


async def safe_reply(event: Message | CallbackQuery | None, text: str) -> None:
    try:
        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
    except TelegramAPIError:
        logger.warning("telegram_reply_failed")


async def delete_sensitive_message(message: Message) -> None:
    try:
        await message.delete()
    except TelegramAPIError:
        logger.warning("sensitive_message_delete_failed")
````

### C:/Users/USER/Documents/Agent/app/core/config.py

````python
from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load configuration without connections. Never log the full settings object.

    Feature startup must validate its required credentials before use.
    """

    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_timezone: str = Field(default="Asia/Tashkent", alias="APP_TIMEZONE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    telegram_bot_token: SecretStr | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_owner_id: int | None = Field(default=None, gt=0, alias="TELEGRAM_OWNER_ID")
    telegram_api_id: int | None = Field(default=None, gt=0, alias="TELEGRAM_API_ID")
    telegram_api_hash: SecretStr | None = Field(default=None, alias="TELEGRAM_API_HASH")

    database_url: SecretStr | None = Field(default=None, alias="DATABASE_URL")
    redis_url: SecretStr | None = Field(default=None, alias="REDIS_URL")
    secret_key: SecretStr | None = Field(default=None, alias="SECRET_KEY")
    bot_pin: SecretStr | None = Field(default=None, alias="BOT_PIN")
    bot_pin_hash: SecretStr | None = Field(default=None, alias="BOT_PIN_HASH")
    bot_unlock_max_attempts: int = Field(default=5, ge=1, le=20, alias="BOT_UNLOCK_MAX_ATTEMPTS")
    bot_unlock_lockout_seconds: int = Field(
        default=300, ge=1, le=86400, alias="BOT_UNLOCK_LOCKOUT_SECONDS"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore",
        validate_assignment=True,
        hide_input_in_errors=True,
    )

    @field_validator("app_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("APP_TIMEZONE must be a valid IANA timezone") from exc
        return value

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)

    @property
    def is_owner_configured(self) -> bool:
        return self.telegram_owner_id is not None and bool(self.telegram_bot_token)


def get_settings() -> Settings:
    """Load explicitly at startup so imports have no configuration side effects."""
    return Settings()
````

### C:/Users/USER/Documents/Agent/app/core/exceptions.py

````python
"""Safe application errors that do not contain credentials."""


class DatabaseConfigurationError(ValueError):
    """Database initialization requires a valid PostgreSQL configuration."""


class AuditDetailsError(ValueError):
    """Audit details must be JSON data without sensitive fields."""


class TelegramConfigurationError(ValueError):
    """Telegram startup requires valid owner, token and PIN configuration."""
````

### C:/Users/USER/Documents/Agent/app/core/logging.py

````python
"""Structured allowlisted logs; never serialize updates, exceptions or settings."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from traceback import walk_tb
from uuid import uuid4

SAFE_FIELDS = ("telegram_user_id", "command", "error_id", "error_type", "frames", "action")


class SafeJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "module": record.name,
            # Framework errors can embed API URLs or message payloads. Do not render them.
            "event": record.msg if record.name.startswith("app.") else "external_log",
        }
        for name in SAFE_FIELDS:
            if hasattr(record, name):
                payload[name] = getattr(record, name)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(SafeJsonFormatter())
    logging.basicConfig(
        handlers=[handler], level=getattr(logging, level.upper(), logging.INFO), force=True
    )


def report_error(logger: logging.Logger, error: Exception) -> str:
    """Log exception type and stack locations, excluding text, locals and source lines."""
    error_id = uuid4().hex[:12].upper()
    frames = [
        f"{Path(frame.f_code.co_filename).name}:{line}:{frame.f_code.co_name}"
        for frame, line in walk_tb(error.__traceback__)
    ]
    logger.error(
        "unexpected_error",
        extra={
            "error_id": error_id,
            "error_type": type(error).__name__,
            "frames": frames,
        },
    )
    return error_id
````

### C:/Users/USER/Documents/Agent/app/modules/audit/actions.py

````python
from enum import StrEnum


class AuditAction(StrEnum):
    BOT_STARTED = "BOT_STARTED"
    BOT_STOPPED = "BOT_STOPPED"
    AUTHORIZED_ACCESS = "AUTHORIZED_ACCESS"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    COMMAND_RECEIVED = "COMMAND_RECEIVED"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    SESSION_LOCKED = "SESSION_LOCKED"
    SESSION_UNLOCKED = "SESSION_UNLOCKED"
````

### C:/Users/USER/Documents/Agent/app/modules/security/__init__.py

````python
"""Owner session security; replace in-memory storage before multi-process deployment."""
````

### C:/Users/USER/Documents/Agent/app/modules/security/lock_service.py

````python
from typing import Protocol


class LockStore(Protocol):
    async def read(self) -> bool: ...
    async def write(self, locked: bool) -> None: ...


class MemoryLockStore:
    def __init__(self) -> None:
        self._locked = True

    async def read(self) -> bool:
        return self._locked

    async def write(self, locked: bool) -> None:
        self._locked = locked


class LockService:
    """A single-owner session, locked by default with replaceable storage."""

    def __init__(self, store: LockStore | None = None) -> None:
        self._store = store if store is not None else MemoryLockStore()

    async def is_locked(self) -> bool:
        return await self._store.read()

    async def lock(self) -> None:
        await self._store.write(True)

    async def unlock(self) -> None:
        await self._store.write(False)
````

### C:/Users/USER/Documents/Agent/app/modules/security/pin_service.py

````python
import asyncio

from argon2 import PasswordHasher, Type, extract_parameters
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings
from app.core.exceptions import TelegramConfigurationError

MAX_PIN_LENGTH = 256


class PinService:
    """Hold only an Argon2id hash; verification runs outside the event loop."""

    def __init__(self, encoded_hash: str) -> None:
        try:
            parameters = extract_parameters(encoded_hash)
            if parameters.type != Type.ID:
                raise ValueError("wrong algorithm")
        except (InvalidHashError, ValueError):
            raise TelegramConfigurationError(
                "BOT_PIN_HASH must be a valid Argon2id hash."
            ) from None
        self._encoded_hash = encoded_hash
        self._hasher = PasswordHasher(type=Type.ID)

    @classmethod
    def from_settings(cls, settings: Settings) -> "PinService":
        if settings.bot_pin_hash:
            return cls(settings.bot_pin_hash.get_secret_value())
        if settings.app_env != "development" or not settings.bot_pin:
            raise TelegramConfigurationError(
                "Configure BOT_PIN_HASH, or BOT_PIN for development only."
            )
        pin = settings.bot_pin.get_secret_value()
        if not 6 <= len(pin) <= MAX_PIN_LENGTH:
            raise TelegramConfigurationError(
                "Development BOT_PIN must contain 6 to 256 characters."
            )
        return cls(PasswordHasher(type=Type.ID).hash(pin))

    async def verify_pin(self, pin: str) -> bool:
        if not pin or len(pin) > MAX_PIN_LENGTH:
            return False
        try:
            return await asyncio.to_thread(self._hasher.verify, self._encoded_hash, pin)
        except VerifyMismatchError:
            return False
        except (VerificationError, InvalidHashError):
            raise TelegramConfigurationError("Configured PIN hash cannot be verified.") from None
````

### C:/Users/USER/Documents/Agent/app/modules/security/service.py

````python
import asyncio
from enum import StrEnum

from app.modules.security.lock_service import LockService
from app.modules.security.pin_service import PinService
from app.modules.security.unlock_guard import UnlockGuard


class UnlockResult(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"


class SecurityService:
    """Serialize lock transitions and verification, including concurrent callers."""

    def __init__(self, lock: LockService, pin: PinService, guard: UnlockGuard) -> None:
        self.lock_state = lock
        self._pin = pin
        self.guard = guard
        self._mutex = asyncio.Lock()

    async def lock(self) -> None:
        async with self._mutex:
            await self.lock_state.lock()

    async def unlock(self, candidate: str) -> UnlockResult:
        async with self._mutex:
            if self.guard.is_blocked():
                return UnlockResult.BLOCKED
            if not await self._pin.verify_pin(candidate):
                self.guard.failed()
                await self.lock_state.lock()
                return UnlockResult.BLOCKED if self.guard.is_blocked() else UnlockResult.FAILED
            self.guard.reset()
            await self.lock_state.unlock()
            return UnlockResult.SUCCESS
````

### C:/Users/USER/Documents/Agent/app/modules/security/unlock_guard.py

````python
from collections.abc import Callable
from time import monotonic


class UnlockGuard:
    """In-memory failed-attempt policy; one instance per owner and process."""

    def __init__(
        self,
        max_attempts: int = 5,
        lockout_seconds: int = 300,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if max_attempts < 1 or lockout_seconds < 1:
            raise ValueError("Unlock policy values must be positive")
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._clock = clock
        self.failed_attempts = 0
        self._blocked_until = 0.0

    def is_blocked(self) -> bool:
        if self._blocked_until and self._clock() >= self._blocked_until:
            self.reset()
        return self._blocked_until > self._clock()

    def failed(self) -> None:
        self.failed_attempts += 1
        if self.failed_attempts >= self.max_attempts:
            self._blocked_until = self._clock() + self.lockout_seconds

    def reset(self) -> None:
        self.failed_attempts = 0
        self._blocked_until = 0.0
````

### C:/Users/USER/Documents/Agent/app/modules/users/service.py

````python
from app.database.models import User
from app.modules.users.repository import UserRepository


class UserService:
    """Synchronize an already-authorized owner's profile within the caller transaction."""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def synchronize(
        self,
        telegram_user_id: int,
        *,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> User:
        user = await self.repository.get_by_telegram_user_id(telegram_user_id)
        if user is None:
            user = await self.repository.create(
                telegram_user_id,
                telegram_username=username,
                first_name=first_name,
                last_name=last_name,
            )
        else:
            user.telegram_username = username
            user.first_name = first_name
            user.last_name = last_name
        await self.repository.update_last_seen(user.id)
        return user
````

### C:/Users/USER/Documents/Agent/README.md

````markdown
# Personal AI Assistant

## Stage 1 - Step 1

A private Telegram assistant built incrementally. Step 1 provides environment
loading, masked secrets, timezone validation and isolated configuration tests.
Step 2 adds database infrastructure, repositories, audit services and migrations.
Step 3 adds the private Telegram polling bot and owner session security.

## Technology Stack

Python 3.12+, Pydantic v2, pydantic-settings and tzdata form the foundation.
Dependencies for subsequent Stage 1 steps include FastAPI, Uvicorn, Aiogram 3,
SQLAlchemy 2 async, asyncpg, Alembic, Redis, structlog and Argon2.
Development tools: pytest, pytest-asyncio, HTTPX and Ruff.

## Windows Requirements and Installation

Use PowerShell in VS Code or Visual Studio. Python 3.12 is the recommended baseline;
Python 3.12 or newer is required. Install it from the official Windows downloads
page (https://www.python.org/downloads/windows/) or Microsoft Store.
With the classic official installer, enable **Add python.exe to PATH** and the
launcher if offered. Reopen your terminal afterward.

```powershell
Set-Location C:\Users\USER\Documents\Agent
python --version
py --version
```

At least one must report Python 3.12+. If `python` opens the Store, check Windows
App execution aliases and PATH. If the launcher is absent, use `python` instead of
`py -3.12` below after checking its version.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python scripts/check_config.py
python -m compileall app scripts
python -m pytest
python -m ruff check app scripts tests
```

If activation is blocked, optionally allow local scripts for this terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Alternatively, skip activation and use `.\.venv\Scripts\python.exe` for every Python
command. Run from the repository root. Editable installation is required before
running `python scripts/check_config.py` so imports work reliably.

### Linux Differences

Install Python 3.12+ and its venv package using your distribution's package manager.

```bash
python3 -m venv .venv
source .venv/bin/activate
test -f .env || cp .env.example .env
```

The remaining pip, verification and test commands are the same.

## Configuration

Environment variables override `.env`, which overrides safe defaults. Names are
case-insensitive. Empty environment and dotenv values are ignored; optional fields
default to None. Malformed nonempty numeric IDs fail validation; IDs must be positive.
Unknown dotenv keys are ignored for future compatibility.

| Variable | Purpose / default |
| --- | --- |
| APP_ENV | Environment label; development |
| APP_DEBUG | Debug flag; false in code, true in example |
| APP_TIMEZONE | IANA timezone; Asia/Tashkent |
| LOG_LEVEL | Future logging configuration; INFO |
| TELEGRAM_OWNER_ID | Optional positive owner ID |
| TELEGRAM_BOT_TOKEN | Optional secret bot credential |
| TELEGRAM_API_ID / TELEGRAM_API_HASH | Optional future MTProto credentials |
| DATABASE_URL / REDIS_URL | Optional secret service URLs |
| SECRET_KEY | Optional secret, no usable default |
| BOT_PIN | Development-only secret, no default PIN |
| BOT_PIN_HASH | Preferred Argon2id hash; required outside development |
| BOT_UNLOCK_MAX_ATTEMPTS | Failed attempts before lockout; 5 |
| BOT_UNLOCK_LOCKOUT_SECONDS | Lockout duration; 300 seconds |

Call `get_settings()` or `Settings()` explicitly at startup. Importing the module
does not load settings. `timezone` returns ZoneInfo; tzdata supplies the timezone
database on Windows. Future timestamps must be timezone-aware, stored in UTC and
presented in the configured timezone.

Loading with integrations unset is allowed. Database initialization validates its
URL explicitly; other features will validate their required credentials at startup.
The verification script prints non-sensitive settings and configured
booleans only. Invalid configuration returns exit code 1 with field names, without
input values. Tests isolate environment variables and never read your real `.env`.

## Step 1 Structure

```text
Agent/
  app/
    __init__.py
    core/
      __init__.py
      config.py
  scripts/
    check_config.py
  tests/
    test_config.py
  .env.example
  .gitignore
  pyproject.toml
  README.md
```

Existing package.json, package-lock.json and server.js are retained legacy Node.js
files. They are not used by this Python application. Package discovery includes
only app and its subpackages. No additional empty directories are required now.

## Planned Stage 1 Structure

```text
app/
  main.py                 FastAPI composition and lifespan
  core/                   Configuration, security, logging and constants
  database/models/        Async sessions and ORM models
  bot/                    Bot and dispatcher composition
    middlewares/          Owner authorization, lock and error handling
    filters/              Reusable update filters
    handlers/             Thin command adapters
    keyboards/            Telegram menus
  modules/
    users/                Owner repository and service
    audit/                Audit repository and service
  services/               Shared services and integration boundaries
  api/routes/             HTTP endpoints and health checks
migrations/               Alembic revisions
tests/                    Unit and integration tests
docker/                   Container support when needed
Dockerfile
docker-compose.yml
alembic.ini
```

Calendar, reminders, email, finance, notebook, tasks, personal Telegram, AI, voice
and storage modules will be added when their contracts are defined. Handlers and
routes will delegate business logic to services. AI output must become a structured
action validated and authorized by the backend, with confirmation when required.

## Security Notes

- Secrets come from environment variables; dotenv files are ignored by Git.
- SecretStr masks tokens, PINs, keys and URLs; it is not encryption.
- Never log full Settings objects, raw secrets or validation input.
- Use get_secret_value() only at integration boundaries that need credentials.
- Configure a strong PIN/passphrase; Step 3 hashes it and limits failed unlock attempts.
- Features must fail closed when required credentials or authorization are missing.
- Dependency constraints are not a reproducible deployment lockfile.

## Not Implemented Yet

FastAPI server, HTTP health endpoints, Redis, Docker, encryption, TOTP and future
product modules are not implemented yet.

## Next Development Step

Stage 1 Step 4: Redis, shared session state, FastAPI application, health endpoints
and bot/application lifecycle integration. Step 4 is not implemented here.

## Stage 1 - Step 2: Database Foundation

### Local PostgreSQL Setup

Use a supported PostgreSQL installation (PostgreSQL 16+ recommended). On Windows,
install PostgreSQL from https://www.postgresql.org/download/windows/ and include
the command-line tools. Keep local PostgreSQL bound to localhost. Add its bin
directory to PATH or invoke psql with its full path. No Docker is used in this step.

Start psql as your local administrator (it prompts for your own installation password):

```powershell
psql -U postgres -h localhost -d postgres
```

Run these commands inside psql. The password command prompts without embedding a
password in SQL history. This dedicated role is not a superuser.

```sql
CREATE ROLE personal_ai_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
\password personal_ai_app
CREATE DATABASE personal_ai OWNER personal_ai_app;
\q
```

Set DATABASE_URL in your ignored .env. This is a placeholder, not a working credential:

```text
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@localhost:5432/personal_ai
```

Use your dedicated role/password. Percent-encode special characters in credentials.
Never print URLs or full database exception objects. A future deployment should
separate the migration role from a runtime role with only necessary table privileges.

### Migration Commands (PowerShell)

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic history
.\.venv\Scripts\python.exe -m alembic check
```

For later schema edits, generate a new revision and inspect it before upgrading:

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe schema change"
```

The initial revision 0001 was authored manually. Do not generate a duplicate initial
revision. Async migrations use the same URL as the application and run Alembic's
synchronous migration operations through AsyncConnection.run_sync().

Rollback is destructive: downgrading 0001 removes users and audit_logs with their
data. Back up first and use this only against an intended development database:

```powershell
.\.venv\Scripts\python.exe -m alembic downgrade -1
```

Offline SQL compilation does not connect to a database or prove a live migration:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head --sql
```

### Schema and Files

```text
app/core/exceptions.py
app/database/
  __init__.py
  base.py
  session.py
  health.py
  models/
    __init__.py
    user.py
    audit_log.py
app/modules/
  __init__.py
  users/
    __init__.py
    repository.py
  audit/
    __init__.py
    actions.py
    repository.py
    service.py
migrations/
  env.py
  script.py.mako
  versions/0001_initial_users_audit_logs.py
alembic.ini
tests/
  conftest.py
  test_database_config.py
  test_user_repository.py
  test_audit_service.py
```

Users have a bigint primary key, unique bigint Telegram ID, nullable username/name
fields, active flag, created/updated timestamps and nullable last_seen_at.
The Telegram ID UNIQUE constraint creates a PostgreSQL unique index, so an extra
duplicate index is unnecessary. The table allows multiple users; owner access is a
Step 3 application-layer rule.

Audit logs have a bigint key, nullable user FK, action string, optional entity fields,
JSONB details, optional IP address and creation timestamp. User, action and creation
time are indexed. ON DELETE SET NULL retains audit history after user deletion.
No implicit ORM relationships are defined; repositories make queries explicitly to
avoid async lazy-loading surprises.

PostgreSQL uses timestamptz and UTC connections. UTCDateTime rejects naive writes;
SQLite test reads regain UTC awareness. created_at/updated_at have server defaults.
SQLAlchemy updates updated_at on ORM/Core updates; direct SQL writers must update
it explicitly (there is no database trigger).

### Sessions and Transactions

Construct one DatabaseManager per application lifespan, call initialize() once and
inject it into services. initialize() validates the URL and creates an engine without
opening a connection. Imports and Settings loading work with DATABASE_URL blank.
Dispose the manager at shutdown after active sessions finish.

```python
from app.core.config import get_settings
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.users.repository import UserRepository

async def example(owner_id: int) -> None:
    database = DatabaseManager(get_settings())
    database.initialize()
    try:
        async with database.session() as session:
            user = await UserRepository(session).create(owner_id)
            await AuditService(AuditRepository(session)).log_event(
                AuditAction.AUTHORIZED_ACCESS, user_id=user.id
            )
    finally:
        await database.dispose()
```

The example is one standalone unit of work, not a per-request engine pattern.
Repositories flush but never commit. The application chooses the transaction scope;
database.session() commits on successful exit and rolls back/closes on failure.
Use a separate session per concurrent task. To persist a failed-action audit event
after rollback, explicitly start a separate transaction.

check_database_health(database.engine) executes SELECT 1 with a timeout and returns
a boolean. Failure logs contain a fixed message, never exception text or credentials.

AuditService accepts only supported actions and JSON objects up to 16 KiB, rejects
nonfinite numbers, cycles, non-JSON values and known sensitive keys recursively.
This cannot detect a secret disguised as a harmless field: callers must supply
purpose-built metadata, never raw messages, credentials, PINs or arbitrary AI output.
The low-level audit repository is internal persistence and does not replace validation.

### Tests and Verification

```powershell
.\.venv\Scripts\python.exe -m compileall app migrations tests
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m ruff check app migrations tests
.\.venv\Scripts\python.exe -m pip check
```

Tests use a fresh async in-memory SQLite database with FK enforcement per test and
never access the owner's database. aiosqlite is a dev-only dependency. Models use
JSON in SQLite and JSONB in PostgreSQL; production migration types are PostgreSQL
native. SQLite verifies repository/transaction behavior, not PostgreSQL connectivity
or migration execution. Live upgrade/check requires a configured PostgreSQL database.

## Stage 1 - Step 3: Private Telegram Bot

### Prerequisites and Credentials

1. In Telegram, contact the official [BotFather](https://t.me/BotFather), run /newbot
   and follow its prompts. Put the issued token in the ignored .env as TELEGRAM_BOT_TOKEN.
   See the [official bot tutorial](https://core.telegram.org/bots/tutorial).
2. Obtain your numeric Telegram user ID (not username, phone number or bot ID).
   One first-party method is to send a recognizable message to your new bot, stop
   any polling process and inspect that message's `message.from.id` using
   [getUpdates](https://core.telegram.org/bots/api#getupdates) in a local API client.
   Match your own message; do not assume the first update belongs to you. Keep the
   token out of browser URLs, screenshots, shell history and logs. Alternatively use
   an ID lookup tool you already trust, without sharing any token or PIN with it.
3. Set TELEGRAM_OWNER_ID to that positive integer. Missing owner/token values fail
   startup clearly. The application never temporarily opens access to discover an ID.
4. Open a private chat with your bot and send /start before starting the polling
   process; this establishes the chat used for owner-scoped command registration.
5. Configure a PIN hash as described below. PostgreSQL is optional for bot startup;
   when configured, apply Step 2 migrations before running the bot.

Example field names only; replace placeholders in .env, never in source code:

```text
TELEGRAM_BOT_TOKEN=<YOUR_BOT_TOKEN>
TELEGRAM_OWNER_ID=<YOUR_NUMERIC_USER_ID>
BOT_PIN_HASH=<YOUR_ARGON2ID_HASH>
BOT_PIN=
BOT_UNLOCK_MAX_ATTEMPTS=5
BOT_UNLOCK_LOCKOUT_SECONDS=300
```

Do not send credentials in issue reports or chat transcripts. A Telegram bot chat
is not end-to-end encrypted; message deletion is best-effort and cannot erase copies
already seen in notifications or other devices. PIN protection is an additional
application lock, not a replacement for securing your Telegram account.

### PIN Configuration

Generate the Argon2id hash locally with a hidden prompt:

```powershell
.\.venv\Scripts\python.exe scripts/hash_pin.py
```

Put the resulting hash in BOT_PIN_HASH inside .env. It starts with `$argon2id$`;
edit .env directly so PowerShell does not expand the dollar signs. Treat the hash as
sensitive because it enables offline guessing. Use a strong, unique passphrase or PIN.

BOT_PIN_HASH takes precedence. In APP_ENV=development only, BOT_PIN can bootstrap a
hash in memory; outside development an Argon2id hash is required. No default PIN
exists. The verification service retains only the hash and runs expensive checks
outside the event loop. Plain configuration still exists in the environment/settings
when you choose BOT_PIN; prefer BOT_PIN_HASH and clear BOT_PIN after bootstrapping.

### Start and Stop (PowerShell)

```powershell
Set-Location C:\Users\USER\Documents\Agent
.\.venv\Scripts\python.exe -m app.bot.run
```

Run one polling process per bot token. Stop with Ctrl+C. Startup registers seven
commands for the owner chat and attempts BOT_STARTED auditing. Shutdown locks the
session, attempts BOT_STOPPED auditing and closes FSM, Telegram HTTP and DB resources.
Sequential polling keeps handler work within the polling lifecycle. Imports never
start polling. No live Telegram call is made by tests.

### Commands and Lock Behavior

| Command | Behavior |
| --- | --- |
| /start | Synchronizes owner profile if DB is available; welcome/locked notice |
| /help | Lists current commands |
| /status | Owner-safe bot/session/timezone and checked database status |
| /id | Returns the owner's Telegram numeric user ID |
| /menu | Shows module placeholders when unlocked |
| /lock | Locks immediately and clears pending PIN state |
| /unlock | Starts a private two-message PIN flow |

The bot starts locked. /start, /help, /status, /id, /unlock and /lock remain usable.
Other commands, module buttons and callbacks are blocked centrally until unlocked.
Unknown/unattributed updates and owner messages in groups are rejected as well.
Unauthorized Message and CallbackQuery updates receive `Access denied` when a reply
is possible and never reach FSM or ordinary handlers.

After /unlock, send the PIN as a separate message. Its text is never placed in FSM
data, logs, audit details or responses. The bot attempts to delete that message,
clears the pending state and replies success/failure. Each retry begins with /unlock.
Known commands continue to work while awaiting a PIN; other input is treated as the
attempt. Five failed attempts block verification for five minutes by default.
Repeated /unlock or /lock does not reset failures. Successful verification resets
the counter. Concurrent verification is serialized. All future sensitive handlers
must stay behind the same authorization and lock middleware.

### Persistence and Logging

The bot adapts existing UserRepository/UserService and AuditService through
BotPersistence. Repeated /start updates one owner profile and last_seen_at without
adding duplicates. Security and command audits contain event names, numeric IDs and
recognized command names only. LOGIN_SUCCESS/FAILED and SESSION_LOCKED/UNLOCKED are
supported in addition to the earlier audit actions.

No database URL means explicit `not_persisted_database_unconfigured` warnings.
Expected connection outages produce `not_persisted_database_unavailable` warnings;
bot commands can still operate. Programming/schema errors propagate to centralized
error handling. Successful bot actions do not imply that an audit was saved. /status
reports Not configured, Connected (after SELECT 1) or Unavailable, never a fabricated
successful connection. Audit writes and profile synchronization have a five-second
timeout so outages do not hang handlers indefinitely.

Unexpected failures produce an error ID, lock the session and return a safe reply.
Structured logs record event, level, timestamp, module and safe contextual fields.
Exception diagnostics include type and stack locations, never exception strings,
source lines, locals or update dumps. Third-party log text is deliberately suppressed
because it can embed credential-bearing API URLs or payloads. Keep this formatter
when integrating later components; do not enable raw SDK request/body logging.

### In-Memory Limits

Lock state, failed-attempt counters and FSM are local to one process. Restart clears
attempts and pending PIN state and starts locked again. This is not a persistent
production security store, and restarting can reset a lockout. There is no idle
auto-lock or PIN prompt expiry yet. Redis-backed shared state and atomic attempt
tracking belong to Step 4. Do not run multiple workers with this implementation.

### Step 3 Files and Verification

`app/bot/` contains factory, dispatcher, context, optional persistence adapter,
middleware, handlers, keyboards, transport helpers and polling entrypoint.
`app/modules/security/` contains lock storage/service, Argon2id verification,
unlock attempt policy and serialized security operations. `app/modules/users/service.py`
owns profile synchronization. `app/core/logging.py` owns safe structured logs.
`tests/bot/` exercises real dispatcher routing with an offline Telegram session,
plus service, persistence and shutdown behavior.

```powershell
.\.venv\Scripts\python.exe -m compileall app scripts tests
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m ruff check app scripts tests
.\.venv\Scripts\python.exe -m pip check
```

Tests never need your real .env secrets, Telegram network or PostgreSQL instance.
Mocked Telegram tests and SQLite persistence tests do not prove live Telegram or
PostgreSQL operation; missing credentials/services are reported separately as BLOCKED.
````

### C:/Users/USER/Documents/Agent/scripts/hash_pin.py

````python
"""Generate a hash using a hidden local prompt; never accept a PIN in shell arguments."""

import warnings
from getpass import GetPassWarning, getpass

from argon2 import PasswordHasher, Type


def main() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", GetPassWarning)
        try:
            pin = getpass("New PIN/passphrase (6-256 characters): ")
        except GetPassWarning:
            raise SystemExit("Use an interactive terminal with hidden input support.") from None
    if not 6 <= len(pin) <= 256:
        raise SystemExit("PIN/passphrase length must be 6-256 characters.")
    print(PasswordHasher(type=Type.ID).hash(pin))


if __name__ == "__main__":
    main()
````

### C:/Users/USER/Documents/Agent/tests/bot/__init__.py

````python
"""Offline Telegram integration tests."""
````

### C:/Users/USER/Documents/Agent/tests/bot/conftest.py

````python
"""Dispatch real Aiogram updates through an offline API session."""

from collections.abc import AsyncGenerator, AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import DeleteMessage, GetMe, SendMessage, TelegramMethod
from aiogram.types import Chat, Message, Update, User
from argon2 import PasswordHasher, Type

from app.bot.context import BotContext
from app.bot.dispatcher import create_dispatcher
from app.bot.persistence import BotPersistence
from app.core.config import Settings
from app.modules.security.lock_service import LockService
from app.modules.security.pin_service import PinService
from app.modules.security.service import SecurityService
from app.modules.security.unlock_guard import UnlockGuard

TEST_TOKEN = "123456789:TEST_ONLY_FAKE_TOKEN_NOT_FOR_TELEGRAM_abc"
TEST_PIN = "test-pin-only"
OWNER = 42


@pytest.fixture(autouse=True)
def isolate_bot_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    names = {str(field.alias).upper() for field in Settings.model_fields.values()}
    for name in list(os.environ):
        if name.upper() in names:
            monkeypatch.delenv(name)


class OfflineSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        self.fail_delete = False
        self.closed = False

    async def close(self) -> None:
        self.closed = True

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        timeout: int | None = None,
    ) -> Any:
        self.calls.append(method)
        if isinstance(method, GetMe):
            return User(id=123456789, is_bot=True, first_name="Test", username="test_assistant_bot")
        if isinstance(method, DeleteMessage) and self.fail_delete:
            raise TelegramBadRequest(method=method, message="test deletion denied")
        if isinstance(method, SendMessage):
            return Message(
                message_id=999,
                date=datetime.now(UTC),
                chat=Chat(id=int(method.chat_id), type="private"),
                text=method.text,
            )
        return True

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes, None]:
        raise AssertionError("Network streaming is prohibited in tests")
        yield b""  # pragma: no cover


@dataclass
class Harness:
    bot: Bot
    dispatcher: Dispatcher
    context: BotContext
    api: OfflineSession
    audit: AsyncMock
    sync: AsyncMock
    sequence: int = field(default=0)

    async def send(
        self,
        text: str | None,
        user_id: int | None = OWNER,
        *,
        chat_type: str = "private",
    ) -> None:
        self.sequence += 1
        payload = {
            "update_id": self.sequence,
            "message": {
                "message_id": self.sequence,
                "date": datetime.now(UTC),
                "chat": {"id": user_id or OWNER, "type": chat_type},
                "text": text,
            },
        }
        if user_id is not None:
            payload["message"]["from"] = {"id": user_id, "is_bot": False, "first_name": "Test"}
        update = Update.model_validate(payload, context={"bot": self.bot})
        await self.dispatcher.feed_update(self.bot, update)

    @property
    def replies(self) -> list[str]:
        return [call.text for call in self.api.calls if isinstance(call, SendMessage)]


@pytest.fixture(scope="session")
def pin_hash() -> str:
    return PasswordHasher(type=Type.ID).hash(TEST_PIN)


@pytest_asyncio.fixture
async def harness(pin_hash: str) -> AsyncIterator[Harness]:
    api = OfflineSession()
    bot = Bot(TEST_TOKEN, session=api)
    persistence = BotPersistence()
    audit = AsyncMock(return_value=False)
    sync = AsyncMock(return_value=False)
    persistence.audit = audit
    persistence.synchronize = sync
    context = BotContext(
        OWNER,
        "Asia/Tashkent",
        SecurityService(LockService(), PinService(pin_hash), UnlockGuard()),
        persistence,
    )
    dispatcher = create_dispatcher(context)
    try:
        yield Harness(bot, dispatcher, context, api, audit, sync)
    finally:
        await dispatcher.fsm.close()
        await bot.session.close()
````

### C:/Users/USER/Documents/Agent/tests/bot/test_bot_commands.py

````python
import pytest

from app.bot.constants import LOCKED, PLACEHOLDER

from .conftest import Harness


@pytest.mark.parametrize("command", ["/help", "/status", "/start"])
async def test_public_owner_commands_while_locked(harness: Harness, command: str) -> None:
    await harness.send(command)
    assert harness.replies
    assert harness.replies[-1] != LOCKED
    assert "Error ID" not in harness.replies[-1]


async def test_status_reports_unconfigured(harness: Harness) -> None:
    await harness.send("/status")
    assert "Database: Not configured" in harness.replies[-1]
    assert "Session: Locked" in harness.replies[-1]
    assert "Connected" not in harness.replies[-1]


async def test_start_sync(harness: Harness) -> None:
    await harness.send("/start")
    harness.sync.assert_awaited_once_with(42, username=None, first_name="Test", last_name=None)


async def test_start_unlocked(harness: Harness) -> None:
    await harness.context.security.lock_state.unlock()
    await harness.send("/start")
    assert "Tizim tayyor" in harness.replies[-1]


async def test_menu_unlocked(harness: Harness) -> None:
    await harness.context.security.lock_state.unlock()
    await harness.send("/menu")
    assert harness.replies[-1] == "Menyu"


async def test_module_unlocked(harness: Harness) -> None:
    await harness.context.security.lock_state.unlock()
    await harness.send("📅 Calendar")
    assert harness.replies[-1] == PLACEHOLDER


async def test_module_locked(harness: Harness) -> None:
    await harness.send("📅 Calendar")
    assert harness.replies[-1] == LOCKED
````

### C:/Users/USER/Documents/Agent/tests/bot/test_bot_factory.py

````python
import logging

import pytest
from argon2 import PasswordHasher, Type

from app.bot.factory import create_bot, require_owner
from app.core.config import Settings
from app.core.exceptions import TelegramConfigurationError
from app.core.logging import SafeJsonFormatter, report_error
from app.modules.security.pin_service import PinService


def configured(**values: object) -> Settings:
    return Settings(_env_file=None, TELEGRAM_OWNER_ID=42, **values)


def test_missing_token() -> None:
    with pytest.raises(TelegramConfigurationError, match="TELEGRAM_BOT_TOKEN"):
        create_bot(configured(TELEGRAM_BOT_TOKEN=None))


def test_missing_owner() -> None:
    with pytest.raises(TelegramConfigurationError, match="TELEGRAM_OWNER_ID"):
        require_owner(Settings(_env_file=None, TELEGRAM_OWNER_ID=None))


def test_invalid_token_redacted() -> None:
    candidate = "test-secret-invalid-token"
    with pytest.raises(TelegramConfigurationError) as caught:
        create_bot(configured(TELEGRAM_BOT_TOKEN=candidate))
    assert candidate not in str(caught.value)


async def test_token_repr() -> None:
    candidate = "123456789:TEST_ONLY_FAKE_TOKEN_NOT_FOR_TELEGRAM_abc"
    settings = configured(TELEGRAM_BOT_TOKEN=candidate)
    bot = create_bot(settings)
    try:
        assert candidate not in repr(settings)
        assert candidate not in repr(bot)
    finally:
        await bot.session.close()


def test_framework_logs_and_exception_text_redacted(caplog: pytest.LogCaptureFixture) -> None:
    formatter = SafeJsonFormatter()
    record = logging.LogRecord(
        "aiogram.dispatcher", logging.ERROR, "", 1, "test-secret-in-url", (), None
    )
    assert "test-secret-in-url" not in formatter.format(record)
    try:
        raise RuntimeError("test-secret-pin")
    except RuntimeError as error:
        report_error(logging.getLogger("app.bot.test"), error)
    assert "test-secret-pin" not in caplog.text
    assert "error_id" in formatter.format(caplog.records[-1])


async def test_hash_priority_and_verification(pin_hash: str) -> None:
    service = PinService.from_settings(
        configured(
            BOT_PIN_HASH=pin_hash,
            BOT_PIN="different-test-only",
            APP_ENV="production",
        )
    )
    assert await service.verify_pin("test-pin-only")
    assert not await service.verify_pin("wrong-test-only")
    assert pin_hash not in repr(service)


def test_plain_pin_rejected_in_production() -> None:
    with pytest.raises(TelegramConfigurationError):
        PinService.from_settings(
            configured(
                APP_ENV="production",
                BOT_PIN="test-pin-only",
                BOT_PIN_HASH=None,
            )
        )


async def test_development_pin() -> None:
    service = PinService.from_settings(
        configured(
            APP_ENV="development",
            BOT_PIN="test-pin-only",
            BOT_PIN_HASH=None,
        )
    )
    assert await service.verify_pin("test-pin-only")


@pytest.mark.parametrize(
    "value",
    ["bad-test-hash", PasswordHasher(type=Type.I).hash("test-only")],
    ids=["malformed", "wrong_algorithm"],
)
def test_invalid_hash(value: str) -> None:
    with pytest.raises(TelegramConfigurationError):
        PinService(value)


def test_missing_pin() -> None:
    with pytest.raises(TelegramConfigurationError):
        PinService.from_settings(configured(BOT_PIN=None, BOT_PIN_HASH=None))


def test_hash_setting_is_masked(pin_hash: str) -> None:
    settings = configured(BOT_PIN_HASH=pin_hash)
    assert pin_hash not in repr(settings)
    assert pin_hash not in settings.model_dump_json()
    assert settings.bot_pin_hash.get_secret_value() == pin_hash
````

### C:/Users/USER/Documents/Agent/tests/bot/test_lifecycle.py

````python
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram import Bot, Dispatcher

from app.bot import run
from app.core.config import Settings
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction

from .conftest import TEST_TOKEN, OfflineSession


async def test_polling_failure_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
    pin_hash: str,
) -> None:
    api = OfflineSession()
    bot = Bot(TEST_TOKEN, session=api)
    settings = Settings(
        _env_file=None,
        TELEGRAM_OWNER_ID=42,
        TELEGRAM_BOT_TOKEN=TEST_TOKEN,
        BOT_PIN_HASH=pin_hash,
        DATABASE_URL=None,
    )
    monkeypatch.setattr(run, "get_settings", lambda: settings)
    monkeypatch.setattr(run, "configure_logging", lambda level: None)
    monkeypatch.setattr(run, "create_bot", lambda settings: bot)
    monkeypatch.setattr(
        Dispatcher, "start_polling", AsyncMock(side_effect=RuntimeError("test stop"))
    )
    with pytest.raises(RuntimeError, match="test stop"):
        await run.main()
    assert api.closed


async def test_registration_failure_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
    pin_hash: str,
) -> None:
    api = OfflineSession()
    bot = Bot(TEST_TOKEN, session=api)
    settings = Settings(
        _env_file=None,
        TELEGRAM_OWNER_ID=42,
        TELEGRAM_BOT_TOKEN=TEST_TOKEN,
        BOT_PIN_HASH=pin_hash,
        DATABASE_URL=None,
    )
    monkeypatch.setattr(run, "get_settings", lambda: settings)
    monkeypatch.setattr(run, "configure_logging", lambda level: None)
    monkeypatch.setattr(run, "create_bot", lambda settings: bot)
    monkeypatch.setattr(bot, "set_my_commands", AsyncMock(side_effect=RuntimeError("test stop")))
    with pytest.raises(RuntimeError, match="test stop"):
        await run.main()
    assert api.closed


async def test_polling_shutdown_disposes_database(
    monkeypatch: pytest.MonkeyPatch,
    pin_hash: str,
) -> None:
    api = OfflineSession()
    bot = Bot(TEST_TOKEN, session=api)
    settings = Settings(
        _env_file=None,
        TELEGRAM_OWNER_ID=42,
        TELEGRAM_BOT_TOKEN=TEST_TOKEN,
        BOT_PIN_HASH=pin_hash,
        DATABASE_URL="postgresql+asyncpg://localhost/test_only",
    )
    database = Mock(spec=DatabaseManager)
    database.dispose = AsyncMock()
    persistence = Mock()
    persistence.audit = AsyncMock(return_value=True)
    monkeypatch.setattr(run, "get_settings", lambda: settings)
    monkeypatch.setattr(run, "configure_logging", lambda level: None)
    monkeypatch.setattr(run, "create_bot", lambda settings: bot)
    monkeypatch.setattr(run, "DatabaseManager", lambda settings: database)
    monkeypatch.setattr(run, "BotPersistence", lambda database: persistence)
    monkeypatch.setattr(Dispatcher, "start_polling", AsyncMock(return_value=None))
    await run.main()
    database.initialize.assert_called_once()
    database.dispose.assert_awaited_once()
    persistence.audit.assert_any_await(AuditAction.BOT_STARTED)
    persistence.audit.assert_any_await(AuditAction.BOT_STOPPED)
    assert api.closed
````

### C:/Users/USER/Documents/Agent/tests/bot/test_lock_service.py

````python
import asyncio

from app.modules.security.lock_service import LockService
from app.modules.security.pin_service import PinService
from app.modules.security.service import SecurityService, UnlockResult
from app.modules.security.unlock_guard import UnlockGuard


async def test_lock_default_and_reset() -> None:
    lock = LockService()
    assert await lock.is_locked()
    await lock.unlock()
    assert not await lock.is_locked()
    await lock.lock()
    assert await lock.is_locked()
    assert await LockService().is_locked()


def test_guard_expiration() -> None:
    clock = [0.0]
    guard = UnlockGuard(max_attempts=2, lockout_seconds=300, clock=lambda: clock[0])
    guard.failed()
    assert not guard.is_blocked()
    guard.failed()
    assert guard.is_blocked()
    clock[0] = 301
    assert not guard.is_blocked()
    assert guard.failed_attempts == 0


async def test_parallel_attempts_cannot_bypass_limit(pin_hash: str) -> None:
    guard = UnlockGuard(max_attempts=2)
    service = SecurityService(LockService(), PinService(pin_hash), guard)
    results = await asyncio.gather(*[service.unlock("wrong-test-only") for _ in range(4)])
    assert results.count(UnlockResult.BLOCKED) == 3
    assert guard.failed_attempts == 2
    assert await service.lock_state.is_locked()
````

### C:/Users/USER/Documents/Agent/tests/bot/test_owner_authorization.py

````python
from datetime import UTC, datetime

from aiogram.methods import AnswerCallbackQuery
from aiogram.types import Update

from app.bot.constants import DENIED, LOCKED
from app.modules.audit.actions import AuditAction

from .conftest import Harness


async def test_owner_id_allowed(harness: Harness) -> None:
    await harness.send("/id")
    assert harness.replies[-1] == "Telegram User ID: 42"


async def test_unauthorized_never_reaches_handler(harness: Harness) -> None:
    await harness.send("/start", 99)
    assert harness.replies == [DENIED]
    harness.sync.assert_not_awaited()
    harness.audit.assert_awaited_once_with(AuditAction.UNAUTHORIZED_ACCESS, 99)


async def test_unauthorized_id(harness: Harness) -> None:
    await harness.send("/id", 99)
    assert harness.replies == [DENIED]


async def test_missing_sender(harness: Harness) -> None:
    await harness.send("/start", None)
    assert harness.replies == [DENIED]
    harness.sync.assert_not_awaited()


async def test_group_owner_rejected(harness: Harness) -> None:
    await harness.send("/id", 42, chat_type="group")
    assert harness.replies == [DENIED]


async def test_callback_authorization_and_lock(harness: Harness) -> None:
    for user_id, expected in [(99, DENIED), (42, LOCKED)]:
        update = Update.model_validate(
            {
                "update_id": user_id,
                "callback_query": {
                    "id": "test-callback",
                    "chat_instance": "test-chat",
                    "data": "calendar",
                    "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
                    "message": {
                        "message_id": 1,
                        "date": datetime.now(UTC),
                        "chat": {"id": user_id, "type": "private"},
                    },
                },
            },
            context={"bot": harness.bot},
        )
        await harness.dispatcher.feed_update(harness.bot, update)
        calls = [c for c in harness.api.calls if isinstance(c, AnswerCallbackQuery)]
        assert calls[-1].text == expected


async def test_unsupported_update_rejected(harness: Harness) -> None:
    await harness.dispatcher.feed_update(harness.bot, Update(update_id=555))
    harness.sync.assert_not_awaited()
    assert not harness.replies
    harness.audit.assert_awaited_once_with(AuditAction.UNAUTHORIZED_ACCESS, None)
````

### C:/Users/USER/Documents/Agent/tests/bot/test_persistence.py

````python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.bot.persistence import BotPersistence
from app.database.models import AuditLog, User
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService


async def test_owner_profile_upsert(engine: AsyncEngine) -> None:
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions.begin() as session:
        service = UserService(UserRepository(session))
        first = await service.synchronize(42, username="first", first_name="Test", last_name=None)
        second = await service.synchronize(
            42, username=None, first_name="Updated", last_name="Owner"
        )
        assert first.id == second.id
    async with sessions() as session:
        user = await UserRepository(session).get_by_telegram_user_id(42)
        assert user.telegram_username is None
        assert user.first_name == "Updated"
        assert user.last_seen_at.tzinfo is not None
        assert await session.scalar(select(func.count()).select_from(User)) == 1


async def test_facade_persists_audit(engine: AsyncEngine) -> None:
    database = Mock(spec=DatabaseManager)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    database.session = sessions.begin
    facade = BotPersistence(database)
    assert await facade.synchronize(42, username=None, first_name="Owner", last_name=None)
    assert await facade.audit(AuditAction.COMMAND_RECEIVED, 42, "start")
    async with sessions() as session:
        event = await session.scalar(select(AuditLog))
        assert event.user_id is not None
        assert event.details == {"telegram_user_id": 42, "command": "start"}


async def test_unconfigured_not_silent(caplog: pytest.LogCaptureFixture) -> None:
    facade = BotPersistence()
    assert not await facade.audit(AuditAction.BOT_STARTED)
    assert "not_persisted" in caplog.text
    assert await facade.status() == "Not configured"


async def test_connection_outage_and_programming_error(caplog: pytest.LogCaptureFixture) -> None:
    database = Mock(spec=DatabaseManager)

    @asynccontextmanager
    async def unavailable() -> AsyncIterator[AsyncSession]:
        raise OSError("test-sensitive-connection-data")
        yield  # pragma: no cover

    database.session = unavailable
    facade = BotPersistence(database)
    assert not await facade.audit(AuditAction.BOT_STARTED)
    assert not await facade.synchronize(42, username=None, first_name="Owner", last_name=None)
    assert "test-sensitive" not in caplog.text
    database.session = Mock(side_effect=TypeError("programming bug"))
    with pytest.raises(TypeError):
        await facade.audit(AuditAction.BOT_STARTED)


async def test_status_checks_real_helper() -> None:
    database = Mock(spec=DatabaseManager)
    facade = BotPersistence(database)
    with patch("app.bot.persistence.check_database_health", new=AsyncMock(return_value=False)):
        assert await facade.status() == "Unavailable"
    with patch("app.bot.persistence.check_database_health", new=AsyncMock(return_value=True)):
        assert await facade.status() == "Connected"
````

### C:/Users/USER/Documents/Agent/tests/bot/test_security_handlers.py

````python
import pytest
from aiogram.methods import DeleteMessage

from app.bot.constants import LOCKED, LOCKOUT, PIN_PROMPT, UNLOCKED, WRONG_PIN
from app.bot.states import UnlockFlow
from app.modules.audit.actions import AuditAction

from .conftest import Harness


async def test_unlock_flow(harness: Harness) -> None:
    await harness.send("/unlock")
    assert harness.replies[-1] == PIN_PROMPT
    state = harness.dispatcher.fsm.get_context(bot=harness.bot, chat_id=42, user_id=42)
    assert await state.get_state() == UnlockFlow.waiting_for_pin.state
    await harness.send("test-pin-only")
    assert harness.replies[-1] == UNLOCKED
    assert not await harness.context.security.lock_state.is_locked()
    assert await state.get_state() is None
    assert any(isinstance(call, DeleteMessage) for call in harness.api.calls)
    assert "test-pin-only" not in repr(harness.audit.await_args_list)
    assert "test-pin-only" not in "\n".join(harness.replies)
    harness.audit.assert_any_await(AuditAction.LOGIN_SUCCESS, 42)
    harness.audit.assert_any_await(AuditAction.SESSION_UNLOCKED, 42)


async def test_wrong_pin(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send("wrong-test-only")
    assert harness.replies[-1] == WRONG_PIN
    assert await harness.context.security.lock_state.is_locked()
    assert harness.context.security.guard.failed_attempts == 1
    harness.audit.assert_any_await(AuditAction.LOGIN_FAILED, 42)
    state = harness.dispatcher.fsm.get_context(bot=harness.bot, chat_id=42, user_id=42)
    assert await state.get_state() is None


async def test_lockout(harness: Harness) -> None:
    for _ in range(5):
        await harness.send("/unlock")
        await harness.send("wrong-test-only")
    assert harness.replies[-1] == LOCKOUT
    assert harness.context.security.guard.is_blocked()
    await harness.send("/unlock")
    assert harness.replies[-1] == LOCKOUT
    assert harness.context.security.guard.failed_attempts == 5


async def test_lock(harness: Harness) -> None:
    await harness.context.security.lock_state.unlock()
    await harness.send("/lock")
    assert await harness.context.security.lock_state.is_locked()
    harness.audit.assert_any_await(AuditAction.SESSION_LOCKED, 42)


async def test_lock_menu_protected(harness: Harness) -> None:
    await harness.send("/menu")
    assert harness.replies[-1] == LOCKED


async def test_delete_failure_safe(harness: Harness, caplog: pytest.LogCaptureFixture) -> None:
    harness.api.fail_delete = True
    await harness.send("/unlock")
    await harness.send("test-pin-only")
    assert harness.replies[-1] == UNLOCKED
    assert "sensitive_message_delete_failed" in caplog.text
    assert "test-pin-only" not in caplog.text


async def test_nonowner_cannot_supply_pin(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send("test-pin-only", 99)
    assert await harness.context.security.lock_state.is_locked()
    assert harness.context.security.guard.failed_attempts == 0


async def test_pending_pin_cannot_dispatch_menu(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send("📅 Calendar")
    assert harness.replies[-1] == WRONG_PIN


async def test_lock_button_clears_pending_pin(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send("🔐 Lock")
    assert harness.replies[-1] == "🔐 Tizim qulflandi."
    state = harness.dispatcher.fsm.get_context(bot=harness.bot, chat_id=42, user_id=42)
    assert await state.get_state() is None


async def test_error_id_no_payload(harness: Harness, caplog: pytest.LogCaptureFixture) -> None:
    harness.sync.side_effect = RuntimeError("test-pin-only test-secret-token")
    await harness.send("/start")
    assert "Error ID:" in harness.replies[-1]
    assert "test-secret-token" not in caplog.text
    assert "test-pin-only" not in caplog.text
    assert await harness.context.security.lock_state.is_locked()


async def test_nontext_pin_clears_state(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send(None)
    assert harness.replies[-1] == WRONG_PIN
    state = harness.dispatcher.fsm.get_context(bot=harness.bot, chat_id=42, user_id=42)
    assert await state.get_state() is None


async def test_unknown_slash_pin_is_deleted(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send("/test-not-a-command")
    assert harness.replies[-1] == WRONG_PIN
    assert any(isinstance(call, DeleteMessage) for call in harness.api.calls)


async def test_help_during_pin_flow(harness: Harness) -> None:
    await harness.send("/unlock")
    await harness.send("/help")
    assert "/unlock" in harness.replies[-1]
    assert harness.context.security.guard.failed_attempts == 0
````

### C:/Users/USER/Documents/Agent/tests/test_audit_service.py

````python
import math

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuditDetailsError
from app.database.models import AuditLog, User
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService, validated_details
from app.modules.users.repository import UserRepository


async def test_system_event_json_and_rollback(session: AsyncSession) -> None:
    service = AuditService(AuditRepository(session))
    details = {"command": "/start", "result": {"accepted": True}, "count": 1}
    event = await service.log_event(AuditAction.BOT_STARTED, details=details)
    await session.refresh(event)
    assert event.id is not None
    assert event.user_id is None
    assert event.details == details
    assert event.created_at.tzinfo is not None
    assert "accepted" not in repr(event)
    await session.rollback()
    assert await session.scalar(select(AuditLog)) is None


async def test_user_deletion_preserves_audit(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    event = await AuditService(AuditRepository(session)).log_event(
        AuditAction.AUTHORIZED_ACCESS, user_id=user.id, ip_address="127.0.0.1"
    )
    await session.execute(delete(User).where(User.id == user.id))
    await session.refresh(event)
    assert event.user_id is None
    assert event.details == {}


@pytest.mark.parametrize(
    "details",
    [
        {"token": "never-store-me"},
        {"nested": [{"BOT_PIN": "never-store-me"}]},
        {"value": object()},
        {"value": math.nan},
        {1: "bad-key"},
        {"payload": "x" * 17000},
    ],
)
def test_unsafe_details_rejected(details: dict[str, object]) -> None:
    with pytest.raises(AuditDetailsError) as caught:
        validated_details(details)
    assert "never-store-me" not in str(caught.value)


def test_circular_details_rejected() -> None:
    details: dict[str, object] = {}
    details["nested"] = details
    with pytest.raises(AuditDetailsError):
        validated_details(details)


def test_actions() -> None:
    assert {action.value for action in AuditAction} == {
        "BOT_STARTED",
        "BOT_STOPPED",
        "AUTHORIZED_ACCESS",
        "UNAUTHORIZED_ACCESS",
        "COMMAND_RECEIVED",
        "LOGIN_SUCCESS",
        "LOGIN_FAILED",
        "SESSION_LOCKED",
        "SESSION_UNLOCKED",
    }
````

