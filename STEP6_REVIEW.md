# Stage 1 Step 6 - Implementation Review and Complete Files

Repository: C:/Users/USER/Documents/Agent

## Verification Summary

- Baseline before Step 6: 181 tests passed.
- Final full regression: 216 tests passed (181 previous plus 35 new), pytest -v.
- PASS: compileall, pip check and ruff check.
- PASS: Alembic upgrade through 0003 and downgrade 0003:0002 generated valid offline PostgreSQL SQL.
- PASS: live API-only process on http://127.0.0.1:8002; root/live/ready 200 and health 200 degraded.
- PASS: health truthfully reports database, Redis and Telegram not_configured and reminder_scheduler disabled.
- BLOCKED: live PostgreSQL migration, persistence and recovery; DATABASE_URL is unset.
- BLOCKED: live Telegram reminder delivery; token, owner and PIN are unset.
- BLOCKED: live enabled scheduler and full runtime.
- No test notification was sent.

## Architecture

PostgreSQL Reminder rows are authoritative. APScheduler has in-memory DateTrigger jobs with stable reminder:<id> identifiers and is rebuilt from PENDING rows at startup. ApplicationContext creates at most one ReminderRuntime only in an explicitly enabled Telegram/combined process. Its shutdown callback runs before Telegram, Calendar HTTP, Redis and DB cleanup.

Each occurrence is one row. Calendar offsets become separate rows. Deterministic SHA-256 keys plus a unique constraint prevent duplicate Calendar occurrences, including concurrent insertion handled with a savepoint. Standalone actions use single-use confirmation capabilities and random occurrence identities so an owner can intentionally schedule equal text/time twice through separate confirmations.

ReminderRepository owns transaction-local persistence without commits. Conditional UPDATE atomically claims only due PENDING rows as PROCESSING. Service owns validation, standalone creation, cancellation, rescheduling, upcoming listing and Calendar synchronization. Dispatcher owns claim/deliver/outcome/retry. TelegramReminderDelivery owns only owner-targeted transport.

## Reliability and Security

Delivery always uses configured TELEGRAM_OWNER_ID, never a row destination. Interactive commands require owner plus unlocked session through existing middleware. Scheduled delivery is deliberately independent of the interactive lock.

Retries are bounded and use configured delays. Only sanitized exception type is persisted. PENDING occurrences overdue within grace run immediately; older ones become MISSED. Stale PROCESSING occurrences return to PENDING unless attempts are exhausted, then become FAILED. Stable jobs, Calendar deduplication and atomic claims reduce duplicates.

The system is at-least-once. A crash after Telegram accepts a message but before DELIVERED commits can produce a duplicate after stale recovery; Telegram has no application idempotency key to guarantee exactly-once. Step 6 intentionally adds no fragile leader heartbeat. Run one scheduler process.

Calendar create synchronizes after Google succeeds. Updates preserve prior pending offsets unless reminders were explicitly changed; old PENDING rows are cancelled and recalculated while delivered history remains. Empty explicit offsets disable pending occurrences. Deletes cancel associated PENDING rows. A DB sync failure never retries the Google write and produces a reminder warning.

Audits contain reminder ID and optional scheduled timestamp only, never body or Telegram token. New actions: REMINDER_CREATED, REMINDER_CANCELLED, REMINDER_RESCHEDULED, REMINDER_DELIVERED, REMINDER_FAILED and REMINDER_RETRY.

## Database Change

Migration 0003 creates reminders with UTC-aware times, owner FK with CASCADE, status/channel, attempts and lifecycle timestamps, retry/processing state, Calendar linkage, offset, sanitized failure reason and unique deduplication key. It indexes owner, status, remind_at, status+remind_at and Calendar event+status. Previous migrations were not edited. Downgrade drops only reminders.

SQLite validates ORM/repository behavior. Offline Alembic validates PostgreSQL DDL. Neither proves a live PostgreSQL upgrade.

## Runtime Decisions and Blockers

RUN_REMINDER_SCHEDULER defaults false. Enabling requires Telegram/combined mode and PostgreSQL. API-only cannot deliver. Missing required configuration fails startup rather than falling back to ephemeral persistence. Health makes scheduler readiness required only when enabled.

Current environment has no DATABASE_URL or Telegram owner/token and scheduler is disabled. Thus live scheduler startup, DB restart recovery and owner notification remain BLOCKED. API-only remains on loopback port 8002 for inspection.

No Step 7, AI/NLP, voice, Gmail, MTProto, Finance, Notebook, Tasks, OCR, location reminder, Celery or public reminder CRUD API was implemented. Service-level reschedule exists, but no /reminder_edit command; Telegram uses cancel/recreate.

## Changed/Created Files

- C:/Users/USER/Documents/Agent/.env.example
- C:/Users/USER/Documents/Agent/pyproject.toml
- C:/Users/USER/Documents/Agent/README.md
- C:/Users/USER/Documents/Agent/app/core/config.py
- C:/Users/USER/Documents/Agent/app/core/application.py
- C:/Users/USER/Documents/Agent/app/core/runtime.py
- C:/Users/USER/Documents/Agent/app/database/models/__init__.py
- C:/Users/USER/Documents/Agent/app/database/models/reminder.py
- C:/Users/USER/Documents/Agent/app/modules/audit/actions.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/schemas.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/service.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/actions.py
- C:/Users/USER/Documents/Agent/app/bot/context.py
- C:/Users/USER/Documents/Agent/app/bot/lifecycle.py
- C:/Users/USER/Documents/Agent/app/bot/dispatcher.py
- C:/Users/USER/Documents/Agent/app/bot/constants.py
- C:/Users/USER/Documents/Agent/app/bot/handlers/reminders.py
- C:/Users/USER/Documents/Agent/app/bot/keyboards/reminders.py
- C:/Users/USER/Documents/Agent/app/api/routes/health.py
- C:/Users/USER/Documents/Agent/app/api/schemas/health.py
- C:/Users/USER/Documents/Agent/migrations/versions/0003_reminders.py
- C:/Users/USER/Documents/Agent/tests/test_audit_service.py
- C:/Users/USER/Documents/Agent/tests/test_api.py
- C:/Users/USER/Documents/Agent/tests/test_database_config.py
- C:/Users/USER/Documents/Agent/tests/test_reminder_model_repository.py
- C:/Users/USER/Documents/Agent/tests/test_reminder_service.py
- C:/Users/USER/Documents/Agent/tests/test_reminder_dispatcher.py
- C:/Users/USER/Documents/Agent/tests/test_reminder_scheduler.py
- C:/Users/USER/Documents/Agent/tests/test_reminder_delivery.py
- C:/Users/USER/Documents/Agent/tests/test_calendar_reminder_sync.py
- C:/Users/USER/Documents/Agent/tests/test_reminder_config_health.py
- C:/Users/USER/Documents/Agent/tests/bot/test_reminder_handlers.py
- C:/Users/USER/Documents/Agent/app/modules/reminders/actions.py
- C:/Users/USER/Documents/Agent/app/modules/reminders/audit.py
- C:/Users/USER/Documents/Agent/app/modules/reminders/delivery.py
- C:/Users/USER/Documents/Agent/app/modules/reminders/dispatcher.py
- C:/Users/USER/Documents/Agent/app/modules/reminders/exceptions.py
- C:/Users/USER/Documents/Agent/app/modules/reminders/repository.py
- C:/Users/USER/Documents/Agent/app/modules/reminders/runtime.py
- C:/Users/USER/Documents/Agent/app/modules/reminders/scheduler.py
- C:/Users/USER/Documents/Agent/app/modules/reminders/schemas.py
- C:/Users/USER/Documents/Agent/app/modules/reminders/service.py
- C:/Users/USER/Documents/Agent/app/modules/reminders/utils.py
- C:/Users/USER/Documents/Agent/app/modules/reminders/__init__.py
- C:/Users/USER/Documents/Agent/STEP6_REVIEW.md (this report)

## Complete Final File Contents

The files follow in full. This report is not recursively embedded.

### C:/Users/USER/Documents/Agent/.env.example

````text
APP_ENV=development
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
GOOGLE_CALENDAR_ID=primary
DATA_ENCRYPTION_KEY=
OAUTH_STATE_BACKEND=memory
CALENDAR_DEFAULT_EVENT_DURATION_MINUTES=60
RUN_REMINDER_SCHEDULER=false
REMINDER_DEFAULT_OFFSET_MINUTES=10
REMINDER_MAX_ATTEMPTS=3
REMINDER_RETRY_DELAYS_SECONDS=60,300,900
REMINDER_OVERDUE_GRACE_MINUTES=60
REMINDER_PROCESSING_TIMEOUT_MINUTES=10
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
    "google-auth>=2.35,<3",
    "google-auth-oauthlib>=1.2,<2",
    "cryptography>=43",
    "httpx>=0.27,<1",
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
    "apscheduler>=3.11,<4",
]

[project.optional-dependencies]
dev = [
    "fakeredis[lua]>=2.26,<3",
    "aiosqlite>=0.20.0,<1",
    "pytest>=8.3.2",
    "pytest-asyncio>=0.24.0",
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
Step 5 adds Google Calendar OAuth, encrypted refresh credentials and confirmed Telegram actions.

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

Run one polling process per bot token. Stop with Ctrl+C. Startup registers current
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
.\.venv\Scripts\python.exe -m uvicorn app.api.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
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
Step 4 added no admin/write HTTP API, Docker, scheduler, webhook, Calendar, Gmail or AI.
Calendar is implemented separately in Step 5 below.

## Stage 1 - Step 5: Google Calendar

### Architecture

`app/modules/calendar/` separates schemas/time utilities, async Calendar REST client,
domain service, encrypted credential repository/store, OAuth, single-use action
confirmations and runtime composition. The shared ApplicationContext owns the HTTP
client and lends CalendarRuntime to both FastAPI and Telegram. Existing DB/Redis
pools and owner/lock middleware are reused. No integration connects on import.

Official `google-auth` handles refresh; `google-auth-oauthlib` generates authorization
URLs/PKCE and exchanges codes. Their synchronous work is offloaded with bounded HTTP
timeouts. Calendar requests use the existing async HTTPX stack, avoiding an extra
synchronous discovery client and httplib2 dependency. No service account is used.

### Google Cloud Setup

1. Create/select your Google Cloud project and enable **Google Calendar API**.
2. Configure Google Auth Platform/OAuth consent branding, audience and data access.
   For a testing application add your own Google account as a test user.
3. Create an OAuth 2.0 **Web application** client, not a service account.
4. Register the exact redirect URI, for local use:
   `http://127.0.0.1:8000/oauth/google/callback`.
5. Put the client ID/secret and matching redirect URI in the ignored `.env`.
   Do not commit downloaded credential JSON. `client_secret*.json`,
   `credentials*.json` and `token*.json` are ignored defensively.

Only Calendar scopes are requested: `https://www.googleapis.com/auth/calendar.events`
for event CRUD and `https://www.googleapis.com/auth/calendar.freebusy` for availability.
No Gmail, Drive, contacts or general calendar-management scope is requested.
See [Google Calendar scopes](https://developers.google.com/workspace/calendar/api/auth)
and [Google web-server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server).

### Settings and Encryption

```text
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
GOOGLE_CALENDAR_ID=primary
DATA_ENCRYPTION_KEY=
OAUTH_STATE_BACKEND=memory
CALENDAR_DEFAULT_EVENT_DURATION_MINUTES=60
```

All credential placeholders are intentionally empty. Google settings are optional
for normal app startup. Starting OAuth requires client settings, a valid redirect,
owner ID, PostgreSQL and an encryption key. Calendar commands also require the
existing authorized, unlocked owner session.

Generate a random 256-bit key directly into `.env`, without printing it:

```powershell
.\.venv\Scripts\python.exe scripts/generate_encryption_key.py
```

The helper refuses to replace a nonempty key. Back up the key separately and protect
`.env` with Windows account/file permissions (on Linux the helper applies mode 0600).
Losing/changing it makes stored credentials unreadable. Automated key rotation is
not implemented; disconnect/reconnect using a planned migration when rotating.

The new `google_credentials` table has an owner FK, unique owner/provider pair and
AES-256-GCM ciphertext with a random nonce and owner/provider-bound associated data.
Only the refresh token is persisted. Access tokens/expiry remain in process memory;
the client automatically refreshes as needed and caches a valid access token.
Rotated refresh tokens use compare-and-swap so a delayed refresh cannot resurrect
a deleted credential. Permanent refresh failures stop repeated attempts for that
credential in the process and ask for reconnect. Restart clears that error cache.
Database backups still need operational access protection and encryption.

### Migration and Startup (PowerShell)

```powershell
Set-Location C:\Users\USER\Documents\Agent
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.run_all
```

`0002_google_calendar_credentials` is a new migration; `0001` is unchanged. When
PostgreSQL is unavailable, validate SQL only, without claiming an applied migration:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head --sql
.\.venv\Scripts\python.exe -m alembic downgrade 0002:0001 --sql
```

API-only: `.\.venv\Scripts\python.exe -m app.run_api`.
Telegram-only: `.\.venv\Scripts\python.exe -m app.bot.run`.
Linux equivalents use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`.

For first connection prefer **combined mode** with explicit `OAUTH_STATE_BACKEND=memory`.
Memory OAuth state cannot cross processes and is lost on restart. For separate API
and bot processes set **both** `OAUTH_STATE_BACKEND=redis` and
`SECURITY_STATE_BACKEND=redis`, plus the same owner, REDIS_URL and REDIS_KEY_PREFIX.
There is no automatic Redis-to-memory fallback. Redis stores state, PKCE verifier
and action previews temporarily, never Google access/refresh tokens. Secure Redis
as private infrastructure. Use one Telegram poller per token.

### Connecting and Disconnecting

Unlock in Telegram, then `/google_connect`. Open the one-time link in a browser on
the same computer as the local API. A phone's 127.0.0.1 is the phone itself, not your
PC. For a private server configure an exact HTTPS callback reachable by your browser;
public deployment/reverse-proxy setup is outside this step.

The start endpoint requires a random owner-issued ticket. It binds a new OAuth
state to an HttpOnly, SameSite=Lax browser cookie and PKCE verifier. Both start and
callback require an unlocked session. State/tickets expire after ten minutes and
are consumed once. Callback validates state and browser binding before exchanging
the code, saves encrypted credentials and returns a plain success page.
Do not forward connection links; they are short-lived bearer capabilities.
Use the same browser for the full flow. Locking/restarting can require starting over.

`/google_status` or `/calendar` reports stored connection presence, not a live Google
API connectivity claim. `/google_disconnect` requires a confirmation button. It
deletes local credentials and attempts remote revocation. If revocation fails it
explicitly asks you to remove the grant in Google account permissions; the local
refresh token is not silently retained. An already in-flight provider request may
finish during disconnect. Do not run concurrent connection/disconnection flows.

Application logs never include OAuth URLs/codes/tokens. Uvicorn access logging is
disabled centrally and by the supplied runners. Future proxy/browser diagnostic
logs must also redact OAuth query strings. Callback responses use no-store and
no-referrer headers and do not echo invalid code/state values.

### Commands

| Command | Behavior |
| --- | --- |
| /calendar, /google_status | Connection state and available commands |
| /google_connect | Owner-only one-time browser authorization link |
| /google_disconnect | Confirm disconnect and credential deletion |
| /today, /tomorrow | Local-day schedule, capped at 50 events |
| /upcoming | Next ten events, ordered by start time |
| /event_add | Title, DD.MM.YYYY, HH:MM, duration, reminders, confirmation |
| /event_update | Select next event by index, edit title/time/reminder, confirm |
| /event_delete | Select exact event by index, preview, confirm deletion |
| /free 25.09.2026 14:00 20:00 | Available intervals within this local-day range |
| /cancel | Cancel current Calendar flow and its pending confirmation |

Creation duration is minutes (1-1440); `-` selects the configured default of 60.
Reminder input is `10`, `1440,60,10`, `-` for default 10, or `none` to disable.
There may be at most five distinct positive minute values, each no greater than
40320. They become explicit Google popup overrides, not Telegram notifications.
See [Google event reminder fields](https://developers.google.com/workspace/calendar/api/v3/reference/events).

For update choose `title`, `time` or `reminder`. Time input is
`DD.MM.YYYY HH:MM duration_minutes`. Only the selected fields are patched; other
provider fields/default reminders are preserved. Date boundaries and displays use
APP_TIMEZONE (Asia/Tashkent by default). Datetimes must be aware; ambiguous/nonexistent
DST wall times are rejected. All-day events are displayed as All day. Free/busy
merges/clips overlaps and adjacent busy ranges before computing available slots.

Confirmation handles are random, short-lived and consumed before provider calls;
a repeated click cannot execute the action twice. Update/delete re-fetch the exact
event and use its ETag with If-Match, rejecting changes since preview. Never trust a
display index as a persistent event identity. Creation supplies a Google-compatible
unique event ID. A network failure can leave an uncertain outcome: inspect /upcoming
before starting a new create flow; the app does not automatically retry writes.

Audits run in a separate best-effort transaction after successful external actions.
An audit outage never retries or reports a completed provider action as failed.
Audit records contain action and event identifier, not event text or credentials.

### Verification and Limits

```powershell
.\.venv\Scripts\python.exe -m compileall app tests migrations
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check .
```

Tests use fake Google HTTP/SDK responses, fake Redis, SQLite and offline Telegram.
They do not open a browser or access your Google account. Live OAuth/API/migrations
remain BLOCKED until actual credentials and PostgreSQL are available. Any manual
live test that creates/deletes an event needs explicit owner confirmation.

Existing /health endpoints intentionally retain Step 4 infrastructure semantics;
they do not call Google or claim its connectivity. Use /google_status for credential
presence and /upcoming for an actual authorized request. Calendar requires PostgreSQL
even though the basic bot and health endpoints still permit DB-free development.

Recurring instances are expanded for listing. Recurring/all-day creation, update
and deletion are intentionally unsupported in this step. No invitations/contact
lookup, natural-language parsing, LLM, voice, Gmail, MTProto, Finance, Notebook,
task system or Docker was added. OAuth memory mode is single
process; it is not a deployment configuration. Full distributed OAuth/credential
operation fencing and a durable outbox are not implemented.

## Stage 1 - Step 6: Persistent Reminder Engine

### Architecture and Persistence

PostgreSQL `reminders` rows are the source of truth. Each standalone reminder or
Calendar offset is one occurrence with its own status, attempt count and timestamps.
APScheduler 3 uses an in-memory job list only as a wake-up index:

```text
PostgreSQL reminder -> APScheduler wake-up -> atomic DB claim
                    -> Telegram owner delivery -> delivered/retry/failed state
```

On startup the scheduler resets stale PROCESSING rows, queries PENDING rows and
reconstructs stable `reminder:<id>` jobs. Future occurrences retain their time.
Occurrences up to `REMINDER_OVERDUE_GRACE_MINUTES` late run immediately; older ones
become MISSED and remain in history. APScheduler jobs need no second persistent job
store because PostgreSQL already holds authoritative state.

The `0003_reminders` migration adds the table, owner FK, unique deduplication key,
status/time and Calendar-event indexes. Times are aware and stored in UTC. User input
and output use APP_TIMEZONE, normally Asia/Tashkent. Apply it after configuring DB:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Offline validation does not modify a database:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head --sql
.\.venv\Scripts\python.exe -m alembic downgrade 0003:0002 --sql
```

### Configuration and Ownership

```text
RUN_REMINDER_SCHEDULER=false
REMINDER_DEFAULT_OFFSET_MINUTES=10
REMINDER_MAX_ATTEMPTS=3
REMINDER_RETRY_DELAYS_SECONDS=60,300,900
REMINDER_OVERDUE_GRACE_MINUTES=60
REMINDER_PROCESSING_TIMEOUT_MINUTES=10
```

The scheduler is deliberately disabled by default. Enable it only in one
Telegram-capable process with valid TELEGRAM_OWNER_ID, TELEGRAM_BOT_TOKEN, PIN and
DATABASE_URL. Recommended Step 6 command:

```powershell
# Set RUN_REMINDER_SCHEDULER=true in the ignored .env first
.\.venv\Scripts\python.exe -m app.run_all
```

Do not also start `app.bot.run`, another combined runner, Uvicorn workers containing
the scheduler, or a second scheduler host. Step 6 has DB-safe atomic claims, so two
wake-ups cannot normally send the same PENDING row, but it has no distributed leader
lease. API-only mode never starts delivery. Health reports `reminder_scheduler` as
disabled/running/stopped/error and treats it as required only when explicitly enabled.

Lifecycle ownership is one instance: DB and Redis initialize, Telegram prepares,
scheduler recovers/starts, then normal service begins. Shutdown stops/removes scheduler
jobs before closing Telegram HTTP, Calendar HTTP, Redis and DB resources. If scheduler
is enabled without PostgreSQL or Telegram mode, startup fails clearly; there is no
ephemeral reminder fallback.

### Commands and Calendar Synchronization

`/remind` asks for text, `DD.MM.YYYY`, `HH:MM`, shows a preview and writes/schedules
only after confirmation. `/reminders` shows the next ten PENDING occurrences.
`/reminder_cancel` lists pending rows, requires confirmation and marks the selected
row CANCELLED; it never deletes history. `/cancel` aborts the active reminder form.

All configuration/list/cancel commands pass the existing owner-only and unlocked
session middleware. Scheduled delivery intentionally ignores the interactive session
lock: locking commands must not suppress already-authorized reminders. Delivery always
targets configured TELEGRAM_OWNER_ID, never a destination copied from a reminder row.

Calendar creation persists one Telegram reminder per Google reminder offset after the
Google event succeeds. The default is 10 minutes; `[1440, 60, 10]` produces three
independent rows. Deduplication hashes owner, Google event ID, event start, offset and
channel, backed by a unique constraint. Google popup reminders and these Telegram
occurrences are independent.

Calendar updates preserve existing offsets when only title/time changes, cancel only
old PENDING occurrences and create recalculated rows. Delivered history is never
resurrected. Explicitly clearing reminders cancels pending occurrences without creating
new ones. Calendar deletion marks associated PENDING rows CANCELLED. If DB reminder
sync fails after Google succeeds, the Calendar action is not retried and Telegram
reports success with a reminder warning, avoiding duplicate Google events.

### Delivery Reliability

At execution, an atomic conditional update claims `PENDING -> PROCESSING`; competing
workers get no row. Success becomes DELIVERED. Safe failure storage records only the
exception type, never Telegram token, SDK response or reminder body. Attempts retry
after the configured delays and become FAILED at the maximum. PROCESSING rows older
than the timeout return to PENDING unless their attempts are exhausted, in which case
they become FAILED.

Delivery is at-least-once, not exactly-once. A crash after Telegram accepts a message
but before PostgreSQL marks DELIVERED can cause a duplicate after stale recovery.
Telegram Bot API provides no application idempotency key that can close this gap.
Stable jobs, deduplication, atomic claims and stale timeouts reduce duplicate risk but
cannot eliminate that specific crash window. There is no Celery or leader heartbeat.

Reminder audits include ID and scheduled timestamp only, not title/message/token:
REMINDER_CREATED, REMINDER_CANCELLED, REMINDER_RESCHEDULED, REMINDER_DELIVERED,
REMINDER_FAILED and REMINDER_RETRY. Audit failure never repeats an external send.

### Verification and Limits

```powershell
.\.venv\Scripts\python.exe -m compileall app tests migrations
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check .
```

Offline tests use SQLite, fake scheduler metadata and an offline Telegram session;
they never wait real minutes or send notifications. SQLite validates behavior, not
PostgreSQL locking/migration execution. Live DB migration, startup recovery and owner
notification remain separate checks when credentials/infrastructure exist. Do not
send an uncontrolled manual reminder.

Step 6 does not add AI/NLP, voice, Gmail, MTProto, Finance, Notebook, Tasks, OCR,
location reminders, Celery or public reminder CRUD endpoints. Standalone reminder
editing is not implemented; cancel and recreate. Reminder content is plaintext in
PostgreSQL in this stage, so database access/backups must be protected. A later
encrypted-data migration can cover reminder bodies.

Next: **Stage 1 - Step 7**, Gmail integration, new-email monitoring, email summary
foundation and Telegram email notifications. Not implemented yet.
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
    google_client_id: SecretStr | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: SecretStr | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str | None = Field(default=None, alias="GOOGLE_REDIRECT_URI")
    google_calendar_id: str = Field(default="primary", min_length=1, alias="GOOGLE_CALENDAR_ID")
    data_encryption_key: SecretStr | None = Field(default=None, alias="DATA_ENCRYPTION_KEY")
    oauth_state_backend: Literal["memory", "redis"] = Field(
        default="memory", alias="OAUTH_STATE_BACKEND"
    )
    calendar_default_event_duration_minutes: int = Field(
        default=60, ge=1, le=1440, alias="CALENDAR_DEFAULT_EVENT_DURATION_MINUTES"
    )
    run_reminder_scheduler: bool = Field(default=False, alias="RUN_REMINDER_SCHEDULER")
    reminder_default_offset_minutes: int = Field(
        default=10, ge=1, le=40320, alias="REMINDER_DEFAULT_OFFSET_MINUTES"
    )
    reminder_max_attempts: int = Field(default=3, ge=1, le=10, alias="REMINDER_MAX_ATTEMPTS")
    reminder_retry_delays_seconds: str = Field(
        default="60,300,900", alias="REMINDER_RETRY_DELAYS_SECONDS"
    )
    reminder_overdue_grace_minutes: int = Field(
        default=60, ge=0, le=10080, alias="REMINDER_OVERDUE_GRACE_MINUTES"
    )
    reminder_processing_timeout_minutes: int = Field(
        default=10, ge=1, le=1440, alias="REMINDER_PROCESSING_TIMEOUT_MINUTES"
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

    @field_validator("reminder_retry_delays_seconds")
    @classmethod
    def validate_retry_delays(cls, value: str) -> str:
        try:
            delays = tuple(int(item.strip()) for item in value.split(","))
        except ValueError:
            raise ValueError(
                "REMINDER_RETRY_DELAYS_SECONDS must be comma-separated integers"
            ) from None
        if not delays or any(delay < 1 or delay > 86400 for delay in delays):
            raise ValueError("Reminder retry delays must be between 1 and 86400 seconds")
        return ",".join(str(delay) for delay in delays)

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)

    @property
    def is_owner_configured(self) -> bool:
        return self.telegram_owner_id is not None and bool(self.telegram_bot_token)

    @property
    def reminder_retry_delays(self) -> tuple[int, ...]:
        return tuple(int(item) for item in self.reminder_retry_delays_seconds.split(","))


def get_settings() -> Settings:
    """Load explicitly at startup so imports have no configuration side effects."""
    return Settings()
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
from app.modules.calendar.runtime import CalendarRuntime
from app.modules.reminders.exceptions import ReminderConfigurationError
from app.modules.reminders.runtime import ReminderRuntime
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
            reminder_scheduler_required=telegram and settings.run_reminder_scheduler,
        )
        self.database: DatabaseManager | None = None
        self.redis: RedisManager | None = None
        self.lock = LockService()
        self.persistence = BotPersistence(None)
        self.telegram: TelegramRuntime | None = None
        self.calendar: CalendarRuntime | None = None
        self.reminders: ReminderRuntime | None = None
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
            self.runtime.startup_complete = True
        except BaseException:
            await self.close()
            raise

    async def close(self) -> None:
        self.runtime.startup_complete = False
        if self.runtime.reminder_scheduler == "running":
            self.runtime.reminder_scheduler = "stopped"
        resources, self._resources = self._resources, None
        if resources is not None:
            await resources.aclose()
````

### C:/Users/USER/Documents/Agent/app/core/runtime.py

````python
from dataclasses import dataclass
from typing import Literal

type TelegramState = Literal["not_configured", "configured", "running", "stopped", "error"]
type SchedulerState = Literal["disabled", "running", "stopped", "error"]


@dataclass
class RuntimeState:
    startup_complete: bool = False
    telegram: TelegramState = "not_configured"
    telegram_required: bool = False
    reminder_scheduler: SchedulerState = "disabled"
    reminder_scheduler_required: bool = False
````

### C:/Users/USER/Documents/Agent/app/database/models/__init__.py

````python
"""Import all mapped models so migrations discover complete metadata."""

from app.database.models.audit_log import AuditLog
from app.database.models.google_credential import GoogleCredential
from app.database.models.reminder import Reminder, ReminderChannel, ReminderStatus
from app.database.models.user import User

__all__ = [
    "AuditLog",
    "GoogleCredential",
    "Reminder",
    "ReminderChannel",
    "ReminderStatus",
    "User",
]
````

### C:/Users/USER/Documents/Agent/app/database/models/reminder.py

````python
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UTCDateTime


class ReminderStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    MISSED = "MISSED"
    CANCELLED = "CANCELLED"


class ReminderChannel(StrEnum):
    TELEGRAM = "TELEGRAM"


class Reminder(TimestampMixin, Base):
    __tablename__ = "reminders"
    __table_args__ = (
        Index("ix_reminders_status_remind_at", "status", "remind_at"),
        Index("ix_reminders_calendar_event", "external_calendar_event_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    external_calendar_event_id: Mapped[str | None] = mapped_column(String(1024))
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str | None] = mapped_column(Text)
    remind_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    retry_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    event_start_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    offset_minutes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus, native_enum=False, length=16),
        default=ReminderStatus.PENDING,
        server_default=ReminderStatus.PENDING.value,
        index=True,
    )
    channel: Mapped[ReminderChannel] = mapped_column(
        Enum(ReminderChannel, native_enum=False, length=16),
        default=ReminderChannel.TELEGRAM,
        server_default=ReminderChannel.TELEGRAM.value,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer)
    processing_started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    delivered_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    failed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    failure_reason: Mapped[str | None] = mapped_column(String(120))
    deduplication_key: Mapped[str] = mapped_column(String(64), unique=True)
````

### C:/Users/USER/Documents/Agent/app/modules/audit/actions.py

````python
from enum import StrEnum


class AuditAction(StrEnum):
    GOOGLE_CALENDAR_CONNECTED = "GOOGLE_CALENDAR_CONNECTED"
    GOOGLE_CALENDAR_DISCONNECTED = "GOOGLE_CALENDAR_DISCONNECTED"
    CALENDAR_EVENT_CREATED = "CALENDAR_EVENT_CREATED"
    CALENDAR_EVENT_UPDATED = "CALENDAR_EVENT_UPDATED"
    CALENDAR_EVENT_DELETED = "CALENDAR_EVENT_DELETED"
    REMINDER_CREATED = "REMINDER_CREATED"
    REMINDER_CANCELLED = "REMINDER_CANCELLED"
    REMINDER_RESCHEDULED = "REMINDER_RESCHEDULED"
    REMINDER_DELIVERED = "REMINDER_DELIVERED"
    REMINDER_FAILED = "REMINDER_FAILED"
    REMINDER_RETRY = "REMINDER_RETRY"
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

### C:/Users/USER/Documents/Agent/app/modules/calendar/schemas.py

````python
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

Reminder = Annotated[int, Field(strict=True, ge=1, le=40320)]


class CalendarEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    title: str = Field(min_length=1, max_length=200)
    start: AwareDatetime
    end: AwareDatetime
    description: str = Field(default="", max_length=2000)
    location: str = Field(default="", max_length=300)
    reminders: list[Reminder] = Field(default_factory=lambda: [10], max_length=5)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Title is required")
        return value.strip()

    @field_validator("reminders")
    @classmethod
    def unique_reminders(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate reminders")
        return value

    @model_validator(mode="after")
    def ordered(self) -> "CalendarEventCreate":
        if self.end <= self.start:
            raise ValueError("End must be after start")
        return self


class CalendarEventUpdate(CalendarEventCreate):
    """Complete editable preview; client PATCH preserves all other Google fields."""

    fields: set[Literal["title", "start", "end", "reminders"]] = Field(
        default_factory=lambda: {"title", "start", "end", "reminders"}, min_length=1
    )


class CalendarEventView(BaseModel):
    id: str
    etag: str
    title: str
    start: datetime | date
    end: datetime | date
    all_day: bool = False
    recurring: bool = False
    description: str = ""
    location: str = ""
    reminders: list[int] = Field(default_factory=list)
    reminder_warning: bool = False

    @model_validator(mode="after")
    def valid_times(self) -> "CalendarEventView":
        for value in (self.start, self.end):
            if isinstance(value, datetime):
                if self.all_day or value.tzinfo is None or value.utcoffset() is None:
                    raise ValueError("Timed events must be timezone-aware")
            elif not self.all_day:
                raise ValueError("Timed event requires a datetime")
        if self.end <= self.start:
            raise ValueError("Invalid event time range")
        return self


class TimeInterval(BaseModel):
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def ordered(self) -> "TimeInterval":
        if self.end <= self.start:
            raise ValueError("End must be after start")
        return self


class FreeBusyResult(BaseModel):
    busy: list[TimeInterval]
    free: list[TimeInterval]
````

### C:/Users/USER/Documents/Agent/app/modules/calendar/service.py

````python
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.modules.audit.actions import AuditAction
from app.modules.calendar.audit import CalendarAudit
from app.modules.calendar.client import GoogleCalendarClient
from app.modules.calendar.exceptions import CalendarConflictError, CalendarError
from app.modules.calendar.schemas import (
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarEventView,
    FreeBusyResult,
    TimeInterval,
)
from app.modules.calendar.utils import day_range, event_view, free_intervals


class ReminderSync(Protocol):
    async def sync_calendar(
        self, event_id: str, title: str, start: datetime, offsets: list[int] | None
    ) -> bool: ...
    async def cancel_calendar(self, event_id: str) -> bool: ...


class CalendarService:
    """Validated domain operations; Telegram confirmation is a separate action boundary."""

    def __init__(
        self,
        client: GoogleCalendarClient,
        audit: CalendarAudit,
        timezone: ZoneInfo,
        reminder_sync: ReminderSync | None = None,
    ) -> None:
        self.client, self.audit, self.timezone = client, audit, timezone
        self.reminder_sync = reminder_sync

    def payload(self, event: CalendarEventCreate) -> dict[str, Any]:
        return {
            "summary": event.title,
            "description": event.description,
            "location": event.location,
            "start": {
                "dateTime": event.start.astimezone(self.timezone).isoformat(),
                "timeZone": str(self.timezone),
            },
            "end": {
                "dateTime": event.end.astimezone(self.timezone).isoformat(),
                "timeZone": str(self.timezone),
            },
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": value} for value in event.reminders],
            },
        }

    def sorted_views(self, raw: list[dict[str, Any]]) -> list[CalendarEventView]:
        def key(event: CalendarEventView) -> datetime:
            return (
                datetime.combine(event.start, time.min, self.timezone)
                if event.all_day
                else event.start.astimezone(self.timezone)
            )

        return sorted((event_view(item) for item in raw), key=key)

    async def events_on(self, day: date) -> list[CalendarEventView]:
        window = day_range(day, self.timezone)
        return self.sorted_views(
            await self.client.list_events(window.start.isoformat(), window.end.isoformat(), 50)
        )

    async def get_today_events(self) -> list[CalendarEventView]:
        return await self.events_on(datetime.now(self.timezone).date())

    async def get_tomorrow_events(self) -> list[CalendarEventView]:
        return await self.events_on(datetime.now(self.timezone).date() + timedelta(days=1))

    async def list_upcoming_events(self) -> list[CalendarEventView]:
        return self.sorted_views(
            await self.client.list_events(datetime.now(UTC).isoformat(), None, 10)
        )

    async def get_event(self, event_id: str) -> CalendarEventView:
        return event_view(await self.client.get_event(event_id))

    async def create_event(
        self, event: CalendarEventCreate, action_id: str | None = None
    ) -> CalendarEventView:
        payload = self.payload(event)
        # Google accepts base32hex IDs: UUID hex is a valid subset and fences duplicate inserts.
        payload["id"] = action_id or uuid4().hex
        result = event_view(await self.client.create_event(payload))
        await self.audit.record(AuditAction.CALENDAR_EVENT_CREATED, result.id)
        if self.reminder_sync and isinstance(result.start, datetime):
            synced = await self.reminder_sync.sync_calendar(
                result.id, result.title, result.start, event.reminders
            )
            result.reminder_warning = not synced
        return result

    async def mutable_event(self, event_id: str, etag: str) -> CalendarEventView:
        event = await self.get_event(event_id)
        if event.recurring or event.all_day:
            raise CalendarError("Recurring/all-day changes are not supported in Step 5.")
        if not etag or event.etag != etag:
            raise CalendarConflictError("Event changed. Select it again before confirming.")
        return event

    async def update_event(
        self, event_id: str, event: CalendarEventUpdate, etag: str
    ) -> CalendarEventView:
        await self.mutable_event(event_id, etag)
        names = {"title": "summary", "start": "start", "end": "end", "reminders": "reminders"}
        complete = self.payload(event)
        payload = {names[field]: complete[names[field]] for field in event.fields}
        result = event_view(await self.client.update_event(event_id, payload, etag))
        await self.audit.record(AuditAction.CALENDAR_EVENT_UPDATED, result.id)
        if self.reminder_sync and isinstance(result.start, datetime):
            offsets = event.reminders if "reminders" in event.fields else None
            result.reminder_warning = not await self.reminder_sync.sync_calendar(
                result.id, result.title, result.start, offsets
            )
        return result

    async def delete_event(self, event_id: str, etag: str) -> bool:
        await self.mutable_event(event_id, etag)
        await self.client.delete_event(event_id, etag)
        await self.audit.record(AuditAction.CALENDAR_EVENT_DELETED, event_id)
        return not self.reminder_sync or await self.reminder_sync.cancel_calendar(event_id)

    async def get_free_busy(self, window: TimeInterval) -> FreeBusyResult:
        raw = await self.client.free_busy(
            window.start.isoformat(), window.end.isoformat(), str(self.timezone)
        )
        calendar = raw.get("calendars", {}).get(self.client.calendar_id)
        if calendar is None or calendar.get("errors"):
            raise CalendarError("Calendar availability could not be checked.")
        busy = [TimeInterval.model_validate(item) for item in calendar.get("busy", [])]
        return FreeBusyResult(busy=busy, free=free_intervals(window, busy))
````

### C:/Users/USER/Documents/Agent/app/modules/calendar/actions.py

````python
"""Single-use confirmation boundary; callbacks contain only random action handles."""

from typing import Any
from uuid import uuid4

from app.modules.calendar.exceptions import CalendarError
from app.modules.calendar.oauth import GoogleOAuthService
from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventUpdate
from app.modules.calendar.service import CalendarService
from app.modules.calendar.state import TemporaryStore


class CalendarActions:
    def __init__(
        self,
        service: CalendarService,
        oauth: GoogleOAuthService,
        states: TemporaryStore,
        owner: int | None,
    ) -> None:
        self.service, self.oauth, self.states, self.owner = service, oauth, states, owner

    async def prepare(self, kind: str, data: dict[str, Any]) -> str:
        return await self.states.issue("action", {"kind": kind, "data": data, "owner": self.owner})

    async def confirm(self, token: str) -> str:
        await self.oauth.unlocked()
        action = await self.states.consume("action", token)
        if not action or action["owner"] != self.owner:
            raise CalendarError("Confirmation expired or already processed. Start again.")
        kind, data = action["kind"], action["data"]
        # Consume BEFORE side effects. Ambiguous network failures require inspecting /upcoming.
        if kind == "create":
            event = await self.service.create_event(
                CalendarEventCreate.model_validate(data), uuid4().hex
            )
            return (
                "Event yaratildi. Reminder setup failed; /reminders ni tekshiring."
                if getattr(event, "reminder_warning", False) is True
                else "Event yaratildi."
            )
        if kind == "update":
            event = await self.service.update_event(
                data["id"], CalendarEventUpdate.model_validate(data["event"]), data["etag"]
            )
            return (
                "Event yangilandi. Reminder sync failed; /reminders ni tekshiring."
                if getattr(event, "reminder_warning", False) is True
                else "Event yangilandi."
            )
        if kind == "delete":
            synced = await self.service.delete_event(data["id"], data["etag"])
            return (
                "Event o'chirildi."
                if synced
                else "Event o'chirildi. Reminder cancellation failed; /reminders ni tekshiring."
            )
        if kind == "disconnect":
            revoked = await self.oauth.disconnect()
            return (
                "Google Calendar uzildi."
                if revoked
                else "Stored credentials deleted. Remote revocation failed; remove access in your Google account."
            )
        raise CalendarError("Invalid confirmation.")

    async def cancel(self, token: str) -> None:
        await self.states.consume("action", token)
````

### C:/Users/USER/Documents/Agent/app/bot/context.py

````python
from dataclasses import dataclass

from app.bot.persistence import BotPersistence
from app.modules.calendar.runtime import CalendarRuntime
from app.modules.reminders.runtime import ReminderRuntime
from app.modules.security.service import SecurityService


@dataclass(repr=False)
class BotContext:
    owner_id: int
    timezone: str
    security: SecurityService
    persistence: BotPersistence
    calendar: CalendarRuntime | None = None
    reminders: ReminderRuntime | None = None
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
from app.modules.calendar.runtime import CalendarRuntime
from app.modules.reminders.runtime import ReminderRuntime
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
        self.calendar: CalendarRuntime | None = None
        self.reminders: ReminderRuntime | None = None
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
        self.context.calendar = self.calendar
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

### C:/Users/USER/Documents/Agent/app/bot/dispatcher.py

````python
from aiogram import Dispatcher
from aiogram.fsm.storage.base import BaseEventIsolation, BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation

from app.bot.context import BotContext
from app.bot.errors import SafeErrorMiddleware
from app.bot.handlers import calendar, common, menu, reminders, security
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
        security.create_router(),
        common.create_router(),
        reminders.create_router(),
        calendar.create_router(),
        menu.create_router(),
    )
    return dispatcher
````

### C:/Users/USER/Documents/Agent/app/bot/constants.py

````python
"""Public commands and labels; never derive audit fields from arbitrary message text."""

COMMANDS = {
    "calendar": "Calendar",
    "today": "Bugungi rejalar",
    "tomorrow": "Ertangi rejalar",
    "upcoming": "Keyingi rejalar",
    "event_add": "Event yaratish",
    "event_update": "Event yangilash",
    "event_delete": "Event o'chirish",
    "free": "Bo'sh vaqt",
    "google_connect": "Google ulash",
    "google_status": "Google holati",
    "google_disconnect": "Google uzish",
    "cancel": "Bekor qilish",
    "remind": "Reminder yaratish",
    "reminders": "Keyingi reminderlar",
    "reminder_cancel": "Reminderni bekor qilish",
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

### C:/Users/USER/Documents/Agent/app/bot/handlers/reminders.py

````python
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.context import BotContext
from app.bot.keyboards.reminders import confirmation
from app.modules.calendar.utils import parse_local
from app.modules.reminders.exceptions import ReminderError
from app.modules.reminders.runtime import ReminderRuntime


class ReminderFlow(StatesGroup):
    text = State()
    date = State()
    time = State()
    select = State()
    confirm = State()


def runtime(context: BotContext) -> ReminderRuntime:
    if context.reminders is None:
        raise ReminderError(
            "Reminder scheduler disabled. PostgreSQL va RUN_REMINDER_SCHEDULER ni sozlang."
        )
    return context.reminders


async def send(message: Message, text: str, **kwargs: Any) -> None:
    await message.answer(text, parse_mode=None, **kwargs)


async def reset(state: FSMContext, reminders: ReminderRuntime) -> None:
    data = await state.get_data()
    if data.get("action"):
        await reminders.actions.cancel_action(data["action"])
    await state.clear()


async def start_create(message: Message, state: FSMContext, app_context: BotContext) -> None:
    reminders = runtime(app_context)
    await reset(state, reminders)
    await state.set_state(ReminderFlow.text)
    await send(message, "Nimani eslatay? Bekor qilish: /cancel")


async def input_step(message: Message, state: FSMContext, app_context: BotContext) -> None:
    reminders = runtime(app_context)
    current, data = await state.get_state(), await state.get_data()
    text = (message.text or "").strip()
    try:
        if current == ReminderFlow.text.state:
            if not 1 <= len(text) <= 200:
                raise ValueError
            await state.update_data(title=text)
            await state.set_state(ReminderFlow.date)
            await send(message, "Sanani kiriting: DD.MM.YYYY")
        elif current == ReminderFlow.date.state:
            parse_local(text, "00:00", reminders.timezone)
            await state.update_data(day=text)
            await state.set_state(ReminderFlow.time)
            await send(message, "Vaqt: HH:MM")
        elif current == ReminderFlow.time.state:
            remind_at = parse_local(data["day"], text, reminders.timezone)
            payload = {"title": data["title"], "remind_at": remind_at.isoformat()}
            token = await reminders.actions.prepare("create", payload)
            await state.set_data({"action": token})
            await state.set_state(ReminderFlow.confirm)
            await send(
                message,
                f"⏰ Reminder\n\n{data['title']}\n{remind_at:%d.%m.%Y %H:%M}\n\nSaqlansinmi?",
                reply_markup=confirmation(token),
            )
        elif current == ReminderFlow.select.state:
            rows = data["reminders"]
            index = int(text) - 1
            if index < 0 or index >= len(rows):
                raise ValueError
            token = await reminders.actions.prepare("cancel", {"id": rows[index]["id"]})
            await state.set_data({"action": token})
            await state.set_state(ReminderFlow.confirm)
            await send(
                message,
                f"{rows[index]['title']} bekor qilinsinmi?",
                reply_markup=confirmation(token),
            )
    except ValueError:
        await send(message, "Format yoki qiymat noto'g'ri. Qayta kiriting yoki /cancel.")


async def list_reminders(message: Message, app_context: BotContext) -> None:
    reminders = runtime(app_context)
    rows = await reminders.service.list_upcoming(10)
    if not rows:
        await send(message, "Pending eslatmalar yo'q.")
        return
    timezone = reminders.timezone
    await send(
        message,
        "⏰ Keyingi eslatmalar:\n\n"
        + "\n".join(
            f"{index}. {row.remind_at.astimezone(timezone):%d.%m.%Y %H:%M} — {row.title}"
            for index, row in enumerate(rows, 1)
        ),
    )


async def start_cancel(message: Message, state: FSMContext, app_context: BotContext) -> None:
    reminders = runtime(app_context)
    await reset(state, reminders)
    rows = await reminders.service.list_upcoming(10)
    if not rows:
        await send(message, "Pending eslatmalar yo'q.")
        return
    timezone = reminders.timezone
    serial = [{"id": row.id, "title": row.title} for row in rows]
    await state.set_data({"reminders": serial})
    await state.set_state(ReminderFlow.select)
    await send(
        message,
        "Bekor qilinadigan reminder raqami:\n"
        + "\n".join(
            f"{index}. {row.remind_at.astimezone(timezone):%d.%m.%Y %H:%M} — {row.title}"
            for index, row in enumerate(rows, 1)
        ),
    )


async def cancel_flow(message: Message, state: FSMContext, app_context: BotContext) -> None:
    await reset(state, runtime(app_context))
    await send(message, "Bekor qilindi.")


async def confirmed(callback: CallbackQuery, state: FSMContext, app_context: BotContext) -> None:
    reminders = runtime(app_context)
    _, decision, token = (callback.data or "").split(":", 2)
    data = await state.get_data()
    if await state.get_state() != ReminderFlow.confirm.state or data.get("action") != token:
        await callback.answer("Tasdiq eskirgan.")
        return
    await state.clear()
    await callback.answer()
    text = await reminders.actions.confirm(token) if decision == "yes" else "Bekor qilindi."
    if decision != "yes":
        await reminders.actions.cancel_action(token)
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramAPIError:
            pass
        await send(callback.message, text)


class ReminderErrorMiddleware:
    async def __call__(self, handler: Any, event: Any, data: dict[str, Any]) -> Any:
        try:
            return await handler(event, data)
        except ReminderError as error:
            if isinstance(event, CallbackQuery):
                await event.answer(str(error)[:180], show_alert=True)
            else:
                await send(event, str(error))
            return None


def create_router() -> Router:
    router = Router(name="reminders")
    router.message.middleware(ReminderErrorMiddleware())
    router.callback_query.middleware(ReminderErrorMiddleware())
    router.message.register(start_create, Command("remind"))
    router.message.register(list_reminders, Command("reminders"))
    router.message.register(start_cancel, Command("reminder_cancel"))
    router.message.register(cancel_flow, Command("cancel"), StateFilter(ReminderFlow))
    router.message.register(
        input_step,
        F.text & ~F.text.startswith("/"),
        StateFilter(ReminderFlow.text, ReminderFlow.date, ReminderFlow.time, ReminderFlow.select),
    )
    router.callback_query.register(confirmed, F.data.regexp(r"^rem:(yes|no):[A-Za-z0-9_-]{32}$"))
    return router
````

### C:/Users/USER/Documents/Agent/app/bot/keyboards/reminders.py

````python
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirmation(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Saqlash", callback_data=f"rem:yes:{token}"),
                InlineKeyboardButton(text="Bekor qilish", callback_data=f"rem:no:{token}"),
            ]
        ]
    )
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
        reminder_scheduler=context.runtime.reminder_scheduler,
    )
    required_failed = (
        not context.runtime.startup_complete
        or (context.settings.security_state_backend == "redis" and cache != "ok")
        or (context.runtime.telegram_required and context.runtime.telegram != "running")
        or (
            context.runtime.reminder_scheduler_required
            and context.runtime.reminder_scheduler != "running"
        )
    )
    status = (
        "error"
        if required_failed
        else (
            "ok"
            if db == cache == "ok"
            and services.telegram in {"configured", "running"}
            and services.reminder_scheduler in {"disabled", "running"}
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

### C:/Users/USER/Documents/Agent/app/api/schemas/health.py

````python
from typing import Literal

from pydantic import BaseModel

type ServiceStatus = Literal[
    "ok", "configured", "not_configured", "unavailable", "error", "running", "stopped", "disabled"
]


class Services(BaseModel):
    application: ServiceStatus
    database: ServiceStatus
    redis: ServiceStatus
    telegram: ServiceStatus
    reminder_scheduler: ServiceStatus


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"]
    services: Services


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]


class LivenessResponse(BaseModel):
    status: Literal["alive"] = "alive"
````

### C:/Users/USER/Documents/Agent/migrations/versions/0003_reminders.py

````python
"""Persistent Telegram reminder occurrences."""

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str = "0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    status = sa.Enum(
        "PENDING",
        "PROCESSING",
        "DELIVERED",
        "FAILED",
        "MISSED",
        "CANCELLED",
        name="reminderstatus",
        native_enum=False,
        length=16,
    )
    channel = sa.Enum("TELEGRAM", name="reminderchannel", native_enum=False, length=16)
    op.create_table(
        "reminders",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("external_calendar_event_id", sa.String(1024), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("offset_minutes", sa.Integer(), nullable=True),
        sa.Column("status", status, server_default="PENDING", nullable=False),
        sa.Column("channel", channel, server_default="TELEGRAM", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(120), nullable=True),
        sa.Column("deduplication_key", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("deduplication_key", name="uq_reminders_deduplication_key"),
    )
    op.create_index("ix_reminders_user_id", "reminders", ["user_id"])
    op.create_index("ix_reminders_remind_at", "reminders", ["remind_at"])
    op.create_index("ix_reminders_status", "reminders", ["status"])
    op.create_index("ix_reminders_status_remind_at", "reminders", ["status", "remind_at"])
    op.create_index(
        "ix_reminders_calendar_event", "reminders", ["external_calendar_event_id", "status"]
    )


def downgrade() -> None:
    op.drop_table("reminders")
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
        "GOOGLE_CALENDAR_CONNECTED",
        "GOOGLE_CALENDAR_DISCONNECTED",
        "CALENDAR_EVENT_CREATED",
        "CALENDAR_EVENT_UPDATED",
        "CALENDAR_EVENT_DELETED",
        "REMINDER_CREATED",
        "REMINDER_CANCELLED",
        "REMINDER_RESCHEDULED",
        "REMINDER_DELIVERED",
        "REMINDER_FAILED",
        "REMINDER_RETRY",
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
                    "reminder_scheduler": "disabled",
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
from app.database.models import AuditLog, Reminder, User
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
    reminder_sql = str(CreateTable(Reminder.__table__).compile(dialect=dialect))
    assert "BIGSERIAL" in user_sql
    assert "UNIQUE (telegram_user_id)" in user_sql
    assert "JSONB" in audit_sql
    assert "TIMESTAMP WITH TIME ZONE" in audit_sql
    assert "ON DELETE SET NULL" in audit_sql
    assert "deduplication_key" in reminder_sql
    assert "UNIQUE (deduplication_key)" in reminder_sql
    assert "TIMESTAMP WITH TIME ZONE" in reminder_sql
    assert "ON DELETE CASCADE" in reminder_sql
````

### C:/Users/USER/Documents/Agent/tests/test_reminder_model_repository.py

````python
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Reminder, ReminderStatus
from app.modules.reminders.repository import ReminderRepository
from app.modules.users.repository import UserRepository

NOW = datetime(2026, 9, 25, 10, tzinfo=UTC)


def row(user_id: int, key: str = "key", **values) -> Reminder:
    defaults = {
        "user_id": user_id,
        "title": "Test",
        "remind_at": NOW + timedelta(hours=1),
        "max_attempts": 3,
        "deduplication_key": key,
    }
    return Reminder(**{**defaults, **values})


async def test_model_creation_utc_and_defaults(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    reminder = await ReminderRepository(session).create(row(user.id))
    await session.commit()
    assert reminder.status == ReminderStatus.PENDING
    assert reminder.remind_at == NOW + timedelta(hours=1)
    assert reminder.attempt_count == 0


async def test_model_rejects_naive_datetime(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    with pytest.raises((StatementError, ValueError)):
        await ReminderRepository(session).create(
            Reminder(
                user_id=user.id,
                title="Test",
                remind_at=datetime(2026, 9, 25, 11),  # noqa: DTZ001
                max_attempts=3,
                deduplication_key="naive",
            )
        )


async def test_deduplication_unique(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    await ReminderRepository(session).create(row(user.id))
    with pytest.raises(IntegrityError):
        await ReminderRepository(session).create(row(user.id))


async def test_claim_is_atomic_and_cancel_preserves_row(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    reminder = await ReminderRepository(session).create(
        row(user.id, remind_at=NOW - timedelta(minutes=1))
    )
    first = await ReminderRepository(session).claim(reminder.id, NOW)
    second = await ReminderRepository(session).claim(reminder.id, NOW)
    assert first is not None and first.attempt_count == 1
    assert second is None
    await session.rollback()
    user = await UserRepository(session).create(42)
    reminder = await ReminderRepository(session).create(row(user.id, "cancel"))
    assert await ReminderRepository(session).cancel(reminder.id, user.id, NOW)
    stored = await session.scalar(select(Reminder).where(Reminder.id == reminder.id))
    assert stored is not None and stored.status == ReminderStatus.CANCELLED
    assert stored.cancelled_at == NOW


async def test_stale_processing_recovery(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    reminder = await ReminderRepository(session).create(
        row(
            user.id,
            status=ReminderStatus.PROCESSING,
            processing_started_at=NOW - timedelta(minutes=20),
        )
    )
    ids, failed = await ReminderRepository(session).recover_stale(NOW - timedelta(minutes=10), NOW)
    assert ids == [reminder.id]
    assert failed == []
    await session.refresh(reminder)
    assert reminder.status == ReminderStatus.PENDING and reminder.retry_at == NOW
````

### C:/Users/USER/Documents/Agent/tests/test_reminder_service.py

````python
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.database.models import Reminder, ReminderStatus
from app.database.session import DatabaseManager
from app.modules.reminders.exceptions import ReminderNotFoundError, ReminderValidationError
from app.modules.reminders.schemas import CalendarReminderCreate, ReminderCreate
from app.modules.reminders.service import ReminderService

NOW = datetime(2026, 9, 25, 10, tzinfo=UTC)


def manager(engine) -> DatabaseManager:
    database = DatabaseManager(Settings(_env_file=None))
    database._sessions = async_sessionmaker(engine, expire_on_commit=False)
    return database


def service(engine) -> ReminderService:
    result = ReminderService(manager(engine), 42, 3, now=lambda: NOW)
    result.audit.record = Mock(return_value=None)

    async def audit(*args, **kwargs):
        return None

    result.audit.record = audit
    return result


async def test_standalone_creation_and_past_rejected(engine) -> None:
    reminders = service(engine)
    created = await reminders.create_standalone(
        ReminderCreate(title="Call broker", remind_at=NOW + timedelta(hours=1))
    )
    assert created.title == "Call broker"
    assert created.status == ReminderStatus.PENDING
    with pytest.raises(ReminderValidationError):
        await reminders.create_standalone(ReminderCreate(title="Past", remind_at=NOW))


async def test_calendar_multiple_offsets_default_and_duplicate(engine) -> None:
    reminders = service(engine)
    request = CalendarReminderCreate(
        external_calendar_event_id="event-1",
        title="Meeting",
        event_start_at=NOW + timedelta(days=2),
        offsets=[1440, 60, 10],
    )
    first = await reminders.create_for_calendar(request)
    second = await reminders.create_for_calendar(request)
    assert len(first) == len(second) == 3
    assert {row.offset_minutes for row in first} == {1440, 60, 10}
    assert {row.id for row in first} == {row.id for row in second}
    default = await reminders.create_for_calendar(
        CalendarReminderCreate(
            external_calendar_event_id="event-2",
            title="Default",
            event_start_at=NOW + timedelta(hours=2),
        )
    )
    assert [row.offset_minutes for row in default] == [10]


async def test_calendar_update_cancels_pending_keeps_delivered(engine) -> None:
    reminders = service(engine)
    original = await reminders.create_for_calendar(
        CalendarReminderCreate(
            external_calendar_event_id="event",
            title="Meeting",
            event_start_at=NOW + timedelta(days=2),
            offsets=[60, 10],
        )
    )
    async with reminders.database.session() as session:
        delivered = await session.get(Reminder, original[0].id)
        delivered.status = ReminderStatus.DELIVERED
    assert await reminders.sync_calendar("event", "Moved", NOW + timedelta(days=3), [60, 10])
    async with reminders.database.session() as session:
        rows = (
            await __import__("app.modules.reminders.repository", fromlist=["ReminderRepository"])
            .ReminderRepository(session)
            .list_for_calendar_event(1, "event")
        )
    assert sum(row.status == ReminderStatus.DELIVERED for row in rows) == 1
    assert sum(row.status == ReminderStatus.CANCELLED for row in rows) == 1
    assert sum(row.status == ReminderStatus.PENDING for row in rows) == 2


async def test_calendar_delete_cancels_only_pending(engine) -> None:
    reminders = service(engine)
    rows = await reminders.create_for_calendar(
        CalendarReminderCreate(
            external_calendar_event_id="event",
            title="Meeting",
            event_start_at=NOW + timedelta(days=1),
            offsets=[60, 10],
        )
    )
    assert await reminders.cancel_calendar("event")
    assert await reminders.list_upcoming() == []
    with pytest.raises(ReminderNotFoundError):
        await reminders.cancel(rows[0].id)


async def test_calendar_empty_offsets_disable_pending(engine) -> None:
    reminders = service(engine)
    await reminders.create_for_calendar(
        CalendarReminderCreate(
            external_calendar_event_id="event",
            title="Meeting",
            event_start_at=NOW + timedelta(days=1),
            offsets=[10],
        )
    )
    assert await reminders.sync_calendar("event", "Meeting", NOW + timedelta(days=1), [])
    assert await reminders.list_upcoming() == []


async def test_list_upcoming_and_scheduler_hooks(engine) -> None:
    reminders = service(engine)
    scheduler = Mock()
    reminders.scheduler = scheduler
    later = await reminders.create_standalone(
        ReminderCreate(title="Later", remind_at=NOW + timedelta(hours=2))
    )
    early = await reminders.create_standalone(
        ReminderCreate(title="Early", remind_at=NOW + timedelta(hours=1))
    )
    assert [row.id for row in await reminders.list_upcoming()] == [early.id, later.id]
    scheduler.schedule_id.assert_any_call(early.id, early.remind_at)
    await reminders.cancel(early.id)
    scheduler.remove_reminder.assert_called_once_with(early.id)


async def test_reschedule_updates_pending_and_scheduler(engine) -> None:
    reminders = service(engine)
    scheduler = Mock()
    reminders.scheduler = scheduler
    created = await reminders.create_standalone(
        ReminderCreate(title="Move me", remind_at=NOW + timedelta(hours=1))
    )
    moved = await reminders.reschedule(created.id, NOW + timedelta(hours=3))
    assert moved.remind_at == NOW + timedelta(hours=3)
    scheduler.schedule_id.assert_called_with(moved.id, moved.remind_at)


async def test_audit_payload_excludes_content_and_token(engine) -> None:
    reminders = ReminderService(manager(engine), 42, 3, now=lambda: NOW)
    reminders.audit.record = AsyncMock()
    await reminders.create_standalone(
        ReminderCreate(
            title="Sensitive reminder text",
            message="private body token=secret",
            remind_at=NOW + timedelta(hours=1),
        )
    )
    payload = repr(reminders.audit.record.call_args)
    assert "Sensitive reminder text" not in payload
    assert "private body" not in payload
    assert "token=secret" not in payload
````

### C:/Users/USER/Documents/Agent/tests/test_reminder_dispatcher.py

````python
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.database.models import Reminder, ReminderStatus
from app.database.session import DatabaseManager
from app.modules.reminders.dispatcher import ReminderDispatcher
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.schemas import ReminderDeliveryResult
from app.modules.users.repository import UserRepository

NOW = datetime(2026, 9, 25, 10, tzinfo=UTC)


def database(engine):
    value = DatabaseManager(Settings(_env_file=None))
    value._sessions = async_sessionmaker(engine, expire_on_commit=False)
    return value


async def create_due(database, max_attempts=3, attempts=0):
    async with database.session() as session:
        user = await UserRepository(session).get_by_telegram_user_id(42)
        if not user:
            user = await UserRepository(session).create(42)
        return await ReminderRepository(session).create(
            Reminder(
                user_id=user.id,
                title="Due",
                remind_at=NOW - timedelta(minutes=1),
                max_attempts=max_attempts,
                attempt_count=attempts,
                deduplication_key=f"due-{max_attempts}-{attempts}",
            )
        )


async def test_delivery_success_marks_delivered(engine) -> None:
    db = database(engine)
    reminder = await create_due(db)
    dispatcher = ReminderDispatcher(
        db,
        Mock(deliver=AsyncMock(return_value=ReminderDeliveryResult(success=True))),
        Mock(record=AsyncMock()),
        (60,),
        now=lambda: NOW,
    )
    await dispatcher.dispatch(reminder.id)
    async with db.session() as session:
        stored = await session.get(Reminder, reminder.id)
        assert stored.status == ReminderStatus.DELIVERED
        assert stored.attempt_count == 1


async def test_failure_retries_then_fails(engine) -> None:
    db = database(engine)
    failed = ReminderDeliveryResult(success=False, failure_reason="TelegramNetworkError")
    scheduler = Mock()
    first = await create_due(db)
    dispatcher = ReminderDispatcher(
        db,
        Mock(deliver=AsyncMock(return_value=failed)),
        Mock(record=AsyncMock()),
        (60, 300),
        now=lambda: NOW,
    )
    dispatcher.scheduler = scheduler
    await dispatcher.dispatch(first.id)
    async with db.session() as session:
        stored = await session.get(Reminder, first.id)
        assert stored.status == ReminderStatus.PENDING
        assert stored.retry_at == NOW + timedelta(seconds=60)
    scheduler.schedule_id.assert_called_once_with(first.id, NOW + timedelta(seconds=60))
    last = await create_due(db, max_attempts=3, attempts=2)
    await dispatcher.dispatch(last.id)
    async with db.session() as session:
        stored = await session.get(Reminder, last.id)
        assert stored.status == ReminderStatus.FAILED
        assert stored.failure_reason == "TelegramNetworkError"
````

### C:/Users/USER/Documents/Agent/tests/test_reminder_scheduler.py

````python
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.database.models import Reminder, ReminderStatus
from app.database.session import DatabaseManager
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.scheduler import ReminderScheduler
from app.modules.users.repository import UserRepository

NOW = datetime(2026, 9, 25, 10, tzinfo=UTC)


class FakeScheduler:
    def __init__(self):
        self.jobs = {}
        self.started = self.paused = self.stopped = False

    def start(self, paused=False):
        self.started, self.paused = True, paused

    def resume(self):
        self.paused = False

    def pause(self):
        self.paused = True

    def shutdown(self, wait=True):
        self.stopped = True

    def remove_all_jobs(self):
        self.jobs.clear()

    def add_job(self, func, trigger, args, id, **kwargs):
        self.jobs[id] = (func, trigger, args, kwargs)

    def get_job(self, identifier):
        return Mock(id=identifier) if identifier in self.jobs else None

    def remove_job(self, identifier):
        self.jobs.pop(identifier, None)


def database(engine):
    value = DatabaseManager(Settings(_env_file=None))
    value._sessions = async_sessionmaker(engine, expire_on_commit=False)
    return value


async def add(db, key, at, status=ReminderStatus.PENDING, processing=None):
    async with db.session() as session:
        user = await UserRepository(session).get_by_telegram_user_id(42)
        if not user:
            user = await UserRepository(session).create(42)
        return await ReminderRepository(session).create(
            Reminder(
                user_id=user.id,
                title=key,
                remind_at=at,
                status=status,
                processing_started_at=processing,
                max_attempts=3,
                deduplication_key=key,
            )
        )


async def test_stable_job_id_remove_and_recovery(engine) -> None:
    db, backend = database(engine), FakeScheduler()
    future = await add(db, "future", NOW + timedelta(hours=1))
    dispatcher = Mock(dispatch=AsyncMock(), scheduler=None)
    scheduler = ReminderScheduler(
        db, dispatcher, Mock(record=AsyncMock()), 60, 10, now=lambda: NOW, scheduler=backend
    )
    await scheduler.start()
    assert list(backend.jobs) == [f"reminder:{future.id}"]
    assert backend.jobs[f"reminder:{future.id}"][2] == [future.id]
    scheduler.remove_reminder(future.id)
    assert backend.jobs == {}
    await scheduler.shutdown()
    assert backend.stopped


async def test_overdue_policy_and_stale_processing(engine) -> None:
    db, backend = database(engine), FakeScheduler()
    recent = await add(db, "recent", NOW - timedelta(minutes=30))
    old = await add(db, "old", NOW - timedelta(minutes=61))
    stale = await add(
        db,
        "stale",
        NOW - timedelta(hours=1),
        ReminderStatus.PROCESSING,
        NOW - timedelta(minutes=20),
    )
    scheduler = ReminderScheduler(
        db,
        Mock(dispatch=AsyncMock(), scheduler=None),
        Mock(record=AsyncMock()),
        60,
        10,
        now=lambda: NOW,
        scheduler=backend,
    )
    await scheduler.start()
    assert f"reminder:{recent.id}" in backend.jobs
    assert f"reminder:{stale.id}" in backend.jobs
    assert f"reminder:{old.id}" not in backend.jobs
    async with db.session() as session:
        assert (await session.get(Reminder, old.id)).status == ReminderStatus.MISSED
        assert (await session.get(Reminder, stale.id)).status == ReminderStatus.PENDING
    await scheduler.shutdown()


async def test_stale_processing_at_max_attempts_fails(engine) -> None:
    db, backend = database(engine), FakeScheduler()
    reminder = await add(
        db,
        "stale-max",
        NOW - timedelta(hours=1),
        ReminderStatus.PROCESSING,
        NOW - timedelta(minutes=20),
    )
    async with db.session() as session:
        stored = await session.get(Reminder, reminder.id)
        stored.attempt_count = stored.max_attempts
    scheduler = ReminderScheduler(
        db,
        Mock(dispatch=AsyncMock(), scheduler=None),
        Mock(record=AsyncMock()),
        60,
        10,
        now=lambda: NOW,
        scheduler=backend,
    )
    await scheduler.start()
    async with db.session() as session:
        assert (await session.get(Reminder, reminder.id)).status == ReminderStatus.FAILED
    assert f"reminder:{reminder.id}" not in backend.jobs
    await scheduler.shutdown()


async def test_restart_rebuilds_from_database(engine) -> None:
    db = database(engine)
    reminder = await add(db, "restart", NOW + timedelta(hours=1))
    first = ReminderScheduler(
        db,
        Mock(dispatch=AsyncMock(), scheduler=None),
        Mock(record=AsyncMock()),
        60,
        10,
        now=lambda: NOW,
        scheduler=FakeScheduler(),
    )
    await first.start()
    await first.shutdown()
    second_backend = FakeScheduler()
    second = ReminderScheduler(
        db,
        Mock(dispatch=AsyncMock(), scheduler=None),
        Mock(record=AsyncMock()),
        60,
        10,
        now=lambda: NOW,
        scheduler=second_backend,
    )
    await second.start()
    assert f"reminder:{reminder.id}" in second_backend.jobs
    await second.shutdown()
````

### C:/Users/USER/Documents/Agent/tests/test_reminder_delivery.py

````python
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

from app.database.models import Reminder
from app.modules.reminders.delivery import TelegramReminderDelivery
from app.modules.security.lock_service import LockService


def reminder(offset=None):
    return Reminder(
        id=1,
        user_id=999,
        title="Private title",
        message=None,
        remind_at=datetime(2026, 9, 25, 10, tzinfo=UTC),
        event_start_at=datetime(2026, 9, 25, 11, tzinfo=UTC) if offset else None,
        offset_minutes=offset,
        max_attempts=3,
        deduplication_key="key",
    )


async def test_delivery_targets_configured_owner_only() -> None:
    bot = Mock(send_message=AsyncMock())
    delivery = TelegramReminderDelivery(bot, 42, ZoneInfo("Asia/Tashkent"))
    assert (await delivery.deliver(reminder(10))).success
    bot.send_message.assert_awaited_once()
    assert bot.send_message.call_args.args[0] == 42
    assert "10 daqiqadan keyin" in bot.send_message.call_args.args[1]


async def test_delivery_failure_is_sanitized() -> None:
    bot = Mock(send_message=AsyncMock(side_effect=OSError("token=private")))
    result = await TelegramReminderDelivery(bot, 42, ZoneInfo("Asia/Tashkent")).deliver(reminder())
    assert not result.success
    assert result.failure_reason == "OSError"
    assert "private" not in result.model_dump_json()


async def test_scheduled_delivery_ignores_interactive_lock() -> None:
    lock = LockService()
    assert await lock.is_locked()
    bot = Mock(send_message=AsyncMock())
    result = await TelegramReminderDelivery(bot, 42, ZoneInfo("Asia/Tashkent")).deliver(reminder())
    assert result.success
    bot.send_message.assert_awaited_once()
````

### C:/Users/USER/Documents/Agent/tests/test_calendar_reminder_sync.py

````python
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventUpdate
from app.modules.calendar.service import CalendarService

TZ = ZoneInfo("Asia/Tashkent")


def raw():
    return {
        "id": "event",
        "etag": '"v1"',
        "summary": "Meeting",
        "start": {"dateTime": "2026-09-25T15:00:00+05:00"},
        "end": {"dateTime": "2026-09-25T16:00:00+05:00"},
    }


def event():
    return CalendarEventCreate(
        title="Meeting",
        start="2026-09-25T15:00:00+05:00",
        end="2026-09-25T16:00:00+05:00",
        reminders=[60, 10],
    )


async def test_create_syncs_after_google_success() -> None:
    sequence = []
    client = Mock(
        create_event=AsyncMock(side_effect=lambda payload: sequence.append("google") or raw())
    )
    sync = Mock(
        sync_calendar=AsyncMock(side_effect=lambda *args: sequence.append("reminders") or True)
    )
    service = CalendarService(client, Mock(record=AsyncMock()), TZ, sync)
    result = await service.create_event(event(), "a" * 32)
    assert sequence == ["google", "reminders"]
    sync.sync_calendar.assert_awaited_once_with(
        "event", "Meeting", datetime.fromisoformat("2026-09-25T15:00:00+05:00"), [60, 10]
    )
    assert not result.reminder_warning


async def test_sync_failure_warns_without_repeating_google() -> None:
    client = Mock(create_event=AsyncMock(return_value=raw()))
    sync = Mock(sync_calendar=AsyncMock(return_value=False))
    result = await CalendarService(client, Mock(record=AsyncMock()), TZ, sync).create_event(
        event(), "a" * 32
    )
    assert result.reminder_warning
    client.create_event.assert_awaited_once()


async def test_update_syncs_and_delete_cancels() -> None:
    client = Mock(
        get_event=AsyncMock(return_value=raw()),
        update_event=AsyncMock(return_value=raw()),
        delete_event=AsyncMock(),
    )
    sync = Mock(
        sync_calendar=AsyncMock(return_value=True), cancel_calendar=AsyncMock(return_value=True)
    )
    service = CalendarService(client, Mock(record=AsyncMock()), TZ, sync)
    update = CalendarEventUpdate(**event().model_dump(), fields={"start", "end"})
    await service.update_event("event", update, '"v1"')
    sync.sync_calendar.assert_awaited_once_with(
        "event", "Meeting", datetime.fromisoformat("2026-09-25T15:00:00+05:00"), None
    )
    assert await service.delete_event("event", '"v1"')
    sync.cancel_calendar.assert_awaited_once_with("event")
````

### C:/Users/USER/Documents/Agent/tests/test_reminder_config_health.py

````python
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError

from app.api.routes.health import snapshot
from app.core.application import ApplicationContext
from app.core.config import Settings
from app.modules.reminders.exceptions import ReminderConfigurationError


def settings(**values):
    defaults = {
        "DATABASE_URL": None,
        "REDIS_URL": None,
        "TELEGRAM_BOT_TOKEN": None,
        "TELEGRAM_OWNER_ID": None,
        "RUN_REMINDER_SCHEDULER": False,
    }
    return Settings(_env_file=None, **{**defaults, **values})


def test_reminder_settings_and_retry_validation() -> None:
    value = settings()
    assert value.reminder_default_offset_minutes == 10
    assert value.reminder_retry_delays == (60, 300, 900)
    with pytest.raises(ValidationError):
        settings(REMINDER_RETRY_DELAYS_SECONDS="60,secret")
    with pytest.raises(ValidationError):
        settings(REMINDER_MAX_ATTEMPTS=0)


async def test_scheduler_requires_telegram_mode_and_database() -> None:
    context = ApplicationContext(settings(RUN_REMINDER_SCHEDULER=True))
    with pytest.raises(ReminderConfigurationError, match="Telegram"):
        await context.start()
    context = ApplicationContext(
        settings(
            RUN_REMINDER_SCHEDULER=True,
            TELEGRAM_BOT_TOKEN="123456789:TEST_ONLY_FAKE_TOKEN_abc",
            TELEGRAM_OWNER_ID=42,
        ),
        telegram=True,
    )
    with patch("app.core.application.TelegramRuntime") as runtime:
        instance = runtime.return_value
        instance.prepare = AsyncMock()
        instance.close = AsyncMock()
        instance.bot = Mock()
        instance.context = Mock()
        with pytest.raises(ReminderConfigurationError, match="DATABASE_URL"):
            await context.start()


async def test_health_reports_scheduler_state() -> None:
    context = ApplicationContext(settings())
    await context.start()
    assert (await snapshot(context)).services.reminder_scheduler == "disabled"
    context.runtime.reminder_scheduler_required = True
    context.runtime.reminder_scheduler = "error"
    assert (await snapshot(context)).status == "error"
    await context.close()


async def test_lifecycle_starts_once_and_stops_scheduler_first() -> None:
    calls = []
    database = Mock(initialize=Mock(), dispose=AsyncMock(side_effect=lambda: calls.append("db")))
    calendar = Mock(close=AsyncMock(side_effect=lambda: calls.append("calendar")))
    telegram = Mock(
        prepare=AsyncMock(), close=AsyncMock(side_effect=lambda: calls.append("telegram"))
    )
    telegram.bot, telegram.context = Mock(), Mock()
    reminders = Mock(
        start=AsyncMock(), close=AsyncMock(side_effect=lambda: calls.append("reminders"))
    )
    reminders.service = Mock()
    configured = settings(
        RUN_REMINDER_SCHEDULER=True,
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        TELEGRAM_BOT_TOKEN="123456789:TEST_ONLY_FAKE_TOKEN_abc",
        TELEGRAM_OWNER_ID=42,
        BOT_PIN="test-pin",
    )
    with (
        patch("app.core.application.DatabaseManager", return_value=database),
        patch("app.core.application.CalendarRuntime", return_value=calendar),
        patch("app.core.application.TelegramRuntime", return_value=telegram),
        patch("app.core.application.ReminderRuntime", return_value=reminders),
    ):
        context = ApplicationContext(configured, telegram=True)
        await context.start()
        await context.start()
        reminders.start.assert_awaited_once()
        assert context.runtime.reminder_scheduler == "running"
        await context.close()
        assert calls == ["reminders", "telegram", "calendar", "db"]
````

### C:/Users/USER/Documents/Agent/tests/bot/test_reminder_handlers.py

````python
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
from aiogram.methods import SendMessage
from aiogram.types import Update

from app.bot.constants import DENIED, LOCKED
from app.modules.calendar.state import MemoryTemporaryStore
from app.modules.reminders.actions import ReminderActions
from app.modules.reminders.schemas import ReminderView

from .conftest import Harness


def attach(harness: Harness) -> Mock:
    runtime = Mock()
    runtime.timezone = ZoneInfo("Asia/Tashkent")
    runtime.service.create_standalone = AsyncMock()
    runtime.service.cancel = AsyncMock()
    runtime.service.list_upcoming = AsyncMock(return_value=[])
    runtime.actions = ReminderActions(runtime.service, MemoryTemporaryStore(), 42)
    harness.context.reminders = runtime
    return runtime


async def callback(harness: Harness, data: str) -> None:
    harness.sequence += 1
    update = Update.model_validate(
        {
            "update_id": harness.sequence,
            "callback_query": {
                "id": str(harness.sequence),
                "from": {"id": 42, "is_bot": False, "first_name": "Test"},
                "chat_instance": "test",
                "data": data,
                "message": {
                    "message_id": 123,
                    "date": datetime.now(UTC),
                    "chat": {"id": 42, "type": "private"},
                },
            },
        },
        context={"bot": harness.bot},
    )
    await harness.dispatcher.feed_update(harness.bot, update)


@pytest.mark.parametrize("command", ["/remind", "/reminders", "/reminder_cancel"])
async def test_owner_and_lock_boundary(harness: Harness, command: str) -> None:
    attach(harness)
    await harness.send(command, user_id=99)
    assert harness.replies[-1] == DENIED
    await harness.send(command)
    assert harness.replies[-1] == LOCKED


async def test_remind_requires_confirmation_and_double_click_safe(harness: Harness) -> None:
    runtime = attach(harness)
    await harness.context.security.lock_state.unlock()
    future = datetime.now(ZoneInfo("Asia/Tashkent")) + timedelta(days=2)
    for text in ["/remind", "Call broker", future.strftime("%d.%m.%Y"), future.strftime("%H:%M")]:
        await harness.send(text)
    runtime.service.create_standalone.assert_not_called()
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    data = prompt.reply_markup.inline_keyboard[0][0].callback_data
    await callback(harness, data)
    await callback(harness, data)
    runtime.service.create_standalone.assert_awaited_once()
    assert "Reminder saqlandi." in harness.replies


async def test_reminders_formatting(harness: Harness) -> None:
    runtime = attach(harness)
    runtime.service.list_upcoming.return_value = [
        ReminderView(
            id=1,
            title="Call broker",
            message=None,
            remind_at="2026-09-25T12:00:00Z",
            event_start_at=None,
            offset_minutes=None,
            status="PENDING",
            channel="TELEGRAM",
            attempt_count=0,
            max_attempts=3,
            external_calendar_event_id=None,
        )
    ]
    await harness.context.security.lock_state.unlock()
    await harness.send("/reminders")
    assert "Call broker" in harness.replies[-1]
    assert "17:00" in harness.replies[-1]


async def test_cancel_requires_confirmation(harness: Harness) -> None:
    runtime = attach(harness)
    runtime.service.list_upcoming.return_value = [
        ReminderView(
            id=7,
            title="Call broker",
            message=None,
            remind_at="2026-09-25T12:00:00Z",
            event_start_at=None,
            offset_minutes=None,
            status="PENDING",
            channel="TELEGRAM",
            attempt_count=0,
            max_attempts=3,
            external_calendar_event_id=None,
        )
    ]
    await harness.context.security.lock_state.unlock()
    await harness.send("/reminder_cancel")
    await harness.send("1")
    runtime.service.cancel.assert_not_called()
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    await callback(harness, prompt.reply_markup.inline_keyboard[0][0].callback_data)
    runtime.service.cancel.assert_awaited_once_with(7)
````

### C:/Users/USER/Documents/Agent/app/modules/reminders/actions.py

````python
from typing import Any

from app.modules.calendar.state import TemporaryStore
from app.modules.reminders.exceptions import ReminderError
from app.modules.reminders.schemas import ReminderCreate
from app.modules.reminders.service import ReminderService


class ReminderActions:
    """Single-use confirmation handles for persistent reminder changes."""

    def __init__(self, service: ReminderService, states: TemporaryStore, owner_id: int) -> None:
        self.service, self.states, self.owner_id = service, states, owner_id

    async def prepare(self, kind: str, data: dict[str, Any]) -> str:
        return await self.states.issue(
            "reminder_action", {"kind": kind, "data": data, "owner": self.owner_id}
        )

    async def cancel_action(self, token: str) -> None:
        await self.states.consume("reminder_action", token)

    async def confirm(self, token: str) -> str:
        action = await self.states.consume("reminder_action", token)
        if not action or action["owner"] != self.owner_id:
            raise ReminderError("Confirmation expired or already processed.")
        if action["kind"] == "create":
            await self.service.create_standalone(ReminderCreate.model_validate(action["data"]))
            return "Reminder saqlandi."
        if action["kind"] == "cancel":
            await self.service.cancel(int(action["data"]["id"]))
            return "Reminder bekor qilindi."
        raise ReminderError("Invalid reminder confirmation.")
````

### C:/Users/USER/Documents/Agent/app/modules/reminders/audit.py

````python
import asyncio
import logging
from datetime import datetime

from app.core.logging import report_error
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.users.repository import UserRepository


class ReminderAudit:
    """Best-effort audit in an independent transaction, without reminder content."""

    def __init__(self, database: DatabaseManager, owner_id: int) -> None:
        self.database, self.owner_id = database, owner_id

    async def record(
        self, action: AuditAction, reminder_id: int, scheduled_at: datetime | None = None
    ) -> None:
        details: dict[str, object] = {"reminder_id": reminder_id}
        if scheduled_at:
            details["scheduled_at"] = scheduled_at.isoformat()
        try:
            async with asyncio.timeout(5), self.database.session() as session:
                user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
                await AuditService(AuditRepository(session)).log_event(
                    action,
                    user_id=user.id if user else None,
                    entity_type="reminder",
                    entity_id=str(reminder_id),
                    details=details,
                )
        except Exception as error:  # noqa: BLE001 - best-effort boundary after domain action
            report_error(logging.getLogger(__name__), error)
````

### C:/Users/USER/Documents/Agent/app/modules/reminders/delivery.py

````python
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.database.models import Reminder
from app.modules.reminders.schemas import ReminderDeliveryResult
from app.modules.reminders.utils import sanitize_failure


class TelegramReminderDelivery:
    """Telegram transport only; the destination is the configured owner, never a row field."""

    def __init__(self, bot: Bot, owner_id: int, timezone: ZoneInfo) -> None:
        self.bot, self.owner_id, self.timezone = bot, owner_id, timezone

    def text(self, reminder: Reminder) -> str:
        if reminder.offset_minutes == 1440:
            heading = "Ertaga:"
        elif reminder.offset_minutes == 60:
            heading = "1 soatdan keyin:"
        elif reminder.offset_minutes:
            heading = f"{reminder.offset_minutes} daqiqadan keyin:"
        else:
            heading = "Eslatma"
        details = reminder.message or reminder.title
        event_time = (
            f"\n\n{reminder.event_start_at.astimezone(self.timezone):%H:%M}"
            if reminder.event_start_at
            else ""
        )
        return f"⏰ {heading}\n\n{details}{event_time}"

    async def deliver(self, reminder: Reminder) -> ReminderDeliveryResult:
        try:
            await self.bot.send_message(self.owner_id, self.text(reminder), parse_mode=None)
            return ReminderDeliveryResult(success=True)
        except (TelegramAPIError, OSError, TimeoutError) as error:
            return ReminderDeliveryResult(success=False, failure_reason=sanitize_failure(error))
````

### C:/Users/USER/Documents/Agent/app/modules/reminders/dispatcher.py

````python
from datetime import timedelta

from app.database.models import ReminderStatus
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.reminders.audit import ReminderAudit
from app.modules.reminders.delivery import TelegramReminderDelivery
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.utils import utc_now


class ReminderDispatcher:
    """Claim, deliver, persist outcome, then arrange a bounded retry."""

    def __init__(
        self,
        database: DatabaseManager,
        delivery: TelegramReminderDelivery,
        audit: ReminderAudit,
        retry_delays: tuple[int, ...],
        *,
        now=utc_now,
    ) -> None:
        self.database, self.delivery, self.audit = database, delivery, audit
        self.retry_delays, self.now = retry_delays, now
        self.scheduler = None

    async def dispatch(self, reminder_id: int) -> None:
        now = self.now()
        async with self.database.session() as session:
            reminder = await ReminderRepository(session).claim(reminder_id, now)
        if reminder is None:
            return
        result = await self.delivery.deliver(reminder)
        completed = self.now()
        if result.success:
            async with self.database.session() as session:
                changed = await ReminderRepository(session).mark_delivered(reminder_id, completed)
            if changed:
                await self.audit.record(AuditAction.REMINDER_DELIVERED, reminder_id)
            return
        retry_at = None
        if reminder.attempt_count < reminder.max_attempts:
            delay_index = min(reminder.attempt_count - 1, len(self.retry_delays) - 1)
            retry_at = completed + timedelta(seconds=self.retry_delays[delay_index])
        async with self.database.session() as session:
            status = await ReminderRepository(session).mark_retry_or_failed(
                reminder_id, completed, retry_at, result.failure_reason or "delivery_failed"
            )
        if status == ReminderStatus.PENDING and retry_at is not None:
            await self.audit.record(AuditAction.REMINDER_RETRY, reminder_id, retry_at)
            if self.scheduler:
                self.scheduler.schedule_id(reminder_id, retry_at)
        elif status == ReminderStatus.FAILED:
            await self.audit.record(AuditAction.REMINDER_FAILED, reminder_id)
````

### C:/Users/USER/Documents/Agent/app/modules/reminders/exceptions.py

````python
class ReminderError(Exception):
    """Safe domain error suitable for owner-facing messages."""


class ReminderConfigurationError(ReminderError):
    pass


class ReminderNotFoundError(ReminderError):
    pass


class ReminderValidationError(ReminderError):
    pass
````

### C:/Users/USER/Documents/Agent/app/modules/reminders/repository.py

````python
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Reminder, ReminderStatus


class ReminderRepository:
    """Transaction-local reminder persistence; callers own commit boundaries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, reminder: Reminder) -> Reminder:
        self.session.add(reminder)
        await self.session.flush()
        return reminder

    async def get_by_id(self, reminder_id: int) -> Reminder | None:
        return await self.session.get(Reminder, reminder_id)

    async def find_by_deduplication_key(self, key: str) -> Reminder | None:
        return await self.session.scalar(select(Reminder).where(Reminder.deduplication_key == key))

    async def list_pending(self, user_id: int | None = None, limit: int = 1000) -> list[Reminder]:
        statement = select(Reminder).where(Reminder.status == ReminderStatus.PENDING)
        if user_id is not None:
            statement = statement.where(Reminder.user_id == user_id)
        next_run = func.coalesce(Reminder.retry_at, Reminder.remind_at)
        return list((await self.session.scalars(statement.order_by(next_run).limit(limit))).all())

    async def list_due(self, now: datetime, limit: int = 100) -> list[Reminder]:
        next_run = func.coalesce(Reminder.retry_at, Reminder.remind_at)
        result = await self.session.scalars(
            select(Reminder)
            .where(Reminder.status == ReminderStatus.PENDING, next_run <= now)
            .order_by(next_run)
            .limit(limit)
        )
        return list(result.all())

    async def list_upcoming(self, user_id: int, now: datetime, limit: int = 10) -> list[Reminder]:
        next_run = func.coalesce(Reminder.retry_at, Reminder.remind_at)
        result = await self.session.scalars(
            select(Reminder)
            .where(
                Reminder.user_id == user_id,
                Reminder.status == ReminderStatus.PENDING,
                next_run > now,
            )
            .order_by(next_run)
            .limit(limit)
        )
        return list(result.all())

    async def list_for_calendar_event(self, user_id: int, event_id: str) -> list[Reminder]:
        return list(
            (
                await self.session.scalars(
                    select(Reminder)
                    .where(
                        Reminder.user_id == user_id,
                        Reminder.external_calendar_event_id == event_id,
                    )
                    .order_by(Reminder.remind_at)
                )
            ).all()
        )

    async def claim(self, reminder_id: int, now: datetime) -> Reminder | None:
        """Atomic PENDING to PROCESSING transition; only one worker receives a row."""
        next_run = func.coalesce(Reminder.retry_at, Reminder.remind_at)
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.status == ReminderStatus.PENDING,
                next_run <= now,
            )
            .values(
                status=ReminderStatus.PROCESSING,
                processing_started_at=now,
                last_attempt_at=now,
                attempt_count=Reminder.attempt_count + 1,
            )
            .returning(Reminder)
        )
        return result.scalar_one_or_none()

    async def mark_delivered(self, reminder_id: int, now: datetime) -> bool:
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.status == ReminderStatus.PROCESSING,
            )
            .values(
                status=ReminderStatus.DELIVERED,
                delivered_at=now,
                processing_started_at=None,
                retry_at=None,
                failure_reason=None,
            )
        )
        return bool(result.rowcount)

    async def mark_retry_or_failed(
        self, reminder_id: int, now: datetime, retry_at: datetime | None, reason: str
    ) -> ReminderStatus | None:
        status = ReminderStatus.PENDING if retry_at else ReminderStatus.FAILED
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.status == ReminderStatus.PROCESSING,
            )
            .values(
                status=status,
                retry_at=retry_at,
                failed_at=None if retry_at else now,
                processing_started_at=None,
                failure_reason=reason,
            )
            .returning(Reminder.status)
        )
        return result.scalar_one_or_none()

    async def mark_missed(self, reminder_id: int, now: datetime) -> bool:
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.status == ReminderStatus.PENDING,
            )
            .values(
                status=ReminderStatus.MISSED,
                failed_at=now,
                failure_reason="overdue_grace_exceeded",
                retry_at=None,
            )
        )
        return bool(result.rowcount)

    async def cancel(self, reminder_id: int, user_id: int, now: datetime) -> bool:
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id,
                Reminder.status == ReminderStatus.PENDING,
            )
            .values(status=ReminderStatus.CANCELLED, cancelled_at=now, retry_at=None)
        )
        return bool(result.rowcount)

    async def reschedule(
        self, reminder_id: int, user_id: int, remind_at: datetime, key: str
    ) -> Reminder | None:
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id,
                Reminder.status == ReminderStatus.PENDING,
            )
            .values(
                remind_at=remind_at,
                retry_at=None,
                failure_reason=None,
                deduplication_key=key,
            )
            .returning(Reminder)
        )
        return result.scalar_one_or_none()

    async def cancel_calendar_pending(
        self, user_id: int, event_id: str, now: datetime
    ) -> list[int]:
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.user_id == user_id,
                Reminder.external_calendar_event_id == event_id,
                Reminder.status == ReminderStatus.PENDING,
            )
            .values(status=ReminderStatus.CANCELLED, cancelled_at=now, retry_at=None)
            .returning(Reminder.id)
        )
        return list(result.scalars().all())

    async def recover_stale(self, before: datetime, now: datetime) -> tuple[list[int], list[int]]:
        failed = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.status == ReminderStatus.PROCESSING,
                Reminder.processing_started_at < before,
                Reminder.attempt_count >= Reminder.max_attempts,
            )
            .values(
                status=ReminderStatus.FAILED,
                processing_started_at=None,
                failed_at=now,
                failure_reason="stale_processing_max_attempts",
            )
            .returning(Reminder.id)
        )
        recovered = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.status == ReminderStatus.PROCESSING,
                Reminder.processing_started_at < before,
                Reminder.attempt_count < Reminder.max_attempts,
            )
            .values(
                status=ReminderStatus.PENDING,
                processing_started_at=None,
                retry_at=now,
                failure_reason="stale_processing_recovered",
            )
            .returning(Reminder.id)
        )
        return list(recovered.scalars().all()), list(failed.scalars().all())
````

### C:/Users/USER/Documents/Agent/app/modules/reminders/runtime.py

````python
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
````

### C:/Users/USER/Documents/Agent/app/modules/reminders/scheduler.py

````python
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.reminders.audit import ReminderAudit
from app.modules.reminders.dispatcher import ReminderDispatcher
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.utils import job_id, utc_now


class ReminderScheduler:
    """In-memory wake-up index rebuilt from PostgreSQL on every startup."""

    def __init__(
        self,
        database: DatabaseManager,
        dispatcher: ReminderDispatcher,
        audit: ReminderAudit,
        overdue_grace_minutes: int,
        processing_timeout_minutes: int,
        *,
        now=utc_now,
        scheduler: AsyncIOScheduler | None = None,
    ) -> None:
        self.database, self.dispatcher, self.audit = database, dispatcher, audit
        self.overdue_grace = timedelta(minutes=overdue_grace_minutes)
        self.processing_timeout = timedelta(minutes=processing_timeout_minutes)
        self.now = now
        self.scheduler = scheduler or AsyncIOScheduler(timezone="UTC")
        self.running = False
        dispatcher.scheduler = self

    async def start(self) -> None:
        if self.running:
            return
        self.scheduler.start(paused=True)
        try:
            await self.recover_pending()
            self.scheduler.resume()
            self.running = True
        except BaseException:
            self.scheduler.shutdown(wait=False)
            raise

    async def shutdown(self) -> None:
        if not self.running:
            return
        self.running = False
        self.scheduler.pause()
        self.scheduler.remove_all_jobs()
        self.scheduler.shutdown(wait=True)

    def schedule_id(self, reminder_id: int, run_at: datetime) -> None:
        self.scheduler.add_job(
            self.dispatcher.dispatch,
            DateTrigger(run_date=run_at),
            args=[reminder_id],
            id=job_id(reminder_id),
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=None,
        )

    def remove_reminder(self, reminder_id: int) -> None:
        job = self.scheduler.get_job(job_id(reminder_id))
        if job is not None:
            self.scheduler.remove_job(job.id)

    async def recover_pending(self) -> None:
        now = self.now()
        async with self.database.session() as session:
            repository = ReminderRepository(session)
            stale, stale_failed = await repository.recover_stale(now - self.processing_timeout, now)
            pending = await repository.list_pending()
        if stale:
            logging.getLogger(__name__).warning(
                "stale_reminders_recovered", extra={"action": "recovery"}
            )
        for reminder_id in stale_failed:
            await self.audit.record(AuditAction.REMINDER_FAILED, reminder_id)
        for reminder in pending:
            run_at = reminder.retry_at or reminder.remind_at
            overdue = now - run_at
            if overdue > self.overdue_grace:
                async with self.database.session() as session:
                    missed = await ReminderRepository(session).mark_missed(reminder.id, now)
                if missed:
                    await self.audit.record(AuditAction.REMINDER_FAILED, reminder.id)
                continue
            self.schedule_id(reminder.id, max(run_at, now))
````

### C:/Users/USER/Documents/Agent/app/modules/reminders/schemas.py

````python
from datetime import UTC, datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.database.models.reminder import ReminderChannel, ReminderStatus

Offset = Annotated[int, Field(strict=True, ge=1, le=40320)]


class ReminderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    title: str = Field(min_length=1, max_length=200)
    message: str | None = Field(default=None, max_length=2000)
    remind_at: AwareDatetime

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Reminder text is required")
        return value.strip()


class CalendarReminderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    external_calendar_event_id: str = Field(min_length=1, max_length=1024)
    title: str = Field(min_length=1, max_length=200)
    event_start_at: AwareDatetime
    offsets: list[Offset] = Field(default_factory=lambda: [10], min_length=1, max_length=5)

    @field_validator("offsets")
    @classmethod
    def unique_offsets(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate reminder offsets")
        return value


class ReminderView(BaseModel):
    id: int
    title: str
    message: str | None
    remind_at: datetime
    event_start_at: datetime | None
    offset_minutes: int | None
    status: ReminderStatus
    channel: ReminderChannel
    attempt_count: int
    max_attempts: int
    external_calendar_event_id: str | None

    @field_validator("remind_at", "event_start_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Timezone-aware datetime required")
        return value.astimezone(UTC) if value else None


class ReminderDeliveryResult(BaseModel):
    success: bool
    failure_reason: str | None = None
````

### C:/Users/USER/Documents/Agent/app/modules/reminders/service.py

````python
import logging
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.database.models import Reminder, ReminderStatus
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.reminders.audit import ReminderAudit
from app.modules.reminders.exceptions import ReminderNotFoundError, ReminderValidationError
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.schemas import CalendarReminderCreate, ReminderCreate, ReminderView
from app.modules.reminders.utils import deduplication_key, utc_now
from app.modules.users.repository import UserRepository


class SchedulerPort(Protocol):
    def schedule_id(self, reminder_id: int, run_at: datetime) -> None: ...
    def remove_reminder(self, reminder_id: int) -> None: ...


class ReminderService:
    def __init__(
        self,
        database: DatabaseManager,
        owner_id: int,
        max_attempts: int,
        default_offset: int = 10,
        *,
        now=utc_now,
    ) -> None:
        self.database, self.owner_id = database, owner_id
        self.max_attempts, self.default_offset = max_attempts, default_offset
        self.now = now
        self.scheduler: SchedulerPort | None = None
        self.audit = ReminderAudit(database, owner_id)

    async def _owner(self, session) -> int:
        users = UserRepository(session)
        user = await users.get_by_telegram_user_id(self.owner_id)
        if user is None:
            user = await users.create(self.owner_id)
        return user.id

    def _view(self, reminder: Reminder) -> ReminderView:
        return ReminderView.model_validate(reminder, from_attributes=True)

    async def create_standalone(self, request: ReminderCreate) -> ReminderView:
        now = self.now()
        if request.remind_at.astimezone(UTC) <= now:
            raise ReminderValidationError("Reminder time must be in the future.")
        key = deduplication_key(
            "standalone",
            self.owner_id,
            uuid4().hex,
        )
        reminder = Reminder(
            user_id=0,
            title=request.title,
            message=request.message,
            remind_at=request.remind_at.astimezone(UTC),
            max_attempts=self.max_attempts,
            deduplication_key=key,
        )
        try:
            async with self.database.session() as session:
                reminder.user_id = await self._owner(session)
                existing = await ReminderRepository(session).find_by_deduplication_key(key)
                if existing:
                    return self._view(existing)
                await ReminderRepository(session).create(reminder)
        except IntegrityError:
            async with self.database.session() as session:
                existing = await ReminderRepository(session).find_by_deduplication_key(key)
                if existing is None:
                    raise
                return self._view(existing)
        if self.scheduler:
            self.scheduler.schedule_id(reminder.id, reminder.remind_at)
        await self.audit.record(AuditAction.REMINDER_CREATED, reminder.id, reminder.remind_at)
        return self._view(reminder)

    async def create_for_calendar(self, request: CalendarReminderCreate) -> list[ReminderView]:
        now = self.now()
        occurrences: list[tuple[Reminder, bool]] = []
        offsets = request.offsets or [self.default_offset]
        async with self.database.session() as session:
            owner = await self._owner(session)
            repository = ReminderRepository(session)
            for offset in offsets:
                remind_at = request.event_start_at.astimezone(UTC) - timedelta(minutes=offset)
                if remind_at <= now:
                    continue
                key = deduplication_key(
                    "calendar",
                    self.owner_id,
                    request.external_calendar_event_id,
                    request.event_start_at.astimezone(UTC).isoformat(),
                    offset,
                    "telegram",
                )
                reminder = Reminder(
                    user_id=owner,
                    external_calendar_event_id=request.external_calendar_event_id,
                    title=request.title,
                    remind_at=remind_at,
                    event_start_at=request.event_start_at.astimezone(UTC),
                    offset_minutes=offset,
                    max_attempts=self.max_attempts,
                    deduplication_key=key,
                )
                existing = await repository.find_by_deduplication_key(key)
                if existing:
                    occurrences.append((existing, False))
                    continue
                try:
                    async with session.begin_nested():
                        await repository.create(reminder)
                    occurrences.append((reminder, True))
                except IntegrityError:
                    existing = await repository.find_by_deduplication_key(key)
                    if existing is None:
                        raise
                    occurrences.append((existing, False))
        for reminder, was_created in occurrences:
            if self.scheduler and reminder.status == ReminderStatus.PENDING:
                self.scheduler.schedule_id(reminder.id, reminder.retry_at or reminder.remind_at)
            if was_created:
                await self.audit.record(
                    AuditAction.REMINDER_CREATED, reminder.id, reminder.remind_at
                )
        return [self._view(item) for item, _ in occurrences]

    async def list_upcoming(self, limit: int = 10) -> list[ReminderView]:
        async with self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            if user is None:
                return []
            rows = await ReminderRepository(session).list_upcoming(user.id, self.now(), limit)
            return [self._view(item) for item in rows]

    async def cancel(self, reminder_id: int) -> None:
        now = self.now()
        async with self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            if user is None or not await ReminderRepository(session).cancel(
                reminder_id, user.id, now
            ):
                raise ReminderNotFoundError("Pending reminder not found.")
        if self.scheduler:
            self.scheduler.remove_reminder(reminder_id)
        await self.audit.record(AuditAction.REMINDER_CANCELLED, reminder_id)

    async def reschedule(self, reminder_id: int, remind_at: datetime) -> ReminderView:
        remind_at = remind_at.astimezone(UTC)
        if remind_at <= self.now():
            raise ReminderValidationError("Reminder time must be in the future.")
        async with self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            reminder = (
                await ReminderRepository(session).reschedule(
                    reminder_id,
                    user.id,
                    remind_at,
                    deduplication_key("rescheduled", self.owner_id, reminder_id, uuid4().hex),
                )
                if user
                else None
            )
            if reminder is None:
                raise ReminderNotFoundError("Pending reminder not found.")
        if self.scheduler:
            self.scheduler.schedule_id(reminder.id, reminder.remind_at)
        await self.audit.record(AuditAction.REMINDER_RESCHEDULED, reminder.id, reminder.remind_at)
        return self._view(reminder)

    async def cancel_calendar(self, event_id: str) -> bool:
        now = self.now()
        async with self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            ids = (
                await ReminderRepository(session).cancel_calendar_pending(user.id, event_id, now)
                if user
                else []
            )
        for reminder_id in ids:
            if self.scheduler:
                self.scheduler.remove_reminder(reminder_id)
            await self.audit.record(AuditAction.REMINDER_CANCELLED, reminder_id)
        return True

    async def sync_calendar(
        self, event_id: str, title: str, start: datetime, offsets: list[int] | None
    ) -> bool:
        try:
            if offsets is None:
                async with self.database.session() as session:
                    user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
                    existing = (
                        await ReminderRepository(session).list_for_calendar_event(user.id, event_id)
                        if user
                        else []
                    )
                    offsets = sorted(
                        {
                            row.offset_minutes
                            for row in existing
                            if row.status == ReminderStatus.PENDING
                            and row.offset_minutes is not None
                        }
                    )
                offsets = offsets or [self.default_offset]
            await self.cancel_calendar(event_id)
            if not offsets:
                return True
            reminders = await self.create_for_calendar(
                CalendarReminderCreate(
                    external_calendar_event_id=event_id,
                    title=title,
                    event_start_at=start,
                    offsets=offsets or [self.default_offset],
                )
            )
            for reminder in reminders:
                await self.audit.record(
                    AuditAction.REMINDER_RESCHEDULED, reminder.id, reminder.remind_at
                )
            return True
        except Exception as error:  # noqa: BLE001 - Google action already succeeded
            logging.getLogger(__name__).warning(
                "calendar_reminder_sync_failed", extra={"error_type": type(error).__name__}
            )
            return False
````

### C:/Users/USER/Documents/Agent/app/modules/reminders/utils.py

````python
import hashlib
from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def deduplication_key(*parts: object) -> str:
    canonical = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(canonical.encode()).hexdigest()


def job_id(reminder_id: int) -> str:
    return f"reminder:{reminder_id}"


def sanitize_failure(error: Exception) -> str:
    """Keep only exception type; SDK text can contain API URLs or message content."""
    return type(error).__name__[:120]
````

### C:/Users/USER/Documents/Agent/app/modules/reminders/__init__.py

````python
"""Persistent reminder domain and scheduler infrastructure."""
````


