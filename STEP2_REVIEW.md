# Stage 1 Step 2 - Complete File Contents

Repository: C:/Users/USER/Documents/Agent

## Verification

- PASS: Python 3.12.10, dependencies installed including dev-only aiosqlite.
- PASS: 37 tests (16 existing Step 1 tests and 21 new database tests).
- PASS: compileall, Ruff, pip check and configuration verification.
- PASS: Alembic offline upgrade and downgrade PostgreSQL SQL generation.
- BLOCKED: PostgreSQL migration execution and full live database verification. DATABASE_URL is unset; no PostgreSQL service or psql command was found.
- Initial migration was authored manually; autogenerate was not run.
- No Step 3 implementation, Redis, Docker or HTTP routes were added.

## Design Decisions

One explicitly initialized manager owns the engine and session factory. Repositories flush; the application controls transactions through the session context manager. Audit history survives user deletion through ON DELETE SET NULL. PostgreSQL uses JSONB and timezone-aware timestamps; isolated SQLite tests use compatible JSON and integer PK variants. Secret-bearing URLs are never printed by application helpers. Audit metadata rejects known sensitive keys, but callers must never pass raw user content or credentials.

## Changed Files

- `pyproject.toml`
- `.env.example`
- `README.md`
- `app/core/exceptions.py`
- `app/database/__init__.py`
- `app/database/base.py`
- `app/database/session.py`
- `app/database/health.py`
- `app/database/models/__init__.py`
- `app/database/models/user.py`
- `app/database/models/audit_log.py`
- `app/modules/__init__.py`
- `app/modules/users/__init__.py`
- `app/modules/users/repository.py`
- `app/modules/audit/__init__.py`
- `app/modules/audit/actions.py`
- `app/modules/audit/repository.py`
- `app/modules/audit/service.py`
- `alembic.ini`
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/0001_initial_users_audit_logs.py`
- `tests/conftest.py`
- `tests/test_database_config.py`
- `tests/test_user_repository.py`
- `tests/test_audit_service.py`

## Complete Contents

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
````

### C:/Users/USER/Documents/Agent/README.md

````markdown
# Personal AI Assistant

## Stage 1 - Step 1

A private Telegram assistant built incrementally. Step 1 provides environment
loading, masked secrets, timezone validation and isolated configuration tests.
Step 2 adds database infrastructure, repositories, audit services and migrations.

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
| BOT_PIN | Optional secret, no default PIN |

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
- Configure a strong PIN later; hashing, rate limits and session locking are future work.
- Features must fail closed when required credentials or authorization are missing.
- Dependency constraints are not a reproducible deployment lockfile.

## Not Implemented Yet

FastAPI server, HTTP health endpoints, Telegram handlers, owner middleware, Redis,
locks, Docker, encryption, TOTP and future product modules are not implemented yet.

## Next Development Step

Stage 1 Step 3: Private Telegram Bot, centralized owner authorization and lock/unlock
foundation. Step 3 is not implemented here.

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
future application-layer rule.

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
````

### C:/Users/USER/Documents/Agent/app/core/exceptions.py

````python
"""Safe application errors that do not contain credentials."""


class DatabaseConfigurationError(ValueError):
    """Database initialization requires a valid PostgreSQL configuration."""


class AuditDetailsError(ValueError):
    """Audit details must be JSON data without sensitive fields."""
````

### C:/Users/USER/Documents/Agent/app/database/__init__.py

````python
"""Database infrastructure; importing this package never opens connections."""
````

### C:/Users/USER/Documents/Agent/app/database/base.py

````python
"""Shared ORM metadata and UTC timestamp behavior."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """Reject naive writes and restore UTC awareness for SQLite test reads."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timezone-aware datetime required")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now(), onupdate=func.now()
    )
````

### C:/Users/USER/Documents/Agent/app/database/session.py

````python
"""Explicit, reusable database lifecycle with caller-owned transactions."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.core.exceptions import DatabaseConfigurationError


def database_url(settings: Settings) -> URL:
    """Validate only when database initialization is requested; never expose the URL."""
    if not settings.database_url:
        raise DatabaseConfigurationError("DATABASE_URL is not configured.")
    try:
        url = make_url(settings.database_url.get_secret_value())
        valid = url.drivername == "postgresql+asyncpg" and bool(url.host and url.database)
        _ = url.port
    except (ArgumentError, ValueError):
        raise DatabaseConfigurationError("DATABASE_URL is invalid.") from None
    if not valid:
        raise DatabaseConfigurationError(
            "DATABASE_URL must use postgresql+asyncpg with host/database."
        )
    return url


class DatabaseManager:
    """Own one engine/pool per application lifespan; inject this instance into services."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: AsyncEngine | None = None
        self._sessions: async_sessionmaker[AsyncSession] | None = None

    def initialize(self) -> None:
        if self._engine is not None:
            return
        self._engine = create_async_engine(
            database_url(self._settings),
            pool_pre_ping=True,
            echo=False,
            hide_parameters=True,
            connect_args={"server_settings": {"timezone": "UTC"}, "timeout": 10},
        )
        self._sessions = async_sessionmaker(self._engine, expire_on_commit=False)

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise DatabaseConfigurationError("DatabaseManager.initialize() must be called first.")
        return self._engine

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Commit on successful scope exit; rollback and close on failure/cancellation."""
        if self._sessions is None:
            raise DatabaseConfigurationError("DatabaseManager.initialize() must be called first.")
        async with self._sessions.begin() as session:
            yield session

    async def dispose(self) -> None:
        """Close the pool after all active work has finished."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessions = None
````

### C:/Users/USER/Documents/Agent/app/database/health.py

````python
"""Credential-free database connectivity check."""

import asyncio
import logging

from asyncpg import PostgresError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def check_database_health(engine: AsyncEngine, timeout_seconds: float = 5) -> bool:
    try:
        async with asyncio.timeout(timeout_seconds):
            async with engine.connect() as connection:
                return await connection.scalar(text("SELECT 1")) == 1
    except (SQLAlchemyError, PostgresError, OSError, TimeoutError):
        logger.warning("database_health_check_failed")
        return False
````

### C:/Users/USER/Documents/Agent/app/database/models/__init__.py

````python
"""Import all mapped models so migrations discover complete metadata."""

from app.database.models.audit_log import AuditLog
from app.database.models.user import User

__all__ = ["AuditLog", "User"]
````

### C:/Users/USER/Documents/Agent/app/database/models/user.py

````python
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UTCDateTime


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    last_seen_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
````

### C:/Users/USER/Documents/Agent/app/database/models/audit_log.py

````python
from datetime import datetime

from sqlalchemy import JSON, BigInteger, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[str | None] = mapped_column(String(255))
    details: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict, server_default="{}"
    )
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now(), index=True
    )
````

### C:/Users/USER/Documents/Agent/app/modules/__init__.py

````python
"""Application modules."""
````

### C:/Users/USER/Documents/Agent/app/modules/users/__init__.py

````python
"""User persistence."""
````

### C:/Users/USER/Documents/Agent/app/modules/users/repository.py

````python
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


class UserRepository:
    """Persist users in an injected session without committing transactions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_telegram_user_id(self, telegram_user_id: int) -> User | None:
        return await self.session.scalar(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )

    async def create(
        self,
        telegram_user_id: int,
        *,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        if telegram_user_id <= 0:
            raise ValueError("Telegram user ID must be positive")
        user = User(
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            first_name=first_name,
            last_name=last_name,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_last_seen(self, user_id: int, at: datetime | None = None) -> bool:
        timestamp = at if at is not None else datetime.now(UTC)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Timezone-aware datetime required")
        result = await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_seen_at=timestamp.astimezone(UTC))
            .returning(User.id)
        )
        await self.session.flush()
        return result.scalar_one_or_none() is not None
````

### C:/Users/USER/Documents/Agent/app/modules/audit/__init__.py

````python
"""Audit event validation and persistence."""
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
````

### C:/Users/USER/Documents/Agent/app/modules/audit/repository.py

````python
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AuditLog


class AuditRepository:
    """Low-level persistence; callers must validate payloads through AuditService."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, event: AuditLog) -> AuditLog:
        self.session.add(event)
        await self.session.flush()
        return event
````

### C:/Users/USER/Documents/Agent/app/modules/audit/service.py

````python
"""Audit only purpose-built metadata, never raw messages or credential payloads."""

import json
from ipaddress import ip_address as parse_ip

from app.core.exceptions import AuditDetailsError
from app.database.models import AuditLog
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository

SENSITIVE_PARTS = (
    "password",
    "secret",
    "token",
    "pin",
    "apikey",
    "apihash",
    "sessionstring",
    "authorization",
    "cookie",
    "databaseurl",
    "redisurl",
    "encryptionkey",
)


def validated_details(details: dict[str, object] | None) -> dict[str, object]:
    """Reject known credential keys and non-JSON values; this is not a secret detector."""

    def inspect(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise AuditDetailsError("Audit detail keys must be strings.")
                normalized = "".join(c for c in key.lower() if c.isalnum())
                if any(part in normalized for part in SENSITIVE_PARTS):
                    raise AuditDetailsError("Sensitive audit detail fields are prohibited.")
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
        elif value is not None and not isinstance(value, (str, bool, int, float)):
            raise AuditDetailsError("Audit details must contain JSON values only.")

    if details is not None and not isinstance(details, dict):
        raise AuditDetailsError("Audit details must be a JSON object.")
    try:
        inspect(details)
        encoded = json.dumps(details if details is not None else {}, allow_nan=False)
        if len(encoded.encode("utf-8")) > 16384:
            raise AuditDetailsError("Audit details exceed 16 KiB.")
        return json.loads(encoded)
    except (TypeError, ValueError, RecursionError):
        raise AuditDetailsError(
            "Audit details must be bounded JSON without sensitive fields."
        ) from None


class AuditService:
    """Append audit events in the caller's transaction; never commit or log payloads."""

    def __init__(self, repository: AuditRepository) -> None:
        self.repository = repository

    async def log_event(
        self,
        action: AuditAction,
        *,
        user_id: int | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        details: dict[str, object] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        if not isinstance(action, AuditAction):
            raise TypeError("Unsupported audit action")
        if ip_address is not None:
            try:
                ip_address = str(parse_ip(ip_address))
            except ValueError:
                raise ValueError("Invalid audit IP address") from None
        return await self.repository.add(
            AuditLog(
                action=action.value,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                details=validated_details(details),
                ip_address=ip_address,
            )
        )
````

### C:/Users/USER/Documents/Agent/alembic.ini

````text
[alembic]
script_location = %(here)s/migrations
prepend_sys_path = %(here)s
path_separator = os
````

### C:/Users/USER/Documents/Agent/migrations/env.py

````python
"""Async online migrations and PostgreSQL-only offline SQL generation."""

import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.database.base import Base, UTCDateTime
from app.database.models import AuditLog, User  # noqa: F401
from app.database.session import database_url

target_metadata = Base.metadata


def render_item(item_type: str, obj: object, autogen_context: object) -> str | bool:
    if item_type == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    engine = create_async_engine(
        database_url(get_settings()),
        poolclass=pool.NullPool,
        hide_parameters=True,
        connect_args={"server_settings": {"timezone": "UTC"}, "timeout": 10},
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    context.configure(
        dialect_name="postgresql",
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_online())
````

### C:/Users/USER/Documents/Agent/migrations/script.py.mako

````text
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | Sequence[str] | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
````

### C:/Users/USER/Documents/Agent/migrations/versions/0001_initial_users_audit_logs.py

````python
"""Initial users and audit_logs schema; authored manually, not autogenerated."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.String(64), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("telegram_user_id", name="uq_users_telegram_user_id"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("details", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_audit_logs_user_id_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("users")
````

### C:/Users/USER/Documents/Agent/tests/conftest.py

````python
"""SQLite fixtures are isolated per test and never use DATABASE_URL."""

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import ConnectionPoolEntry

from app.database.base import Base
from app.database.models import AuditLog, User  # noqa: F401


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection: DBAPIConnection, record: ConnectionPoolEntry) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
````

### C:/Users/USER/Documents/Agent/tests/test_database_config.py

````python
import subprocess
import sys
from unittest.mock import patch

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from sqlalchemy.schema import CreateTable

from app.core.config import Settings
from app.core.exceptions import DatabaseConfigurationError
from app.database.health import check_database_health
from app.database.models import AuditLog, User
from app.database.session import DatabaseManager, database_url
from app.modules.users.repository import UserRepository


def test_import_and_initialization_without_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    code = (
        "from unittest.mock import patch\n"
        "with patch('sqlalchemy.ext.asyncio.create_async_engine') as create:\n"
        "    import app.database.models\n"
        "    import app.database.session\n"
        "    create.assert_not_called()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, timeout=15, check=False
    )
    assert result.returncode == 0
    manager = DatabaseManager(Settings(_env_file=None, DATABASE_URL=None))
    with pytest.raises(DatabaseConfigurationError, match="DATABASE_URL is not configured"):
        manager.initialize()


@pytest.mark.parametrize("url", ["not-a-url", "sqlite:///db", "postgresql+asyncpg://host"])
def test_invalid_url_redacted(url: str) -> None:
    with pytest.raises(DatabaseConfigurationError) as caught:
        database_url(Settings(_env_file=None, DATABASE_URL=url))
    assert url not in str(caught.value)


async def test_lifecycle_and_transactions(engine: AsyncEngine) -> None:
    manager = DatabaseManager(Settings(_env_file=None, DATABASE_URL=None))
    with (
        patch("app.database.session.database_url"),
        patch("app.database.session.create_async_engine", return_value=engine) as create,
    ):
        manager.initialize()
        manager.initialize()
        create.assert_called_once()
    async with manager.session() as session:
        await UserRepository(session).create(42)
    with pytest.raises(RuntimeError):
        async with manager.session() as session:
            await UserRepository(session).create(43)
            raise RuntimeError("rollback")
    async with async_sessionmaker(engine)() as session:
        assert await UserRepository(session).get_by_telegram_user_id(42) is not None
        assert await UserRepository(session).get_by_telegram_user_id(43) is None
    await manager.dispose()
    await manager.dispose()
    with pytest.raises(DatabaseConfigurationError):
        _ = manager.engine


async def test_health(engine: AsyncEngine) -> None:
    assert await check_database_health(engine)
    with patch.object(
        engine.sync_engine,
        "connect",
        side_effect=OperationalError("SELECT 1", {}, Exception("sensitive")),
    ):
        assert not await check_database_health(engine)


async def test_dispose_before_initialize() -> None:
    manager = DatabaseManager(Settings(_env_file=None, DATABASE_URL=None))
    await manager.dispose()
    with pytest.raises(DatabaseConfigurationError):
        async with manager.session():
            pass


def test_postgres_schema() -> None:
    dialect = postgresql.dialect()
    user_sql = str(CreateTable(User.__table__).compile(dialect=dialect))
    audit_sql = str(CreateTable(AuditLog.__table__).compile(dialect=dialect))
    assert "BIGSERIAL" in user_sql
    assert "UNIQUE (telegram_user_id)" in user_sql
    assert "JSONB" in audit_sql
    assert "TIMESTAMP WITH TIME ZONE" in audit_sql
    assert "ON DELETE SET NULL" in audit_sql
````

### C:/Users/USER/Documents/Agent/tests/test_user_repository.py

````python
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.repository import UserRepository


async def test_create_and_lookup(session: AsyncSession) -> None:
    repository = UserRepository(session)
    user = await repository.create(2**40, first_name="Owner")
    assert user.id is not None
    assert user.is_active
    assert user.created_at.utcoffset() == timedelta(0)
    assert user.updated_at.tzinfo is not None
    assert await repository.get_by_id(user.id) is user
    assert await repository.get_by_telegram_user_id(2**40) is user
    assert await repository.get_by_telegram_user_id(42) is None
    await session.rollback()
    assert await repository.get_by_telegram_user_id(2**40) is None


async def test_unique_telegram_id(session: AsyncSession) -> None:
    repository = UserRepository(session)
    await repository.create(42)
    with pytest.raises(IntegrityError):
        await repository.create(42)
    await session.rollback()


async def test_update_last_seen(session: AsyncSession) -> None:
    repository = UserRepository(session)
    user = await repository.create(42)
    at = datetime(2026, 9, 23, 15, tzinfo=timezone(timedelta(hours=5)))
    assert await repository.update_last_seen(user.id, at)
    await session.refresh(user)
    assert user.last_seen_at == at.astimezone(UTC)
    assert user.last_seen_at.utcoffset() == timedelta(0)
    assert not await repository.update_last_seen(999)
    with pytest.raises(ValueError, match="Timezone-aware"):
        await repository.update_last_seen(user.id, datetime(2026, 1, 1))  # noqa: DTZ001
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
    }
````

