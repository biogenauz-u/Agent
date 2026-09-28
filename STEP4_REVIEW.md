# Stage 1 Step 4 - Complete File Contents

Repository: C:/Users/USER/Documents/Agent

## Architecture Summary

One ApplicationContext owns database and Redis pools, the lock service, persistence facade and optional Telegram runtime. API-only mode owns the context through FastAPI lifespan; combined mode lends the same initialized context to HTTP and Telegram. Telegram-only uses the same lifecycle. All imports are connection-free. Redis security selection requires a successful PING and never falls back to memory.

Redis security stores locked state, failure counters, TTL lockouts and FSM state. Atomic Lua scripts serialize failure updates and successful unlock commits. A short verification lease and revision check prevent concurrent or stale PIN verification from bypassing shared lock state. Missing/corrupt lock keys mean locked. Redis state survives bot restart; Redis server persistence itself is an operational setting. No credentials/PIN payloads are stored in state keys.

## Verification Results

- PASS: 112 tests, including all 89 previous tests and 23 new Step 4 tests.
- PASS: python -m compileall app tests migrations.
- PASS: python -m pip check (no broken requirements).
- PASS: python -m ruff check .
- PASS: actual FastAPI process started on http://127.0.0.1:8000 with memory security.
- PASS: GET / returned HTTP 200 and the expected project name/running response.
- PASS: GET /health returned HTTP 200 with degraded; DB, Redis and Telegram were truthfully not_configured.
- PASS: GET /health/live returned HTTP 200 alive.
- PASS: GET /health/ready returned HTTP 200 ready (optional services are not readiness requirements).
- PASS: offline tests cover component failure/cancellation cleanup and SIGTERM cancellation handling.
- BLOCKED: live Redis connectivity, because REDIS_URL is unset.
- BLOCKED: live PostgreSQL connectivity, because DATABASE_URL is unset.
- BLOCKED: live Telegram/combined operation, because owner/token/PIN credentials remain unconfigured.
- BLOCKED: full live verification. Fake Redis tests execute Lua with fakeredis[lua]; they do not prove live Redis operation.

An initial HTTP probe reached the port before startup completed and was refused; the subsequent live probe succeeded for all four endpoints. The API server was left running for local review. No Docker, Calendar, AI, scheduler or other Step 5 functionality was implemented.

## Health Rules

Detailed health is error/503 when application startup is incomplete, required Redis security is unavailable, or required Telegram polling is not running. Optional missing/unavailable services produce degraded/200. Readiness checks only required services; liveness does not query dependencies. Telegram health is lifecycle/configuration state, not a per-request Telegram API check.

## Compatibility Notes

All earlier behavioral assertions were retained. Three Telegram lifecycle tests now patch shared lifecycle wiring instead of the old runner-local constructors. The memory guard's synchronous helpers remain available for prior tests, while runtime code uses the async guard interface. Lua/fake Redis support was added only to dev dependencies. Redis FSM borrows the shared client and does not own pool closure. Separate OS processes necessarily own separate pools; combined mode shares instances.

## Changed Files

- `.env.example`
- `app/api/__init__.py`
- `app/api/app.py`
- `app/api/dependencies.py`
- `app/api/routes/__init__.py`
- `app/api/routes/health.py`
- `app/api/routes/root.py`
- `app/api/schemas/__init__.py`
- `app/api/schemas/health.py`
- `app/bot/dispatcher.py`
- `app/bot/errors.py`
- `app/bot/handlers/security.py`
- `app/bot/lifecycle.py`
- `app/bot/run.py`
- `app/bot/storage.py`
- `app/core/application.py`
- `app/core/config.py`
- `app/core/exceptions.py`
- `app/core/runtime.py`
- `app/modules/security/__init__.py`
- `app/modules/security/redis_service.py`
- `app/modules/security/redis_state.py`
- `app/modules/security/service.py`
- `app/modules/security/unlock_guard.py`
- `app/redis/__init__.py`
- `app/redis/health.py`
- `app/redis/keys.py`
- `app/redis/manager.py`
- `app/run_all.py`
- `app/run_api.py`
- `pyproject.toml`
- `README.md`
- `tests/bot/test_lifecycle.py`
- `tests/test_api.py`
- `tests/test_coordination.py`
- `tests/test_redis_state.py`
- `tests/test_shared_fsm.py`

## Complete Final Contents

### C:/Users/USER/Documents/Agent/.env.example

````text
APP_ENV=development
APP_DEBUG=true
APP_TIMEZONE=Asia/Tashkent
LOG_LEVEL=INFO
API_HOST=127.0.0.1
API_PORT=8000
SECURITY_STATE_BACKEND=memory
REDIS_KEY_PREFIX=personal_ai

TELEGRAM_BOT_TOKEN=
TELEGRAM_OWNER_ID=
TELEGRAM_API_ID=
TELEGRAM_API_HASH=

# PostgreSQL format (placeholders only):
# postgresql+asyncpg://USER:PASSWORD@localhost:5432/personal_ai
# Percent-encode special characters in credentials. Never commit real credentials.
DATABASE_URL=
# Optional for memory security; required for the redis security backend.
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

### C:/Users/USER/Documents/Agent/app/api/__init__.py

````python
"""Read-only public HTTP surface."""
````

### C:/Users/USER/Documents/Agent/app/api/app.py

````python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health, root
from app.core.application import ApplicationContext
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging


def create_app(
    settings: Settings | None = None,
    context: ApplicationContext | None = None,
) -> FastAPI:
    """Own lifespan in API mode, or borrow an already-started context in combined mode."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned = context is None
        resources = (
            context if context is not None else ApplicationContext(settings or get_settings())
        )
        if owned:
            configure_logging(resources.settings.log_level)
            await resources.start()
        elif not resources.runtime.startup_complete:
            raise RuntimeError("Shared application context has not started.")
        app.state.context = resources
        try:
            yield
        finally:
            if owned:
                await resources.close()

    app = FastAPI(title="Personal AI Assistant", lifespan=lifespan, debug=False)
    app.include_router(root.router)
    app.include_router(health.router)
    return app
````

### C:/Users/USER/Documents/Agent/app/api/dependencies.py

````python
from fastapi import Request

from app.core.application import ApplicationContext


def application_context(request: Request) -> ApplicationContext:
    return request.app.state.context
````

### C:/Users/USER/Documents/Agent/app/api/routes/__init__.py

````python
"""Informational root and dependency health routes only."""
````

### C:/Users/USER/Documents/Agent/app/api/routes/health.py

````python
import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.dependencies import application_context
from app.api.schemas.health import HealthResponse, LivenessResponse, ReadinessResponse, Services
from app.core.application import ApplicationContext
from app.database.health import check_database_health
from app.redis.health import check_redis_health

router = APIRouter(prefix="/health")
type Context = Annotated[ApplicationContext, Depends(application_context)]


async def snapshot(context: ApplicationContext) -> HealthResponse:
    async def database() -> str:
        if context.database is None:
            return "not_configured"
        return "ok" if await check_database_health(context.database.engine) else "unavailable"

    async def redis() -> str:
        if context.redis is None:
            return "not_configured"
        return "ok" if await check_redis_health(context.redis.client) else "unavailable"

    db, cache = await asyncio.gather(database(), redis())
    services = Services(
        application="ok" if context.runtime.startup_complete else "unavailable",
        database=db,
        redis=cache,
        telegram=context.runtime.telegram,
    )
    required_failed = (
        not context.runtime.startup_complete
        or (context.settings.security_state_backend == "redis" and cache != "ok")
        or (context.runtime.telegram_required and context.runtime.telegram != "running")
    )
    status = (
        "error"
        if required_failed
        else (
            "ok"
            if db == cache == "ok" and services.telegram in {"configured", "running"}
            else "degraded"
        )
    )
    return HealthResponse(status=status, services=services)


@router.get("", response_model=HealthResponse)
async def health(response: Response, context: Context) -> HealthResponse:
    result = await snapshot(context)
    response.status_code = 503 if result.status == "error" else 200
    return result


@router.get("/live", response_model=LivenessResponse)
async def live() -> LivenessResponse:
    return LivenessResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def ready(response: Response, context: Context) -> ReadinessResponse:
    result = await snapshot(context)
    response.status_code = 503 if result.status == "error" else 200
    return ReadinessResponse(status="not_ready" if result.status == "error" else "ready")
````

### C:/Users/USER/Documents/Agent/app/api/routes/root.py

````python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RootResponse(BaseModel):
    name: str = "Personal AI Assistant"
    status: str = "running"


@router.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    return RootResponse()
````

### C:/Users/USER/Documents/Agent/app/api/schemas/__init__.py

````python
"""Typed HTTP response contracts."""
````

### C:/Users/USER/Documents/Agent/app/api/schemas/health.py

````python
from typing import Literal

from pydantic import BaseModel

type ServiceStatus = Literal[
    "ok", "configured", "not_configured", "unavailable", "error", "running", "stopped"
]


class Services(BaseModel):
    application: ServiceStatus
    database: ServiceStatus
    redis: ServiceStatus
    telegram: ServiceStatus


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"]
    services: Services


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]


class LivenessResponse(BaseModel):
    status: Literal["alive"] = "alive"
````

### C:/Users/USER/Documents/Agent/app/bot/dispatcher.py

````python
from aiogram import Dispatcher
from aiogram.fsm.storage.base import BaseEventIsolation, BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation

from app.bot.context import BotContext
from app.bot.errors import SafeErrorMiddleware
from app.bot.handlers import common, menu, security
from app.bot.middlewares.lock_state import LockStateMiddleware
from app.bot.middlewares.owner_auth import OwnerAuthMiddleware


def create_dispatcher(
    context: BotContext,
    *,
    storage: BaseStorage | None = None,
    isolation: BaseEventIsolation | None = None,
) -> Dispatcher:
    """Authorize before allocating FSM state; isolate owner updates before lock checks."""
    dispatcher = Dispatcher(
        storage=storage if storage is not None else MemoryStorage(),
        events_isolation=isolation if isolation is not None else SimpleEventIsolation(),
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
            try:
                await self.context.security.lock()
                if state := data.get("state"):
                    await state.clear()
            except Exception as cleanup_error:  # noqa: BLE001 - Redis may also be unavailable
                report_error(logger, cleanup_error)
            incoming = update_event(event) if isinstance(event, Update) else None
            text = (
                f"⚠️ Xatolik yuz berdi.\n\nError ID: {error_id}"
                if data.get("owner_authorized")
                else DENIED
            )
            await safe_reply(incoming, text)
            return None
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
    if await app_context.security.guard.blocked():
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

### C:/Users/USER/Documents/Agent/app/bot/lifecycle.py

````python
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
from app.modules.audit.actions import AuditAction
from app.modules.security.lock_service import LockService
from app.modules.security.pin_service import PinService
from app.modules.security.redis_service import RedisSecurityService
from app.modules.security.redis_state import RedisUnlockGuard
from app.modules.security.service import SecurityService
from app.modules.security.unlock_guard import UnlockGuard
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
        self.context = BotContext(owner, self.settings.app_timezone, security, self.persistence)
        self.dispatcher = create_dispatcher(self.context, storage=storage, isolation=isolation)
        await self.bot.set_my_commands(
            [BotCommand(command=name, description=text) for name, text in COMMANDS.items()],
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
````

### C:/Users/USER/Documents/Agent/app/bot/run.py

````python
"""Telegram-only entrypoint using the same application lifecycle as the API."""

import asyncio
import logging

from app.core.application import ApplicationContext
from app.core.config import get_settings
from app.core.exceptions import RedisConfigurationError, TelegramConfigurationError
from app.core.logging import configure_logging, report_error


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    context = ApplicationContext(settings, telegram=True)
    try:
        await context.start()
        assert context.telegram is not None
        await context.telegram.poll()
    finally:
        await context.close()


def run() -> int:
    configure_logging()
    try:
        asyncio.run(main())
    except (TelegramConfigurationError, RedisConfigurationError) as error:
        print(str(error))
        return 1
    except KeyboardInterrupt:
        return 0
    except Exception as error:  # noqa: BLE001 - executable boundary
        print(f"Bot stopped. Error ID: {report_error(logging.getLogger('app.bot.run'), error)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
````

### C:/Users/USER/Documents/Agent/app/bot/storage.py

````python
from aiogram.fsm.storage.redis import RedisStorage


class SharedRedisStorage(RedisStorage):
    """Borrow the application-owned client; FSM shutdown must not close its pool."""

    async def close(self) -> None:
        pass
````

### C:/Users/USER/Documents/Agent/app/core/application.py

````python
"""One owner for shared resources across HTTP and Telegram transports."""

import asyncio
from contextlib import AsyncExitStack

from app.bot.lifecycle import TelegramRuntime
from app.bot.persistence import BotPersistence
from app.core.config import Settings
from app.core.exceptions import RedisConfigurationError, SecurityStateUnavailable
from app.core.runtime import RuntimeState
from app.database.session import DatabaseManager
from app.modules.security.lock_service import LockService
from app.modules.security.redis_state import RedisLockService
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
        )
        self.database: DatabaseManager | None = None
        self.redis: RedisManager | None = None
        self.lock = LockService()
        self.persistence = BotPersistence(None)
        self.telegram: TelegramRuntime | None = None
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
            if self.settings.security_state_backend == "redis":
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
            self.persistence.database = self.database
            if self.runtime.telegram_required:
                self.telegram = TelegramRuntime(
                    self.settings,
                    self.runtime,
                    self.persistence,
                    self.lock,
                    self.redis,
                )
                resources.push_async_callback(self.telegram.close)
                await self.telegram.prepare()
            self.runtime.startup_complete = True
        except BaseException:
            await self.close()
            raise

    async def close(self) -> None:
        self.runtime.startup_complete = False
        resources, self._resources = self._resources, None
        if resources is not None:
            await resources.aclose()
````

### C:/Users/USER/Documents/Agent/app/core/config.py

````python
from __future__ import annotations

from typing import Literal
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
    api_host: str = Field(default="127.0.0.1", min_length=1, alias="API_HOST")
    api_port: int = Field(default=8000, ge=1, le=65535, alias="API_PORT")
    security_state_backend: Literal["memory", "redis"] = Field(
        default="memory", alias="SECURITY_STATE_BACKEND"
    )
    redis_key_prefix: str = Field(
        default="personal_ai", pattern=r"^[a-zA-Z0-9:_-]{1,64}$", alias="REDIS_KEY_PREFIX"
    )

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


class RedisConfigurationError(ValueError):
    """Redis initialization requires a valid private service URL."""


class SecurityStateUnavailable(RuntimeError):
    """Shared security storage failed or a verification lease was lost."""
````

### C:/Users/USER/Documents/Agent/app/core/runtime.py

````python
from dataclasses import dataclass
from typing import Literal

type TelegramState = Literal["not_configured", "configured", "running", "stopped", "error"]


@dataclass
class RuntimeState:
    startup_complete: bool = False
    telegram: TelegramState = "not_configured"
    telegram_required: bool = False
````

### C:/Users/USER/Documents/Agent/app/modules/security/__init__.py

````python
"""Owner session security with explicit memory and shared Redis backends."""
````

### C:/Users/USER/Documents/Agent/app/modules/security/redis_service.py

````python
"""Serialize costly verification across processes and fence stale unlock results."""

import logging
from secrets import token_hex

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.exceptions import SecurityStateUnavailable
from app.modules.security.pin_service import PinService
from app.modules.security.redis_state import RedisLockService, RedisUnlockGuard
from app.modules.security.service import SecurityService, UnlockResult
from app.redis.keys import SecurityKeys

logger = logging.getLogger(__name__)
LEASE_SECONDS = 30
RELEASE = """
if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end
return 0
"""
COMPLETE = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return -1 end
if (redis.call('GET', KEYS[2]) or '0') ~= ARGV[2] then return -1 end
if redis.call('EXISTS', KEYS[4]) == 1 then return 2 end
if ARGV[3] == '1' then
    redis.call('DEL', KEYS[3], KEYS[4])
    redis.call('SET', KEYS[5], '0')
    redis.call('INCR', KEYS[2])
    return 0
end
local n = redis.call('INCR', KEYS[3])
redis.call('SET', KEYS[5], '1')
redis.call('INCR', KEYS[2])
if n >= tonumber(ARGV[4]) then
    redis.call('SET', KEYS[4], '1', 'EX', ARGV[5])
    redis.call('EXPIRE', KEYS[3], ARGV[5])
    return 2
end
return 1
"""


class RedisSecurityService(SecurityService):
    def __init__(
        self,
        client: Redis,
        keys: SecurityKeys,
        pin: PinService,
        guard: RedisUnlockGuard,
    ) -> None:
        super().__init__(RedisLockService(client, keys), pin, guard)
        self.client, self.keys = client, keys
        self.redis_guard = guard

    async def unlock(self, candidate: str) -> UnlockResult:
        token = token_hex(16)
        lease = self.keys.key("verification")
        try:
            if not await self.client.set(lease, token, nx=True, ex=LEASE_SECONDS):
                return UnlockResult.BLOCKED
            try:
                version = await self.client.get(self.keys.key("version")) or "0"
                if await self.guard.blocked():
                    return UnlockResult.BLOCKED
                verified = await self._pin.verify_pin(candidate)
                result = await self.client.eval(
                    COMPLETE,
                    5,
                    lease,
                    self.keys.key("version"),
                    self.keys.key("failures"),
                    self.keys.key("lockout"),
                    self.keys.key("locked"),
                    token,
                    version,
                    "1" if verified else "0",
                    self.redis_guard.max_attempts,
                    self.redis_guard.lockout_seconds,
                )
                if result == -1:
                    raise SecurityStateUnavailable("Security state changed; retry unlock.")
                return {0: UnlockResult.SUCCESS, 1: UnlockResult.FAILED, 2: UnlockResult.BLOCKED}[
                    result
                ]
            finally:
                await self.client.eval(RELEASE, 1, lease, token)
        except RedisError:
            logger.warning("security_state_unavailable")
            raise SecurityStateUnavailable("Shared security state is unavailable.") from None
````

### C:/Users/USER/Documents/Agent/app/modules/security/redis_state.py

````python
"""Shared security state. Atomic Redis scripts store no PIN or hash."""

from redis.asyncio import Redis

from app.modules.security.lock_service import LockService
from app.redis.keys import SecurityKeys

WRITE_LOCK = """
redis.call('SET', KEYS[1], ARGV[1])
redis.call('INCR', KEYS[2])
return 1
"""
FAILURE = """
if redis.call('EXISTS', KEYS[2]) == 1 then return tonumber(ARGV[1]) end
local n = redis.call('INCR', KEYS[1])
if n >= tonumber(ARGV[1]) then
    redis.call('SET', KEYS[2], '1', 'EX', ARGV[2])
    redis.call('EXPIRE', KEYS[1], ARGV[2])
end
return n
"""


class RedisLockStore:
    def __init__(self, client: Redis, keys: SecurityKeys) -> None:
        self.client, self.keys = client, keys

    async def read(self) -> bool:
        # Missing, corrupt or unexpected values can never unlock the session.
        return await self.client.get(self.keys.key("locked")) not in {"0", b"0"}

    async def write(self, locked: bool) -> None:
        await self.client.eval(
            WRITE_LOCK,
            2,
            self.keys.key("locked"),
            self.keys.key("version"),
            "1" if locked else "0",
        )


class RedisLockService(LockService):
    def __init__(self, client: Redis, keys: SecurityKeys) -> None:
        super().__init__(RedisLockStore(client, keys))


class RedisUnlockGuard:
    """Atomic failure increments with native TTL for lockout and counter expiration."""

    def __init__(
        self,
        client: Redis,
        keys: SecurityKeys,
        max_attempts: int = 5,
        lockout_seconds: int = 300,
    ) -> None:
        self.client, self.keys = client, keys
        self.max_attempts, self.lockout_seconds = max_attempts, lockout_seconds

    async def blocked(self) -> bool:
        return bool(await self.client.exists(self.keys.key("lockout")))

    async def record_failure(self) -> None:
        await self.client.eval(
            FAILURE,
            2,
            self.keys.key("failures"),
            self.keys.key("lockout"),
            self.max_attempts,
            self.lockout_seconds,
        )

    async def clear(self) -> None:
        await self.client.delete(self.keys.key("failures"), self.keys.key("lockout"))

    async def remaining(self) -> int:
        return max(0, await self.client.ttl(self.keys.key("lockout")))
````

### C:/Users/USER/Documents/Agent/app/modules/security/service.py

````python
import asyncio
from enum import StrEnum

from app.modules.security.lock_service import LockService
from app.modules.security.pin_service import PinService
from app.modules.security.unlock_guard import AttemptGuard


class UnlockResult(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"


class SecurityService:
    """Serialize lock transitions and verification, including concurrent callers."""

    def __init__(self, lock: LockService, pin: PinService, guard: AttemptGuard) -> None:
        self.lock_state = lock
        self._pin = pin
        self.guard = guard
        self._mutex = asyncio.Lock()

    async def lock(self) -> None:
        async with self._mutex:
            await self.lock_state.lock()

    async def unlock(self, candidate: str) -> UnlockResult:
        async with self._mutex:
            if await self.guard.blocked():
                return UnlockResult.BLOCKED
            if not await self._pin.verify_pin(candidate):
                await self.guard.record_failure()
                await self.lock_state.lock()
                return UnlockResult.BLOCKED if await self.guard.blocked() else UnlockResult.FAILED
            await self.guard.clear()
            await self.lock_state.unlock()
            return UnlockResult.SUCCESS
````

### C:/Users/USER/Documents/Agent/app/modules/security/unlock_guard.py

````python
from collections.abc import Callable
from time import monotonic
from typing import Protocol


class AttemptGuard(Protocol):
    async def blocked(self) -> bool: ...
    async def record_failure(self) -> None: ...
    async def clear(self) -> None: ...
    async def remaining(self) -> int: ...


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

    async def blocked(self) -> bool:
        return self.is_blocked()

    async def record_failure(self) -> None:
        self.failed()

    async def clear(self) -> None:
        self.reset()

    async def remaining(self) -> int:
        from math import ceil

        return max(0, ceil(self._blocked_until - self._clock())) if self.is_blocked() else 0
````

### C:/Users/USER/Documents/Agent/app/redis/__init__.py

````python
"""Explicit async Redis infrastructure; no import-time connections."""
````

### C:/Users/USER/Documents/Agent/app/redis/health.py

````python
import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


async def check_redis_health(client: Redis) -> bool:
    try:
        async with asyncio.timeout(3):
            return bool(await client.ping())
    except (RedisError, OSError, TimeoutError):
        logger.warning("redis_health_check_failed")
        return False
````

### C:/Users/USER/Documents/Agent/app/redis/keys.py

````python
from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityKeys:
    prefix: str
    owner_id: int

    @property
    def base(self) -> str:
        # A common hash tag keeps security Lua keys in one Redis Cluster slot.
        return f"{self.prefix}:security:{{{self.owner_id}}}"

    def key(self, name: str) -> str:
        return f"{self.base}:{name}"
````

### C:/Users/USER/Documents/Agent/app/redis/manager.py

````python
from urllib.parse import urlsplit

from redis.asyncio import Redis

from app.core.config import Settings
from app.core.exceptions import RedisConfigurationError


class RedisManager:
    """Own one Redis connection pool for the entire application lifespan."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Redis | None = None

    def initialize(self) -> None:
        if self._client is not None:
            return
        if not self._settings.redis_url:
            raise RedisConfigurationError("REDIS_URL is not configured.")
        raw = self._settings.redis_url.get_secret_value()
        try:
            url = urlsplit(raw)
            if url.scheme not in {"redis", "rediss"} or not url.hostname:
                raise ValueError("invalid scheme or host")
            _ = url.port
            self._client = Redis.from_url(
                raw,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                health_check_interval=30,
            )
        except ValueError:
            raise RedisConfigurationError(
                "REDIS_URL must be a valid redis:// or rediss:// URL."
            ) from None

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RedisConfigurationError("RedisManager.initialize() must be called first.")
        return self._client

    async def close(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            await client.aclose(close_connection_pool=True)
````

### C:/Users/USER/Documents/Agent/app/run_all.py

````python
"""One event loop and one resource owner for the explicit combined development mode."""

import asyncio
import logging
import signal
import socket
from collections.abc import Iterator
from contextlib import contextmanager
from types import FrameType

import uvicorn

from app.api.app import create_app
from app.core.application import ApplicationContext
from app.core.config import get_settings
from app.core.logging import configure_logging, report_error


class DevelopmentServer(uvicorn.Server):
    async def serve(self, sockets: list[socket.socket] | None = None) -> None:
        try:
            await super().serve(sockets=sockets)
        except SystemExit:
            raise RuntimeError("HTTP server startup failed.") from None

    @contextmanager
    def capture_signals(self) -> Iterator[None]:
        # asyncio.run owns Ctrl+C; avoid competing Uvicorn/Aiogram signal handlers.
        yield


@contextmanager
def cancel_on_sigterm() -> Iterator[None]:
    """Route service-manager termination through the same cleanup as Ctrl+C."""
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    assert task is not None
    previous = signal.getsignal(signal.SIGTERM)

    def terminate(signum: int, frame: FrameType | None) -> None:
        loop.call_soon_threadsafe(task.cancel)

    signal.signal(signal.SIGTERM, terminate)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


async def coordinate(context: ApplicationContext, server: uvicorn.Server) -> None:
    assert context.telegram is not None
    web = asyncio.create_task(server.serve(), name="http-server")
    bot = asyncio.create_task(context.telegram.poll(handle_signals=False), name="telegram-polling")
    try:
        done, _ = await asyncio.wait({web, bot}, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        server.should_exit = True
        try:
            await context.telegram.stop()
        except Exception as error:  # noqa: BLE001 - still drain both tasks after stop failure
            report_error(logging.getLogger(__name__), error)
        try:
            async with asyncio.timeout(15):
                await asyncio.gather(web, bot, return_exceptions=True)
        except TimeoutError:
            web.cancel()
            bot.cancel()
            await asyncio.gather(web, bot, return_exceptions=True)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    context = ApplicationContext(settings, telegram=True)
    with cancel_on_sigterm():
        try:
            await context.start()
            server = DevelopmentServer(
                uvicorn.Config(
                    create_app(context=context),
                    host=settings.api_host,
                    port=settings.api_port,
                    log_config=None,
                    access_log=False,
                    timeout_graceful_shutdown=10,
                )
            )
            await coordinate(context, server)
        finally:
            await context.close()


def run() -> int:
    configure_logging()
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        return 0
    except Exception as error:  # noqa: BLE001 - executable boundary
        report_error(logging.getLogger("app.run_all"), error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
````

### C:/Users/USER/Documents/Agent/app/run_api.py

````python
import uvicorn

from app.api.app import create_app
from app.core.config import get_settings
from app.core.logging import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        create_app(settings),
        host=settings.api_host,
        port=settings.api_port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
````

### C:/Users/USER/Documents/Agent/pyproject.toml

````toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "personal-ai-assistant"
version = "0.1.0"
description = "Private personal AI assistant backend and Telegram bot foundation"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "aiogram>=3.13.0,<4",
    "sqlalchemy>=2.0.0,<3",
    "asyncpg>=0.29.0",
    "alembic>=1.14.0",
    "redis>=5.0.0",
    "pydantic>=2.9.2,<3",
    "pydantic-settings>=2.7.1,<3",
    "structlog>=24.4.0",
    "python-dotenv>=1.0.1",
    "argon2-cffi>=23.1.0",
    "tzdata>=2024.1",
]

[project.optional-dependencies]
dev = [
    "fakeredis[lua]>=2.26,<3",
    "aiosqlite>=0.20.0,<1",
    "pytest>=8.3.2",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "ruff>=0.6.0",
]

[tool.setuptools.packages.find]
include = ["app", "app.*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"
````

### C:/Users/USER/Documents/Agent/README.md

````markdown
# Personal AI Assistant

## Stage 1 - Step 1

A private Telegram assistant built incrementally. Step 1 provides environment
loading, masked secrets, timezone validation and isolated configuration tests.
Step 2 adds database infrastructure, repositories, audit services and migrations.
Step 3 adds the private Telegram polling bot and owner session security.
Step 4 adds Redis security storage and a shared lifecycle for HTTP and Telegram.

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
| LOG_LEVEL | Logging level; INFO |
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

Docker, encryption, TOTP, Calendar, Gmail, AI, reminders and other future product
modules are not implemented yet.

## Next Development Step

Stage 1 Step 5: Google Calendar integration, calendar command/action service and
event create/read/update/delete foundation. Step 5 is not implemented here.

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
commands for the owner chat and attempts BOT_STARTED auditing. Shutdown attempts
BOT_STOPPED auditing and closes FSM, Telegram HTTP, Redis and DB resources.
Redis security state is preserved; the memory backend starts locked on restart.
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

With no stored state the bot starts locked. Redis restores the existing lock state.
/start, /help, /status, /id, /unlock and /lock remain usable while locked.
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

With SECURITY_STATE_BACKEND=memory, lock state, failed-attempt counters and FSM are
local to one process. Restart clears
attempts and pending PIN state and starts locked again. This is not a persistent
production security store, and restarting can reset a lockout. There is no idle
auto-lock or PIN prompt expiry yet. Step 4 provides Redis-backed shared state and
atomic attempt tracking. Do not share memory-backend state across multiple workers.

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

## Stage 1 - Step 4: Redis and HTTP Lifecycle

### Architecture and Ownership

ApplicationContext owns one database manager, one Redis manager, one lock service,
one persistence facade and (when enabled) one Telegram runtime. FastAPI routes access
it through request.app.state; Aiogram receives the same services via BotContext.
The API lifespan owns resources in API-only mode. In combined mode it borrows an
already-started context, so engines, pools and service instances are not duplicated.
Imports do not load credentials, connect to services or start polling.

New files live in app/redis/, app/api/, app/core/application.py,
app/core/runtime.py, app/bot/lifecycle.py and the explicit runners. Redis security
implementations live in app/modules/security/ alongside the memory implementation.

### Redis on Windows and Linux

Use memory mode temporarily, a private remote Redis instance, or Redis in WSL2.
Do not install abandoned unofficial Windows Redis builds. Docker support comes
later and is not part of this step. Example commands for an Ubuntu WSL distribution:

```powershell
wsl sudo apt update
wsl sudo apt install redis-server
wsl sudo service redis-server start
wsl redis-cli ping
```

On Ubuntu/Linux run the commands without the `wsl` prefix. Configure Redis to listen
on a private/local interface, not the public internet. Enable server persistence
(such as AOF) if state must survive Redis server restarts, not just bot restarts.
Use authentication and TLS on remote connections. This project does not change
Redis server configuration or install a server automatically.

### Configuration

```text
API_HOST=127.0.0.1
API_PORT=8000
SECURITY_STATE_BACKEND=memory
REDIS_KEY_PREFIX=personal_ai
REDIS_URL=
```

For a local Redis without credentials, REDIS_URL=redis://localhost:6379/0 is a
development example. For an authenticated server the format is
rediss://USER:PASSWORD@HOST:PORT/0 (placeholders only). Percent-encode special
characters in credentials and store the URL only in your ignored .env.

SECURITY_STATE_BACKEND accepts memory or redis. memory is the explicit development
default; configured Redis is then optional. redis requires REDIS_URL and a successful
startup PING. It never silently switches to memory after a Redis failure. Use redis
for shared/persistent security. Missing configuration does not break Settings or
imports; explicit Redis initialization raises RedisConfigurationError.

### Shared Security

Keys use REDIS_KEY_PREFIX and the configured numeric owner as a namespace, for
example personal_ai:security:{OWNER_ID}:locked. A missing or unexpected lock value
means locked. Explicit lock/unlock writes 1/0. No Telegram/API token, PIN or PIN hash is stored
in Redis. Use the same prefix and owner settings for transports sharing security.
API-only mode without an owner has an unused default-locked namespace; no security
write endpoints are exposed.

Failure increments and threshold activation use atomic Lua. At the threshold, both
the lockout and failure count receive native Redis TTLs. Partial failure counts stay
until successful unlock or threshold expiration. Success clears failures atomically
with unlock. remaining() returns remaining lockout seconds.

Verification is serialized across processes using a 30-second Redis lease. A
contending attempt is rejected without hashing. Unlock commits verify lease ownership
and a lock-state revision atomically, so a slow/stale verification cannot undo a more
recent lock. Lease expiration fails closed. The memory service still uses its local
mutex. Redis outages block security actions and generate safe error replies; there
is no memory fallback. Redis atomicity tests execute the real Lua scripts with
fakeredis[lua], a dev-only dependency, rather than reimplementing their logic in mocks.

Aiogram FSM uses the same Redis client and a namespaced key builder in redis mode.
FSM storage borrows the client and does not close the shared pool. PIN text is never
stored in FSM data. Redis state survives bot restarts, including an unlocked state;
use /lock explicitly when leaving the session. Idle locking is not implemented yet.
Redis server persistence, backups and failover remain operational responsibilities.
Only one Telegram poller may run per token even with shared Redis storage.

### Run Modes (PowerShell)

API only, no Telegram credentials or PIN needed:

```powershell
.\.venv\Scripts\python.exe -m app.run_api
```

Equivalent factory command (host/port here override runner settings):

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Telegram only, with the Step 3 credentials:

```powershell
.\.venv\Scripts\python.exe -m app.bot.run
```

Combined development mode, one event loop/context:

```powershell
.\.venv\Scripts\python.exe -m app.run_all
```

Do not run the Telegram-only and combined commands simultaneously with the same
token. API-only plus a separate bot process has separate pools by process; redis
security state is shared when both use identical settings. Combined mode shares
the actual resource instances. No reload/workers are enabled in combined mode.
Ctrl+C (and SIGTERM in combined mode) stops polling and HTTP before closing Telegram
HTTP, Redis and PostgreSQL.
If either component ends or fails, the coordinator shuts down the other and drains
tasks. Application cleanup is idempotent and startup failures close partial resources.
Lifecycle audit insertion errors are logged safely and do not prevent cleanup.

### Endpoints and Readiness Rules

| Endpoint | Purpose |
| --- | --- |
| GET / | Project name and running status only |
| GET /health/live | Process alive; no network dependency checks |
| GET /health | Typed detailed dependency summary |
| GET /health/ready | Required resources usable |

Database and Redis statuses come from actual SELECT 1/PING checks with timeouts.
They are not_configured when absent, unavailable on connectivity failure, and ok
only after a successful query. Telegram status is internal configuration/task state:
configured in API-only mode, running while polling task is active, stopped or error
after polling exits. Health requests never call Telegram. running means the polling
task is active, not that Telegram's network is currently reachable during SDK retries.

At this stage PostgreSQL is optional because bot actions support explicitly logged
missing persistence. Redis is required only when SECURITY_STATE_BACKEND=redis.
Telegram running is required in Telegram/combined modes. The application must have
completed startup. Required failures yield status=error and HTTP 503. Optional
missing/unavailable services yield degraded and HTTP 200; otherwise status=ok.
Readiness is 200 ready when required services are usable, even if optional services
make the detailed summary degraded. Liveness stays 200 alive during dependency outages.
No URLs, credentials, owner IDs, exception text or audit records appear in responses.

Illustrative response only; actual results reflect runtime configuration:

```json
{
  "status": "degraded",
  "services": {
    "application": "ok",
    "database": "not_configured",
    "redis": "not_configured",
    "telegram": "configured"
  }
}
```

```powershell
Invoke-RestMethod http://127.0.0.1:8000/
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

### Step 4 Verification and Limits

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m compileall app tests migrations
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check .
```

All default tests are offline: fake Redis with Lua, SQLite and a fake Telegram API.
ASGI tests explicitly enter the application lifespan. Live Redis/PostgreSQL/Telegram
are separate verification steps and are not claimed healthy when unconfigured.
No admin/write HTTP API, Docker, scheduler, webhook, Calendar, Gmail or AI integration
was added. The next planned step is Stage 1 Step 5: Google Calendar integration and
the calendar command/action service with create/read/update/delete foundations.
````

### C:/Users/USER/Documents/Agent/tests/bot/test_lifecycle.py

````python
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram import Bot, Dispatcher

from app.bot import lifecycle, run
from app.core import application
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
    monkeypatch.setattr(lifecycle, "create_bot", lambda settings: bot)
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
    monkeypatch.setattr(lifecycle, "create_bot", lambda settings: bot)
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
    monkeypatch.setattr(lifecycle, "create_bot", lambda settings: bot)
    monkeypatch.setattr(application, "DatabaseManager", lambda settings: database)
    monkeypatch.setattr(application, "BotPersistence", lambda database: persistence)
    monkeypatch.setattr(Dispatcher, "start_polling", AsyncMock(return_value=None))
    await run.main()
    database.initialize.assert_called_once()
    database.dispose.assert_awaited_once()
    persistence.audit.assert_any_await(AuditAction.BOT_STARTED)
    persistence.audit.assert_any_await(AuditAction.BOT_STOPPED)
    assert api.closed
````

### C:/Users/USER/Documents/Agent/tests/test_api.py

````python
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.api.app import create_app
from app.core.application import ApplicationContext
from app.core.config import Settings
from app.core.exceptions import RedisConfigurationError, SecurityStateUnavailable


def settings(**kwargs: object) -> Settings:
    values = {
        "DATABASE_URL": None,
        "REDIS_URL": None,
        "TELEGRAM_BOT_TOKEN": None,
        "TELEGRAM_OWNER_ID": None,
        "SECURITY_STATE_BACKEND": "memory",
    }
    values.update(kwargs)
    return Settings(_env_file=None, **values)


def test_backend_config_validation() -> None:
    assert settings().security_state_backend == "memory"
    assert settings(SECURITY_STATE_BACKEND="redis").security_state_backend == "redis"
    with pytest.raises(ValidationError):
        settings(SECURITY_STATE_BACKEND="other")


async def test_redis_backend_requires_url() -> None:
    context = ApplicationContext(settings(SECURITY_STATE_BACKEND="redis"))
    with pytest.raises(RedisConfigurationError):
        await context.start()
    assert not context.runtime.startup_complete


async def test_redis_required_no_fallback() -> None:
    redis = Mock()
    redis.close = AsyncMock()
    with (
        patch("app.core.application.RedisManager", return_value=redis),
        patch("app.core.application.check_redis_health", new=AsyncMock(return_value=False)),
    ):
        context = ApplicationContext(
            settings(SECURITY_STATE_BACKEND="redis", REDIS_URL="redis://local")
        )
        with pytest.raises(SecurityStateUnavailable):
            await context.start()
        redis.close.assert_awaited_once()


async def test_root_live_degraded_ready() -> None:
    app = create_app(settings())
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/")).json() == {
                "name": "Personal AI Assistant",
                "status": "running",
            }
            assert (await client.get("/health/live")).json() == {"status": "alive"}
            health = await client.get("/health")
            assert health.status_code == 200
            assert health.json() == {
                "status": "degraded",
                "services": {
                    "application": "ok",
                    "database": "not_configured",
                    "redis": "not_configured",
                    "telegram": "not_configured",
                },
            }
            assert (await client.get("/health/ready")).json() == {"status": "ready"}
        assert app.state.context.runtime.startup_complete
    assert not app.state.context.runtime.startup_complete


@pytest.mark.parametrize("healthy", [True, False])
async def test_optional_dependency_health_truthful_and_no_secrets(healthy: bool) -> None:
    context = ApplicationContext(
        settings(TELEGRAM_BOT_TOKEN="test-secret-token", TELEGRAM_OWNER_ID=42)
    )
    await context.start()
    context.database = Mock()
    context.redis = Mock()
    app = create_app(context=context)
    with (
        patch("app.api.routes.health.check_database_health", new=AsyncMock(return_value=healthy)),
        patch("app.api.routes.health.check_redis_health", new=AsyncMock(return_value=healthy)),
    ):
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["services"]["database"] == ("ok" if healthy else "unavailable")
            assert response.json()["services"]["redis"] == ("ok" if healthy else "unavailable")
            assert response.json()["services"]["telegram"] == "configured"
            assert response.json()["status"] == ("ok" if healthy else "degraded")
            assert "test-secret-token" not in response.text
            assert "42" not in response.text
    assert context.runtime.startup_complete  # borrowed lifespan does not dispose owner resources
    await context.close()


async def test_required_dependency_failure_readiness() -> None:
    context = ApplicationContext(settings())
    await context.start()
    context.settings.security_state_backend = "redis"
    context.redis = Mock()
    app = create_app(context=context)
    with patch("app.api.routes.health.check_redis_health", new=AsyncMock(return_value=False)):
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            assert (await client.get("/health")).status_code == 503
            assert (await client.get("/health/ready")).status_code == 503
            assert (await client.get("/health/live")).status_code == 200
    await context.close()


async def test_context_initializes_once_and_cleans_reverse_order() -> None:
    calls: list[str] = []
    db, redis = Mock(), Mock()
    db.dispose = AsyncMock(side_effect=lambda: calls.append("database"))
    redis.close = AsyncMock(side_effect=lambda: calls.append("redis"))
    with (
        patch("app.core.application.DatabaseManager", return_value=db),
        patch("app.core.application.RedisManager", return_value=redis),
    ):
        context = ApplicationContext(settings(DATABASE_URL="test-url", REDIS_URL="test-url"))
        await context.start()
        await context.start()
        db.initialize.assert_called_once()
        redis.initialize.assert_called_once()
        await context.close()
        await context.close()
        assert calls == ["redis", "database"]
````

### C:/Users/USER/Documents/Agent/tests/test_coordination.py

````python
import asyncio
import signal
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.application import ApplicationContext
from app.run_all import cancel_on_sigterm, coordinate


async def test_sigterm_uses_cancellation_and_restores_handler() -> None:
    previous = signal.getsignal(signal.SIGTERM)
    entered = asyncio.Event()

    async def worker() -> None:
        with cancel_on_sigterm():
            entered.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(worker())
    await entered.wait()
    handler = signal.getsignal(signal.SIGTERM)
    assert callable(handler)
    handler(signal.SIGTERM, None)
    with pytest.raises(asyncio.CancelledError):
        await task
    assert signal.getsignal(signal.SIGTERM) == previous


class FakeServer:
    def __init__(self) -> None:
        self.should_exit = False
        self.closed = False

    async def serve(self) -> None:
        try:
            while not self.should_exit:
                await asyncio.sleep(0.01)
        finally:
            self.closed = True


async def test_bot_failure_stops_web_and_drains_tasks() -> None:
    context = Mock(spec=ApplicationContext)
    context.telegram = Mock()
    context.telegram.poll = AsyncMock(side_effect=RuntimeError("test component failure"))
    context.telegram.stop = AsyncMock()
    server = FakeServer()
    with pytest.raises(RuntimeError, match="test component failure"):
        await coordinate(context, server)
    assert server.closed
    context.telegram.stop.assert_awaited_once()
    assert not any(t.get_name() in {"http-server", "telegram-polling"} for t in asyncio.all_tasks())


async def test_combined_cancellation_drains_both_components() -> None:
    context = Mock(spec=ApplicationContext)
    context.telegram = Mock()
    stopped = asyncio.Event()
    started = asyncio.Event()

    async def poll(handle_signals: bool) -> None:
        started.set()
        await stopped.wait()

    context.telegram.poll = poll
    context.telegram.stop = AsyncMock(side_effect=stopped.set)
    server = FakeServer()
    task = asyncio.create_task(coordinate(context, server))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert server.closed
    assert not any(t.get_name() in {"http-server", "telegram-polling"} for t in asyncio.all_tasks())
````

### C:/Users/USER/Documents/Agent/tests/test_redis_state.py

````python
import asyncio
import importlib
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import pytest
import pytest_asyncio
from argon2 import PasswordHasher
from redis.asyncio import Redis

from app.core.config import Settings
from app.core.exceptions import RedisConfigurationError, SecurityStateUnavailable
from app.modules.security.pin_service import PinService
from app.modules.security.redis_service import RedisSecurityService
from app.modules.security.redis_state import RedisLockService, RedisUnlockGuard
from app.modules.security.service import UnlockResult
from app.redis.health import check_redis_health
from app.redis.keys import SecurityKeys
from app.redis.manager import RedisManager


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[Redis]:
    async with fakeredis.aioredis.FakeRedis(decode_responses=True) as client:
        yield client


def test_import_does_not_construct_redis_client() -> None:
    with patch("redis.asyncio.Redis.from_url") as create:
        importlib.reload(importlib.import_module("app.redis.manager"))
        create.assert_not_called()


def test_manager_explicit_missing_and_invalid_url() -> None:
    with patch("app.redis.manager.Redis.from_url") as create:
        manager = RedisManager(Settings(_env_file=None, REDIS_URL=None))
        create.assert_not_called()
        with pytest.raises(RedisConfigurationError, match="not configured"):
            manager.initialize()
    with pytest.raises(RedisConfigurationError):
        RedisManager(Settings(_env_file=None, REDIS_URL="https://bad.example")).initialize()


async def test_manager_reuses_and_closes() -> None:
    client = AsyncMock()
    with patch("app.redis.manager.Redis.from_url", return_value=client) as create:
        manager = RedisManager(Settings(_env_file=None, REDIS_URL="redis://localhost/0"))
        manager.initialize()
        manager.initialize()
        assert manager.client is client
        create.assert_called_once()
        await manager.close()
        await manager.close()
        client.aclose.assert_awaited_once()


async def test_health(redis_client: Redis) -> None:
    assert await check_redis_health(redis_client)
    with patch.object(redis_client, "ping", side_effect=OSError("test-secret")):
        assert not await check_redis_health(redis_client)


async def test_lock_default_persistence_and_corruption(redis_client: Redis) -> None:
    keys = SecurityKeys("test", 42)
    first = RedisLockService(redis_client, keys)
    assert await first.is_locked()
    await first.unlock()
    assert not await RedisLockService(redis_client, keys).is_locked()
    await first.lock()
    assert await first.is_locked()
    await redis_client.set(keys.key("locked"), "invalid")
    assert await first.is_locked()


async def test_guard_atomic_threshold_ttl_and_clear(redis_client: Redis) -> None:
    keys = SecurityKeys("test", 42)
    guard = RedisUnlockGuard(redis_client, keys, max_attempts=5, lockout_seconds=300)
    assert not await guard.blocked()
    await asyncio.gather(*[guard.record_failure() for _ in range(5)])
    assert await redis_client.get(keys.key("failures")) == "5"
    assert await guard.blocked()
    assert 0 < await guard.remaining() <= 300
    assert 0 < await redis_client.ttl(keys.key("failures")) <= 300
    await guard.clear()
    assert not await guard.blocked()
    assert await redis_client.get(keys.key("failures")) is None


async def test_guard_ttl_expires(redis_client: Redis) -> None:
    guard = RedisUnlockGuard(redis_client, SecurityKeys("test", 42), 1, 1)
    await guard.record_failure()
    await asyncio.sleep(1.05)
    assert not await guard.blocked()
    assert await guard.remaining() == 0


async def test_success_resets_failures(redis_client: Redis) -> None:
    keys = SecurityKeys("test", 42)
    pin = PinService(PasswordHasher().hash("test-pin-only"))
    guard = RedisUnlockGuard(redis_client, keys)
    service = RedisSecurityService(redis_client, keys, pin, guard)
    assert await service.unlock("wrong-test-only") == UnlockResult.FAILED
    assert await service.unlock("test-pin-only") == UnlockResult.SUCCESS
    assert not await service.lock_state.is_locked()
    assert await redis_client.get(keys.key("failures")) is None


async def test_lock_during_verification_cannot_be_undone(redis_client: Redis) -> None:
    keys = SecurityKeys("test", 42)
    pin = AsyncMock(spec=PinService)
    service = RedisSecurityService(redis_client, keys, pin, RedisUnlockGuard(redis_client, keys))

    async def verify(candidate: str) -> bool:
        await service.lock()
        return True

    pin.verify_pin.side_effect = verify
    with pytest.raises(SecurityStateUnavailable):
        await service.unlock("test-pin-only")
    assert await service.lock_state.is_locked()


async def test_expired_lease_cannot_unlock(redis_client: Redis) -> None:
    keys = SecurityKeys("test", 42)
    pin = AsyncMock(spec=PinService)
    service = RedisSecurityService(redis_client, keys, pin, RedisUnlockGuard(redis_client, keys))

    async def verify(candidate: str) -> bool:
        await redis_client.delete(keys.key("verification"))
        return True

    pin.verify_pin.side_effect = verify
    with pytest.raises(SecurityStateUnavailable):
        await service.unlock("test-pin-only")
    assert await service.lock_state.is_locked()


async def test_multiple_instances_share_lockout(redis_client: Redis) -> None:
    keys = SecurityKeys("test", 42)
    pin = AsyncMock(spec=PinService)
    pin.verify_pin.return_value = False
    one = RedisSecurityService(redis_client, keys, pin, RedisUnlockGuard(redis_client, keys, 1))
    two = RedisSecurityService(redis_client, keys, pin, RedisUnlockGuard(redis_client, keys, 1))
    assert await one.unlock("wrong-test-only") == UnlockResult.BLOCKED
    assert await two.unlock("test-pin-only") == UnlockResult.BLOCKED
    assert pin.verify_pin.await_count == 1
````

### C:/Users/USER/Documents/Agent/tests/test_shared_fsm.py

````python
import fakeredis.aioredis
from aiogram.fsm.storage.base import DefaultKeyBuilder, StorageKey

from app.bot.storage import SharedRedisStorage


async def test_fsm_survives_storage_shutdown_without_closing_shared_pool() -> None:
    async with fakeredis.aioredis.FakeRedis(decode_responses=True) as client:
        builder = DefaultKeyBuilder(prefix="test:shared_fsm", with_bot_id=True)
        first = SharedRedisStorage(client, key_builder=builder)
        second = SharedRedisStorage(client, key_builder=builder)
        key = StorageKey(bot_id=1, chat_id=42, user_id=42)
        await first.set_state(key, "UnlockFlow:waiting_for_pin")
        await first.close()
        assert await client.ping()
        assert await second.get_state(key) == "UnlockFlow:waiting_for_pin"
        assert await second.get_data(key) == {}
````

