# Stage 1 Step 5 - Implementation Review and Complete Files

Repository: C:/Users/USER/Documents/Agent

## Verification

- Baseline before changes: 112 tests passed.
- Final full regression: 181 tests passed (112 previous cases plus 69 new), pytest -v.
- Existing tests retained; exact AuditAction enum expectation extended for five new events.
- PASS: python -m compileall app tests migrations scripts.
- PASS: python -m pip check, no broken requirements.
- PASS: python -m ruff check .
- PASS: alembic upgrade head --sql and downgrade 0002:0001 --sql.
- PASS: live HTTP on http://127.0.0.1:8001: root 200, health 200 degraded, live 200 alive, ready 200 ready.
- PASS: unconfigured OAuth start returns safe HTTP 400.
- BLOCKED: live PostgreSQL and migration application; DATABASE_URL unset.
- BLOCKED: Google OAuth/API; client ID, client secret, redirect URI and encryption key unset.
- BLOCKED: live Telegram/combined run; bot token and owner unset, existing PIN configuration also required.
- BLOCKED: live Redis; REDIS_URL unset. Fake Redis is not live verification.
- BLOCKED: full live runtime.
- No real Google events were read, created, updated or deleted.
- API remains on loopback port 8001; the earlier Step 4 server occupied port 8000.

## Architecture

CalendarRuntime borrows existing database, Redis and security resources and owns one HTTPX client. ApplicationContext supplies the same instance to HTTP and Telegram. The async REST adapter uses official google-auth for refresh and google-auth-oauthlib for OAuth/PKCE; no synchronous discovery/httplib2 dependency was necessary. Imports do not connect.

Schemas/time utilities, low-level client, CalendarService, credential repository/store, OAuth and single-use CalendarActions have separate responsibilities. Telegram routing/presentation and deterministic FSM live in separate files. No AI executes actions.

## Security Decisions

Only AES-256-GCM encrypted refresh tokens are persisted. A versioned random-nonce envelope binds owner/provider through authenticated associated data. Access tokens/expiry remain in memory. Refresh rotation uses compare-and-swap so a delayed refresh cannot recreate deleted credentials. Key generation writes into ignored .env without printing; it was not run during this verification.

Owner-only middleware and locked-session rules cover all Calendar commands. OAuth uses a one-time owner-issued start link, expiring secure random state, browser cookie binding and PKCE. Both start and callback require unlocked state. Explicit memory storage is single-process development only. Separate processes need Redis for both security and OAuth state. No silent fallback.

OAuth callbacks do not echo codes/state or raw exceptions. Uvicorn access logs are disabled. Proxy logs must be configured separately in a later deployment stage. Redis contains only expiring OAuth/action coordination data, not Google access/refresh tokens.

Confirmations are consumed before external writes and FSM state is invalidated. Update/delete refetch the exact event and use ETag/If-Match. Field masks preserve unrelated provider fields/default reminders. Creation supplies a unique Google-compatible ID. No automatic retries of writes. Audit runs in a separate best-effort transaction after provider success.

## Migration

New revision 0002 creates google_credentials: owner FK, unique owner/provider, encrypted BYTEA payload and UTC timestamps. Downgrade drops that table. Initial revision 0001 was unchanged. Offline SQL and SQLite repository tests do not prove live PostgreSQL execution.

## Limits and Blockers

Only Step 5 was implemented. Recurring/all-day listing is supported, but their creation/update/deletion is intentionally unsupported. Free/busy uses local aware ranges and clips/merges busy intervals. Daily output is capped at 50; upcoming at ten.

Network failures may leave uncertain outcomes: inspect /upcoming before starting a new create flow. Disconnect deletes local credentials even if remote revocation fails and warns the owner to remove the Google grant manually. Concurrent connect/disconnect flows, distributed operation fencing and a durable outbox are not implemented.

Health retains Step 4 infrastructure semantics and does not call Google. /google_status indicates stored credential presence, not live connectivity. Basic app startup permits missing integrations; OAuth/Calendar operations validate their requirements.

Google settings, encryption key, PostgreSQL, Redis and Telegram settings are not configured. No live Google success or applied DB migration is claimed.

## Setup and Next Step

README Step 5 includes PowerShell-first setup, Google Cloud project/API/consent/client instructions, redirect URI, key helper, migrations, run modes and all Telegram flows. Official Google OAuth, scopes and event documentation links are included there. Do not commit or send credentials.

Next: Stage 1 Step 6 - reminder engine, scheduled Telegram notifications, Calendar reminder synchronization and persistent reminder jobs. Not implemented.

## Changed/Created Files

- C:/Users/USER/Documents/Agent/.env.example
- C:/Users/USER/Documents/Agent/.gitignore
- C:/Users/USER/Documents/Agent/pyproject.toml
- C:/Users/USER/Documents/Agent/README.md
- C:/Users/USER/Documents/Agent/app/core/config.py
- C:/Users/USER/Documents/Agent/app/core/encryption.py
- C:/Users/USER/Documents/Agent/app/core/application.py
- C:/Users/USER/Documents/Agent/app/core/logging.py
- C:/Users/USER/Documents/Agent/app/database/models/__init__.py
- C:/Users/USER/Documents/Agent/app/database/models/google_credential.py
- C:/Users/USER/Documents/Agent/app/modules/audit/actions.py
- C:/Users/USER/Documents/Agent/app/bot/context.py
- C:/Users/USER/Documents/Agent/app/bot/constants.py
- C:/Users/USER/Documents/Agent/app/bot/dispatcher.py
- C:/Users/USER/Documents/Agent/app/bot/lifecycle.py
- C:/Users/USER/Documents/Agent/app/bot/handlers/calendar.py
- C:/Users/USER/Documents/Agent/app/bot/handlers/calendar_flow.py
- C:/Users/USER/Documents/Agent/app/bot/keyboards/calendar.py
- C:/Users/USER/Documents/Agent/app/api/app.py
- C:/Users/USER/Documents/Agent/app/api/routes/google_oauth.py
- C:/Users/USER/Documents/Agent/migrations/versions/0002_google_calendar_credentials.py
- C:/Users/USER/Documents/Agent/scripts/generate_encryption_key.py
- C:/Users/USER/Documents/Agent/tests/test_audit_service.py
- C:/Users/USER/Documents/Agent/tests/test_calendar_domain.py
- C:/Users/USER/Documents/Agent/tests/test_calendar_client.py
- C:/Users/USER/Documents/Agent/tests/test_google_credentials.py
- C:/Users/USER/Documents/Agent/tests/test_google_oauth.py
- C:/Users/USER/Documents/Agent/tests/bot/test_calendar_handlers.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/actions.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/audit.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/auth.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/client.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/credentials.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/exceptions.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/oauth.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/repository.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/runtime.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/schemas.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/service.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/state.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/utils.py
- C:/Users/USER/Documents/Agent/app/modules/calendar/__init__.py
- C:/Users/USER/Documents/Agent/STEP5_REVIEW.md (this report)

## Complete Final Contents

All implementation/documentation files follow in full. This report is not recursively embedded.

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

### C:/Users/USER/Documents/Agent/.gitignore

````text
node_modules/
.env
.env.*
!.env.example
.venv/
venv/
env/
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.mypy_cache/
.ruff_cache/
.pyright/
.coverage
.coverage.*
htmlcov/
coverage.xml
.idea/
.vscode/
*.log
Thumbs.db
dist/
build/
*.egg-info/
npm-debug.log*
.DS_Store
.google-credentials/
client_secret*.json
credentials*.json
token*.json
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
task system, Docker or reminder scheduler was added. OAuth memory mode is single
process; it is not a deployment configuration. Full distributed OAuth/credential
operation fencing and a durable outbox are not implemented.

Next: **Stage 1 - Step 6**, reminder engine, scheduled Telegram notifications,
Calendar reminder synchronization and persistent reminder jobs. Not implemented yet.
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

### C:/Users/USER/Documents/Agent/app/core/encryption.py

````python
"""Versioned AES-256-GCM envelopes bound to the credential owner/provider."""

import base64
import binascii
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr

from app.modules.calendar.exceptions import CalendarConfigurationError


class CredentialEncryption:
    def __init__(self, key: SecretStr | None) -> None:
        try:
            raw = (
                base64.b64decode(key.get_secret_value(), altchars=b"-_", validate=True)
                if key
                else b""
            )
            if len(raw) != 32:
                raise ValueError
        except (ValueError, binascii.Error):
            raise CalendarConfigurationError(
                "DATA_ENCRYPTION_KEY must be a Base64-encoded 32-byte key."
            ) from None
        self._cipher = AESGCM(raw)

    def encrypt(self, value: str, owner: int) -> bytes:
        nonce = secrets.token_bytes(12)
        return (
            b"\x01"
            + nonce
            + self._cipher.encrypt(nonce, value.encode(), f"google_calendar:{owner}:v1".encode())
        )

    def decrypt(self, value: bytes, owner: int) -> str:
        try:
            if value[:1] != b"\x01":
                raise ValueError
            return self._cipher.decrypt(
                value[1:13], value[13:], f"google_calendar:{owner}:v1".encode()
            ).decode()
        except (InvalidTag, ValueError, UnicodeError):
            raise CalendarConfigurationError(
                "Stored Google credential cannot be decrypted."
            ) from None
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
        self.calendar: CalendarRuntime | None = None
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
    # OAuth callbacks carry authorization codes in query strings, including under CLI Uvicorn.
    logging.getLogger("uvicorn.access").disabled = True
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

### C:/Users/USER/Documents/Agent/app/database/models/__init__.py

````python
"""Import all mapped models so migrations discover complete metadata."""

from app.database.models.audit_log import AuditLog
from app.database.models.google_credential import GoogleCredential
from app.database.models.user import User

__all__ = ["AuditLog", "GoogleCredential", "User"]
````

### C:/Users/USER/Documents/Agent/app/database/models/google_credential.py

````python
from sqlalchemy import BigInteger, ForeignKey, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class GoogleCredential(TimestampMixin, Base):
    """Persist only the encrypted refresh token; access tokens remain in memory."""

    __tablename__ = "google_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_google_credentials_owner_provider"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(32), default="google_calendar")
    refresh_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
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

### C:/Users/USER/Documents/Agent/app/bot/context.py

````python
from dataclasses import dataclass

from app.bot.persistence import BotPersistence
from app.modules.calendar.runtime import CalendarRuntime
from app.modules.security.service import SecurityService


@dataclass(repr=False)
class BotContext:
    owner_id: int
    timezone: str
    security: SecurityService
    persistence: BotPersistence
    calendar: CalendarRuntime | None = None
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

### C:/Users/USER/Documents/Agent/app/bot/dispatcher.py

````python
from aiogram import Dispatcher
from aiogram.fsm.storage.base import BaseEventIsolation, BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation

from app.bot.context import BotContext
from app.bot.errors import SafeErrorMiddleware
from app.bot.handlers import calendar, common, menu, security
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
        calendar.create_router(),
        menu.create_router(),
    )
    return dispatcher
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

### C:/Users/USER/Documents/Agent/app/bot/handlers/calendar.py

````python
"""Telegram presentation/FSM only. Provider operations live behind CalendarActions."""

import logging
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.context import BotContext
from app.bot.handlers.calendar_flow import CalendarFlow, add, input_step, reset, runtime, show
from app.bot.keyboards.calendar import confirmation
from app.modules.calendar.exceptions import CalendarConfigurationError, CalendarError
from app.modules.calendar.schemas import TimeInterval
from app.modules.calendar.utils import event_label, parse_local


async def calendar_menu(message: Message, app_context: BotContext) -> None:
    if app_context.calendar is None and message.text == "📅 Calendar":
        from app.bot.constants import PLACEHOLDER

        await show(message, PLACEHOLDER)
        return
    calendar = runtime(app_context)
    try:
        connected = await calendar.store.load()
    except CalendarConfigurationError:
        connected = None
    text = (
        "Google Calendar: Connected"
        if connected
        else "Google Calendar hali ulanmagan. /google_connect orqali ulang."
    )
    await show(
        message,
        text + f"\nCalendar: {calendar.settings.google_calendar_id}\n"
        f"Timezone: {app_context.timezone}\n/today /tomorrow /upcoming\n"
        "/event_add /event_update /event_delete\n/free DD.MM.YYYY HH:MM HH:MM\n"
        "/google_connect /google_status /google_disconnect /cancel",
    )


async def connect(message: Message, app_context: BotContext) -> None:
    url = await runtime(app_context).oauth.connect_url()
    await show(message, "Google Calendar ulash (10 daqiqa):\n" + url, disable_web_page_preview=True)


async def events(message: Message, app_context: BotContext) -> None:
    calendar = runtime(app_context)
    command = (message.text or "").split()[0].split("@")[0]
    if command == "/today":
        items = await calendar.service.get_today_events()
    elif command == "/tomorrow":
        items = await calendar.service.get_tomorrow_events()
    else:
        items = await calendar.service.list_upcoming_events()
    if not items:
        await show(message, "Calendar'da reja yo'q.")
    for offset in range(0, len(items), 10):
        await show(
            message,
            "\n".join(
                event_label(item, calendar.settings.timezone)
                for item in items[offset : offset + 10]
            ),
        )


async def free(message: Message, app_context: BotContext) -> None:
    calendar = runtime(app_context)
    try:
        _, day, start, end = (message.text or "").split()
        window = TimeInterval(
            start=parse_local(day, start, calendar.settings.timezone),
            end=parse_local(day, end, calendar.settings.timezone),
        )
    except ValueError:
        await show(message, "Format: /free DD.MM.YYYY HH:MM HH:MM")
        return
    result = await calendar.service.get_free_busy(window)
    await show(
        message,
        "Bo'sh vaqt:\n"
        + (
            "\n".join(
                f"{item.start.astimezone(calendar.settings.timezone):%H:%M}-{item.end.astimezone(calendar.settings.timezone):%H:%M}"
                for item in result.free
            )
            or "Bo'sh vaqt yo'q."
        ),
    )


async def cancel(message: Message, state: FSMContext, app_context: BotContext) -> None:
    data = await state.get_data()
    if data.get("action"):
        await runtime(app_context).actions.cancel(data["action"])
    await state.clear()
    await show(message, "Bekor qilindi.")


async def select(message: Message, state: FSMContext, app_context: BotContext) -> None:
    calendar = runtime(app_context)
    await reset(state, calendar)
    events = await calendar.service.list_upcoming_events()
    if not events:
        await show(message, "Calendar'da reja yo'q.")
        return
    kind = "delete" if (message.text or "").startswith("/event_delete") else "update"
    await state.set_data({"kind": kind, "events": [event.id for event in events]})
    await state.set_state(CalendarFlow.select)
    await show(
        message,
        "Event raqamini kiriting:\n"
        + "\n".join(
            f"{index}. {event_label(event, calendar.settings.timezone)}"
            for index, event in enumerate(events, 1)
        ),
    )


async def disconnect(message: Message, state: FSMContext, app_context: BotContext) -> None:
    calendar = runtime(app_context)
    await reset(state, calendar)
    token = await calendar.actions.prepare("disconnect", {})
    await state.set_data({"action": token})
    await state.set_state(CalendarFlow.confirm)
    await show(message, "Google Calendar ulanishi uzilsinmi?", reply_markup=confirmation(token))


async def confirmed(callback: CallbackQuery, state: FSMContext, app_context: BotContext) -> None:
    calendar = runtime(app_context)
    _, decision, token = (callback.data or "").split(":", 2)
    data = await state.get_data()
    if await state.get_state() != CalendarFlow.confirm.state or data.get("action") != token:
        await callback.answer("Tasdiq eskirgan.")
        return
    await state.clear()
    await callback.answer()
    if decision == "yes":
        text = await calendar.actions.confirm(token)
    else:
        await calendar.actions.cancel(token)
        text = "Bekor qilindi."
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramAPIError:
            logging.getLogger(__name__).warning("calendar_confirmation_markup_not_removed")
        await show(callback.message, text)


class CalendarErrorMiddleware:
    async def __call__(self, handler: Any, event: Any, data: dict[str, Any]) -> Any:
        try:
            return await handler(event, data)
        except CalendarError as error:
            if isinstance(event, CallbackQuery):
                if isinstance(event.message, Message):
                    await show(event.message, str(error))
                else:
                    await event.answer(str(error)[:180])
            else:
                await show(event, str(error))
            return None


def create_router() -> Router:
    router = Router(name="calendar")
    router.message.middleware(CalendarErrorMiddleware())
    router.callback_query.middleware(CalendarErrorMiddleware())
    router.message.register(calendar_menu, Command("calendar", "google_status"))
    router.message.register(calendar_menu, F.text == "📅 Calendar")
    router.message.register(connect, Command("google_connect"))
    router.message.register(events, Command("today", "tomorrow", "upcoming"))
    router.message.register(free, Command("free"))
    router.message.register(add, Command("event_add"))
    router.message.register(select, Command("event_update", "event_delete"))
    router.message.register(disconnect, Command("google_disconnect"))
    router.message.register(cancel, Command("cancel"))
    router.message.register(
        input_step,
        F.text & ~F.text.startswith("/"),
        StateFilter(
            CalendarFlow.title,
            CalendarFlow.date,
            CalendarFlow.time,
            CalendarFlow.duration,
            CalendarFlow.reminders,
            CalendarFlow.select,
            CalendarFlow.field,
            CalendarFlow.edit,
        ),
    )
    router.callback_query.register(confirmed, F.data.regexp(r"^cal:(yes|no):[A-Za-z0-9_-]{32}$"))
    return router
````

### C:/Users/USER/Documents/Agent/app/bot/handlers/calendar_flow.py

````python
"""Telegram presentation/FSM only. Provider operations live behind CalendarActions."""

from datetime import timedelta
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from pydantic import ValidationError

from app.bot.context import BotContext
from app.bot.keyboards.calendar import confirmation
from app.modules.calendar.exceptions import CalendarError
from app.modules.calendar.runtime import CalendarRuntime
from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventView
from app.modules.calendar.utils import event_label, parse_local


class CalendarFlow(StatesGroup):
    title = State()
    date = State()
    time = State()
    duration = State()
    reminders = State()
    select = State()
    field = State()
    edit = State()
    confirm = State()


def runtime(context: BotContext) -> CalendarRuntime:
    if context.calendar is None:
        raise CalendarError("Calendar is not available.")
    return context.calendar


async def show(message: Message, text: str, **kwargs: Any) -> None:
    for offset in range(0, len(text), 3500):
        await message.answer(text[offset : offset + 3500], parse_mode=None, **kwargs)


async def reset(state: FSMContext, calendar: CalendarRuntime) -> None:
    data = await state.get_data()
    if data.get("action"):
        await calendar.actions.cancel(data["action"])
    await state.clear()


async def add(message: Message, state: FSMContext, app_context: BotContext) -> None:
    await reset(state, runtime(app_context))
    await state.set_state(CalendarFlow.title)
    await show(message, "Event nomini kiriting. Bekor qilish: /cancel")


async def preview(
    message: Message,
    state: FSMContext,
    calendar: CalendarRuntime,
    kind: str,
    event: CalendarEventCreate,
    identifier: dict[str, str] | None = None,
) -> None:
    payload = event.model_dump(mode="json")
    if identifier:
        payload["fields"] = {
            "title": ["title"],
            "time": ["start", "end"],
            "reminder": ["reminders"],
        }[identifier["field"]]
    token = await calendar.actions.prepare(
        kind, {**identifier, "event": payload} if identifier else payload
    )
    await state.set_data({"action": token})
    await state.set_state(CalendarFlow.confirm)
    reminders = (
        "unchanged" if identifier and identifier["field"] != "reminder" else str(event.reminders)
    )
    start = event.start.astimezone(calendar.settings.timezone)
    end = event.end.astimezone(calendar.settings.timezone)
    await show(
        message,
        f"{event.title}\n{start:%d.%m.%Y %H:%M} - {end:%d.%m.%Y %H:%M}\n"
        f"Reminder (daqiqa): {reminders}\nCalendar'ga saqlansinmi?",
        reply_markup=confirmation(token),
    )


async def input_step(message: Message, state: FSMContext, app_context: BotContext) -> None:
    calendar = runtime(app_context)
    text = (message.text or "").strip()
    current, data = await state.get_state(), await state.get_data()
    try:
        if current == CalendarFlow.title.state:
            if not 1 <= len(text) <= 200:
                raise ValueError
            await state.update_data(title=text)
            await state.set_state(CalendarFlow.date)
            await show(message, "Sana: DD.MM.YYYY")
        elif current == CalendarFlow.date.state:
            parse_local(text, "00:00", calendar.settings.timezone)
            await state.update_data(day=text)
            await state.set_state(CalendarFlow.time)
            await show(message, "Boshlanish vaqti: HH:MM")
        elif current == CalendarFlow.time.state:
            start = parse_local(data["day"], text, calendar.settings.timezone)
            await state.update_data(start=start.isoformat())
            await state.set_state(CalendarFlow.duration)
            await show(
                message,
                f"Davomiylik daqiqada (1-1440); default uchun '-': {calendar.settings.calendar_default_event_duration_minutes}",
            )
        elif current == CalendarFlow.duration.state:
            duration = (
                calendar.settings.calendar_default_event_duration_minutes
                if text == "-"
                else int(text)
            )
            if not 1 <= duration <= 1440:
                raise ValueError
            await state.update_data(duration=duration)
            await state.set_state(CalendarFlow.reminders)
            await show(message, "Reminder: 10 yoki 1440,60,10. Default: '-'. O'chirish: none")
        elif current == CalendarFlow.reminders.state:
            from datetime import datetime

            start = datetime.fromisoformat(data["start"])
            event = CalendarEventCreate(
                title=data["title"],
                start=start,
                end=start + timedelta(minutes=data["duration"]),
                reminders=parse_reminders(text),
            )
            await preview(message, state, calendar, "create", event)
        elif current == CalendarFlow.select.state:
            index = int(text) - 1
            if index < 0 or index >= len(data["events"]):
                raise ValueError
            event = await calendar.service.get_event(data["events"][index])
            await calendar.service.mutable_event(event.id, event.etag)
            if data["kind"] == "delete":
                token = await calendar.actions.prepare(
                    "delete", {"id": event.id, "etag": event.etag}
                )
                await state.set_data({"action": token})
                await state.set_state(CalendarFlow.confirm)
                await show(
                    message,
                    event_label(event, calendar.settings.timezone) + "\nO'chirilsinmi?",
                    reply_markup=confirmation(token),
                )
            else:
                await state.update_data(event=event.model_dump(mode="json"))
                await state.set_state(CalendarFlow.field)
                await show(message, "Nimani o'zgartiramiz? title / time / reminder")
        elif current == CalendarFlow.field.state:
            if text not in {"title", "time", "reminder"}:
                raise ValueError
            await state.update_data(field=text)
            await state.set_state(CalendarFlow.edit)
            await show(
                message,
                {
                    "title": "Yangi nom:",
                    "time": "DD.MM.YYYY HH:MM duration_minutes",
                    "reminder": "10 yoki 1440,60,10; none",
                }[text],
            )
        elif current == CalendarFlow.edit.state:
            existing = CalendarEventView.model_validate(data["event"])
            values = existing.model_dump(
                include={"title", "start", "end", "description", "location", "reminders"}
            )
            if data["field"] == "title":
                values["title"] = text
            elif data["field"] == "reminder":
                values["reminders"] = parse_reminders(text)
            else:
                day, clock, duration_text = text.split()
                duration = int(duration_text)
                if not 1 <= duration <= 1440:
                    raise ValueError
                values["start"] = parse_local(day, clock, calendar.settings.timezone)
                values["end"] = values["start"] + timedelta(minutes=duration)
            await preview(
                message,
                state,
                calendar,
                "update",
                CalendarEventCreate.model_validate(values),
                {"id": existing.id, "etag": existing.etag, "field": data["field"]},
            )
    except (ValueError, ValidationError):
        await show(message, "Format yoki qiymat noto'g'ri. Qayta kiriting yoki /cancel.")


def parse_reminders(text: str) -> list[int]:
    if text == "none":
        return []
    return [10] if text == "-" else [int(value.strip()) for value in text.split(",")]
````

### C:/Users/USER/Documents/Agent/app/bot/keyboards/calendar.py

````python
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirmation(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Tasdiqlash", callback_data=f"cal:yes:{token}"),
                InlineKeyboardButton(text="Bekor qilish", callback_data=f"cal:no:{token}"),
            ]
        ]
    )
````

### C:/Users/USER/Documents/Agent/app/api/app.py

````python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import google_oauth, health, root
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
    app.include_router(google_oauth.router)
    return app
````

### C:/Users/USER/Documents/Agent/app/api/routes/google_oauth.py

````python
import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.api.dependencies import application_context
from app.core.application import ApplicationContext
from app.core.logging import report_error
from app.modules.calendar.exceptions import CalendarError

router = APIRouter(prefix="/oauth/google")
Context = Annotated[ApplicationContext, Depends(application_context)]
HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


@router.get("/start", response_model=None)
async def start(context: Context, ticket: str = "") -> PlainTextResponse | RedirectResponse:
    assert context.calendar is not None
    if not 20 <= len(ticket) <= 128:
        return PlainTextResponse("Invalid connection link.", status_code=400, headers=HEADERS)
    browser = secrets.token_urlsafe(32)
    try:
        url = await context.calendar.oauth.begin(ticket, browser)
    except CalendarError as error:
        return PlainTextResponse(str(error), status_code=400, headers=HEADERS)
    except Exception as error:  # noqa: BLE001 - public OAuth boundary never renders backend errors
        report_error(logging.getLogger(__name__), error)
        return PlainTextResponse(
            "Connection unavailable. Try again later.", status_code=503, headers=HEADERS
        )
    response = RedirectResponse(url, status_code=303, headers=HEADERS)
    response.set_cookie(
        "calendar_oauth",
        browser,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=(context.settings.google_redirect_uri or "").startswith("https:"),
        path="/oauth/google",
    )
    return response


@router.get("/callback")
async def callback(
    request: Request, context: Context, state: str = "", code: str = ""
) -> PlainTextResponse:
    assert context.calendar is not None
    if not 20 <= len(state) <= 128 or len(code) > 4096:
        return PlainTextResponse("Invalid OAuth callback.", status_code=400, headers=HEADERS)
    try:
        await context.calendar.oauth.callback(
            state, code, request.cookies.get("calendar_oauth", "")
        )
        response = PlainTextResponse(
            "Google Calendar connected. You may return to Telegram.", headers=HEADERS
        )
    except CalendarError as error:
        response = PlainTextResponse(str(error), status_code=400, headers=HEADERS)
    except Exception as error:  # noqa: BLE001 - public OAuth boundary never renders backend errors
        report_error(logging.getLogger(__name__), error)
        response = PlainTextResponse(
            "Connection unavailable. Use /google_connect again.", status_code=503, headers=HEADERS
        )
    response.delete_cookie("calendar_oauth", path="/oauth/google")
    return response
````

### C:/Users/USER/Documents/Agent/migrations/versions/0002_google_calendar_credentials.py

````python
"""Encrypted owner Calendar refresh credentials; no access token persistence."""

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "google_credentials",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("refresh_token_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "provider", name="uq_google_credentials_owner_provider"),
    )


def downgrade() -> None:
    op.drop_table("google_credentials")
````

### C:/Users/USER/Documents/Agent/scripts/generate_encryption_key.py

````python
"""Write a new encryption key to the ignored .env without printing it."""

import base64
import os
import secrets
from pathlib import Path

from dotenv import dotenv_values, set_key


def main() -> None:
    path = Path(__file__).resolve().parents[1] / ".env"
    if not path.is_file():
        raise SystemExit("Create .env from .env.example first.")
    if dotenv_values(path).get("DATA_ENCRYPTION_KEY"):
        raise SystemExit("DATA_ENCRYPTION_KEY already exists; refusing to replace it.")
    value = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    set_key(str(path), "DATA_ENCRYPTION_KEY", value, quote_mode="always")
    if os.name != "nt":
        path.chmod(0o600)
    print("Encryption key written to .env. Back it up securely; it was not printed.")


if __name__ == "__main__":
    main()
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

### C:/Users/USER/Documents/Agent/tests/test_calendar_domain.py

````python
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.modules.audit.actions import AuditAction
from app.modules.calendar.exceptions import CalendarConflictError, CalendarError
from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventUpdate, TimeInterval
from app.modules.calendar.service import CalendarService
from app.modules.calendar.utils import day_range, event_view, free_intervals, parse_local

TZ = ZoneInfo("Asia/Tashkent")


def event(**overrides: object) -> CalendarEventCreate:
    values = {
        "title": "Meeting",
        "start": "2026-09-25T15:00:00+05:00",
        "end": "2026-09-25T16:00:00+05:00",
    }
    return CalendarEventCreate.model_validate({**values, **overrides})


def raw_event() -> dict:
    return {
        "id": "abc123",
        "etag": '"v1"',
        "summary": "Meeting",
        "start": {"dateTime": "2026-09-25T15:00:00+05:00"},
        "end": {"dateTime": "2026-09-25T16:00:00+05:00"},
    }


def test_defaults_and_payload() -> None:
    service = CalendarService(Mock(), Mock(), TZ)
    payload = service.payload(event())
    assert payload["start"] == {
        "dateTime": "2026-09-25T15:00:00+05:00",
        "timeZone": "Asia/Tashkent",
    }
    assert payload["reminders"] == {
        "useDefault": False,
        "overrides": [{"method": "popup", "minutes": 10}],
    }
    assert event(reminders=[1440, 60, 10]).reminders == [1440, 60, 10]


@pytest.mark.parametrize("values", [[0], [-1], [40321], [10, 10], [1, 2, 3, 4, 5, 6], [True]])
def test_reminders_rejected(values: list[int]) -> None:
    with pytest.raises(ValidationError):
        event(reminders=values)


def test_naive_and_reversed_rejected() -> None:
    with pytest.raises(ValidationError):
        event(start="2026-09-25T15:00:00")
    with pytest.raises(ValidationError):
        event(end="2026-09-25T14:00:00+05:00")


def test_local_boundaries_and_all_day() -> None:
    window = day_range(date(2026, 9, 25), TZ)
    assert window.start.isoformat() == "2026-09-25T00:00:00+05:00"
    assert window.end.isoformat() == "2026-09-26T00:00:00+05:00"
    item = event_view({"id": "all", "start": {"date": "2026-09-25"}, "end": {"date": "2026-09-26"}})
    assert item.all_day and item.start == date(2026, 9, 25)


def interval(start: int, end: int) -> TimeInterval:
    return TimeInterval(
        start=datetime(2026, 9, 25, start, tzinfo=TZ), end=datetime(2026, 9, 25, end, tzinfo=TZ)
    )


@pytest.mark.parametrize(
    ("busy", "expected"),
    [
        ([], [(9, 18)]),
        ([(10, 11)], [(9, 10), (11, 18)]),
        ([(10, 12), (11, 14)], [(9, 10), (14, 18)]),
        ([(10, 12), (12, 14)], [(9, 10), (14, 18)]),
        ([(0, 23)], []),
        ([(9, 18)], []),
        ([(7, 10), (17, 22)], [(10, 17)]),
    ],
)
def test_free_intervals(busy: list, expected: list) -> None:
    result = free_intervals(interval(9, 18), [interval(*pair) for pair in busy])
    assert [(item.start.hour, item.end.hour) for item in result] == expected


def test_dst_invalid_time_rejected() -> None:
    with pytest.raises(ValueError):
        parse_local("08.03.2026", "02:30", ZoneInfo("America/New_York"))


async def test_create_audits_safe_identifier() -> None:
    client, audit = Mock(), Mock()
    client.create_event = AsyncMock(return_value=raw_event())
    audit.record = AsyncMock()
    service = CalendarService(client, audit, TZ)
    created = await service.create_event(event(), "a" * 32)
    assert created.id == "abc123"
    assert client.create_event.call_args.args[0]["id"] == "a" * 32
    audit.record.assert_awaited_once_with(AuditAction.CALENDAR_EVENT_CREATED, "abc123")
    assert "token" not in str(audit.record.call_args)


async def test_today_tomorrow_and_upcoming_sorted(monkeypatch: pytest.MonkeyPatch) -> None:
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 25, 1, tzinfo=TZ).astimezone(tz)

    monkeypatch.setattr("app.modules.calendar.service.datetime", FixedDateTime)
    client = Mock()
    client.list_events = AsyncMock(return_value=[])
    service = CalendarService(client, Mock(), TZ)
    await service.get_today_events()
    assert client.list_events.call_args.args[:2] == (
        "2026-09-25T00:00:00+05:00",
        "2026-09-26T00:00:00+05:00",
    )
    await service.get_tomorrow_events()
    assert client.list_events.call_args.args[:2] == (
        "2026-09-26T00:00:00+05:00",
        "2026-09-27T00:00:00+05:00",
    )
    early = {**raw_event(), "id": "early", "start": {"dateTime": "2026-09-25T09:00:00+05:00"}}
    client.list_events.return_value = [raw_event(), early]
    assert [item.id for item in await service.list_upcoming_events()] == ["early", "abc123"]


async def test_update_refetches_and_only_changes_selected_fields() -> None:
    client = Mock(
        get_event=AsyncMock(return_value=raw_event()),
        update_event=AsyncMock(return_value=raw_event()),
    )
    audit = Mock(record=AsyncMock())
    service = CalendarService(client, audit, TZ)
    update = CalendarEventUpdate(**event().model_dump(), fields={"title"})
    await service.update_event("abc123", update, '"v1"')
    client.get_event.assert_awaited_once_with("abc123")
    client.update_event.assert_awaited_once_with("abc123", {"summary": "Meeting"}, '"v1"')
    audit.record.assert_awaited_once_with(AuditAction.CALENDAR_EVENT_UPDATED, "abc123")


async def test_stale_delete_and_recurring_changes_are_rejected() -> None:
    client = Mock(get_event=AsyncMock(return_value=raw_event()), delete_event=AsyncMock())
    service = CalendarService(client, Mock(record=AsyncMock()), TZ)
    with pytest.raises(CalendarConflictError):
        await service.delete_event("abc123", '"stale"')
    client.delete_event.assert_not_called()
    client.get_event.return_value = {**raw_event(), "recurringEventId": "series"}
    with pytest.raises(CalendarError):
        await service.delete_event("abc123", '"v1"')
    client.delete_event.assert_not_called()


async def test_free_busy_missing_calendar_is_not_fake_free_time() -> None:
    client = Mock(calendar_id="primary", free_busy=AsyncMock(return_value={"calendars": {}}))
    service = CalendarService(client, Mock(), TZ)
    with pytest.raises(CalendarError):
        await service.get_free_busy(interval(9, 18))
````

### C:/Users/USER/Documents/Agent/tests/test_calendar_client.py

````python
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.modules.calendar.client import GoogleCalendarClient
from app.modules.calendar.exceptions import (
    CalendarConflictError,
    CalendarEventNotFoundError,
    GoogleCalendarAuthenticationError,
    GoogleCalendarPermissionError,
    GoogleCalendarUnavailableError,
)


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, GoogleCalendarAuthenticationError),
        (403, GoogleCalendarPermissionError),
        (404, CalendarEventNotFoundError),
        (429, GoogleCalendarUnavailableError),
        (503, GoogleCalendarUnavailableError),
        (412, CalendarConflictError),
    ],
)
async def test_safe_error_mapping(status, error) -> None:
    token = Mock(access_token=AsyncMock(return_value="private-access"))
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, json={"error": {"message": "secret-data"}})
        )
    ) as http:
        client = GoogleCalendarClient(http, token, "primary")
        with pytest.raises(error) as caught:
            await client.get_event("abc")
        assert "secret-data" not in str(caught.value)
        assert "private-access" not in str(caught.value)


async def test_insert_payload_and_patch_precondition() -> None:
    requests = []

    def reply(request):
        requests.append(request)
        return httpx.Response(200, json={"id": "abc"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as http:
        client = GoogleCalendarClient(
            http, Mock(access_token=AsyncMock(return_value="test")), "primary"
        )
        await client.create_event({"summary": "Test"})
        assert requests[0].method == "POST" and b"Test" in requests[0].content
        await client.update_event("abc", {"summary": "Changed"}, '"v1"')
        assert requests[1].method == "PATCH"
        assert requests[1].headers["If-Match"] == '"v1"'
        await client.delete_event("abc", '"v1"')
        assert requests[2].headers["If-Match"] == '"v1"'


async def test_pagination_and_recurring_expansion() -> None:
    requests = []

    def reply(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "items": [{"id": str(len(requests))}],
                **({"nextPageToken": "next"} if len(requests) == 1 else {}),
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as http:
        client = GoogleCalendarClient(
            http, Mock(access_token=AsyncMock(return_value="test")), "primary"
        )
        assert len(await client.list_events("2026-09-25T00:00:00Z", None, 10)) == 2
    assert requests[0].url.params["singleEvents"] == "true"
    assert requests[0].url.params["orderBy"] == "startTime"
    assert requests[1].url.params["pageToken"] == "next"
````

### C:/Users/USER/Documents/Agent/tests/test_google_credentials.py

````python
import base64
import secrets
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.encryption import CredentialEncryption
from app.database.models import GoogleCredential
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.calendar.audit import CalendarAudit
from app.modules.calendar.credentials import GoogleCredentialStore
from app.modules.calendar.exceptions import CalendarConfigurationError
from app.modules.calendar.repository import GoogleCredentialRepository
from app.modules.users.repository import UserRepository


def key() -> SecretStr:
    return SecretStr(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())


def test_encryption_binding_and_no_plaintext() -> None:
    encryption = CredentialEncryption(key())
    envelope = encryption.encrypt("private-refresh", 42)
    assert b"private-refresh" not in envelope
    assert encryption.decrypt(envelope, 42) == "private-refresh"
    assert encryption.encrypt("private-refresh", 42) != envelope
    with pytest.raises(CalendarConfigurationError):
        encryption.decrypt(envelope, 43)
    with pytest.raises(CalendarConfigurationError):
        encryption.decrypt(envelope[:-1] + bytes([envelope[-1] ^ 1]), 42)
    with pytest.raises(CalendarConfigurationError):
        CredentialEncryption(SecretStr("invalid"))


async def test_repository_save_load_delete(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    repository = GoogleCredentialRepository(session)
    await repository.save(user.id, b"encrypted-one")
    assert (await repository.load(user.id)).refresh_token_encrypted == b"encrypted-one"
    await repository.save(user.id, b"encrypted-two")
    assert (await repository.load(user.id)).refresh_token_encrypted == b"encrypted-two"
    await repository.delete(user.id)
    assert await repository.load(user.id) is None


async def test_credential_store_persists_only_ciphertext(engine) -> None:
    database = DatabaseManager(Settings(_env_file=None))
    database._sessions = async_sessionmaker(engine, expire_on_commit=False)
    store = GoogleCredentialStore(database, 42, key())
    await store.save(SecretStr("refresh-private"))
    assert (await store.load()).get_secret_value() == "refresh-private"
    async with database.session() as session:
        row = await session.scalar(select(GoogleCredential))
        assert b"refresh-private" not in row.refresh_token_encrypted
    await store.delete()
    assert await store.load() is None
    assert not await store.rotate(SecretStr("refresh-private"), SecretStr("new-refresh"))
    assert await store.load() is None


async def test_audit_failure_is_best_effort() -> None:
    database = Mock()
    database.session.side_effect = RuntimeError("secret-detail")
    await CalendarAudit(database, 42).record(AuditAction.CALENDAR_EVENT_CREATED, "abc")


async def test_token_refresh_cache_and_disconnect(monkeypatch) -> None:
    from datetime import UTC, datetime, timedelta

    from app.modules.calendar.auth import GoogleTokenProvider
    from app.modules.calendar.exceptions import GoogleCalendarAuthenticationError

    store = Mock()
    store.load = AsyncMock(return_value=SecretStr("refresh-private"))
    store.save = AsyncMock()
    provider = GoogleTokenProvider(
        Settings(_env_file=None, GOOGLE_CLIENT_ID="client", GOOGLE_CLIENT_SECRET="secret"), store
    )
    calls = []

    def refresh(credentials, request):
        calls.append(True)
        credentials.token = "access-private"
        credentials.expiry = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)

    monkeypatch.setattr("google.oauth2.credentials.Credentials.refresh", refresh)
    assert await provider.access_token() == "access-private"
    assert await provider.access_token() == "access-private"
    assert len(calls) == 1
    store.save.assert_not_called()  # access token is never persisted
    store.load.return_value = None
    with pytest.raises(GoogleCalendarAuthenticationError):
        await provider.access_token()


async def test_permanent_refresh_failure_not_repeated(monkeypatch) -> None:
    from google.auth.exceptions import RefreshError

    from app.modules.calendar.auth import GoogleTokenProvider
    from app.modules.calendar.exceptions import GoogleCalendarAuthenticationError

    store = Mock(load=AsyncMock(return_value=SecretStr("bad-refresh")))
    provider = GoogleTokenProvider(
        Settings(_env_file=None, GOOGLE_CLIENT_ID="client", GOOGLE_CLIENT_SECRET="secret"), store
    )
    refresh = Mock(side_effect=RefreshError("private-details"))
    monkeypatch.setattr("google.oauth2.credentials.Credentials.refresh", refresh)
    for _ in range(2):
        with pytest.raises(GoogleCalendarAuthenticationError):
            await provider.access_token()
    refresh.assert_called_once()
````

### C:/Users/USER/Documents/Agent/tests/test_google_oauth.py

````python
import asyncio
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fakeredis.aioredis import FakeRedis
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.calendar.actions import CalendarActions
from app.modules.calendar.exceptions import (
    CalendarConfigurationError,
    CalendarError,
    OAuthStateError,
)
from app.modules.calendar.oauth import GoogleOAuthService
from app.modules.calendar.state import MemoryTemporaryStore, RedisTemporaryStore
from app.modules.security.lock_service import LockService


def oauth(http: httpx.AsyncClient) -> GoogleOAuthService:
    settings = Settings(
        _env_file=None,
        GOOGLE_CLIENT_ID="test-client",
        GOOGLE_CLIENT_SECRET="test-secret",
        GOOGLE_REDIRECT_URI="http://127.0.0.1:8000/oauth/google/callback",
        TELEGRAM_OWNER_ID=42,
    )
    store = Mock(
        save=AsyncMock(), load=AsyncMock(return_value=SecretStr("refresh")), delete=AsyncMock()
    )
    return GoogleOAuthService(
        settings, store, MemoryTemporaryStore(), LockService(), Mock(record=AsyncMock()), http
    )


def test_optional_google_settings() -> None:
    settings = Settings(
        _env_file=None,
        GOOGLE_CLIENT_ID=None,
        GOOGLE_CLIENT_SECRET=None,
        GOOGLE_REDIRECT_URI=None,
        DATA_ENCRYPTION_KEY=None,
    )
    assert settings.app_timezone == "Asia/Tashkent"
    assert settings.google_client_id is None


async def test_missing_config_fails_only_on_oauth() -> None:
    async with httpx.AsyncClient() as http:
        service = oauth(http)
        service.settings.google_client_id = None
        with pytest.raises(CalendarConfigurationError):
            await service.connect_url()


async def test_oauth_state_pkce_browser_binding_and_replay() -> None:
    async with httpx.AsyncClient() as http:
        service = oauth(http)
        await service.lock.unlock()
        link = await service.connect_url()
        ticket = parse_qs(urlsplit(link).query)["ticket"][0]
        url = await service.begin(ticket, "browser-random")
        query = parse_qs(urlsplit(url).query)
        assert query["access_type"] == ["offline"]
        assert query["code_challenge_method"] == ["S256"]
        assert len(query["state"][0]) >= 32
        assert "test-secret" not in url
        service.exchange = AsyncMock(return_value=SecretStr("private-token"))
        await service.callback(query["state"][0], "fake-code", "browser-random")
        service.store.save.assert_awaited_once_with(SecretStr("private-token"))
        with pytest.raises(OAuthStateError):
            await service.callback(query["state"][0], "fake-code", "browser-random")
        with pytest.raises(OAuthStateError):
            await service.begin(ticket, "browser-random")


@pytest.mark.parametrize("scenario", ["invalid", "browser", "locked"])
async def test_oauth_rejects_invalid_callback(scenario) -> None:
    async with httpx.AsyncClient() as http:
        service = oauth(http)
        await service.lock.unlock()
        ticket = parse_qs(urlsplit(await service.connect_url()).query)["ticket"][0]
        state = parse_qs(urlsplit(await service.begin(ticket, "correct")).query)["state"][0]
        service.exchange = AsyncMock()
        if scenario == "locked":
            await service.lock.lock()
        with pytest.raises(OAuthStateError):
            await service.callback(
                "invalid" if scenario == "invalid" else state,
                "fake-code",
                "wrong" if scenario == "browser" else "correct",
            )
        service.exchange.assert_not_called()


async def test_state_expiry(monkeypatch) -> None:
    store = MemoryTemporaryStore()
    monkeypatch.setattr("app.modules.calendar.state.time.monotonic", lambda: 100)
    token = await store.issue("oauth", {"test": True}, ttl=600)
    monkeypatch.setattr("app.modules.calendar.state.time.monotonic", lambda: 701)
    assert await store.consume("oauth", token) is None


async def test_redis_state_single_use_and_ttl() -> None:
    async with FakeRedis(decode_responses=True) as redis:
        store = RedisTemporaryStore(redis, "test", 42)
        token = await store.issue("oauth", {"owner": 42})
        assert 0 < await redis.ttl(store.key("oauth", token)) <= 600
        values = await asyncio.gather(store.consume("oauth", token), store.consume("oauth", token))
        assert values.count(None) == 1
        assert {"owner": 42} in values


async def test_create_confirmation_single_use_and_delete() -> None:
    service = Mock(create_event=AsyncMock(), delete_event=AsyncMock())
    actions = CalendarActions(service, Mock(unlocked=AsyncMock()), MemoryTemporaryStore(), 42)
    data = {
        "title": "Test",
        "start": "2026-09-25T15:00:00+05:00",
        "end": "2026-09-25T16:00:00+05:00",
    }
    token = await actions.prepare("create", data)
    service.create_event.assert_not_called()
    results = await asyncio.gather(
        actions.confirm(token), actions.confirm(token), return_exceptions=True
    )
    service.create_event.assert_awaited_once()
    assert sum(isinstance(item, CalendarError) for item in results) == 1
    token = await actions.prepare("delete", {"id": "abc", "etag": "v1"})
    service.delete_event.assert_not_called()
    await actions.confirm(token)
    service.delete_event.assert_awaited_once_with("abc", "v1")


async def test_disconnect_removes_credentials_on_revocation_outage() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(503))
    ) as http:
        service = oauth(http)
        assert not await service.disconnect()
        service.store.delete.assert_awaited_once()


async def test_oauth_http_endpoints_are_safe() -> None:
    from app.api.app import create_app
    from app.core.application import ApplicationContext

    context = ApplicationContext(
        Settings(
            _env_file=None,
            DATABASE_URL=None,
            REDIS_URL=None,
            SECURITY_STATE_BACKEND="memory",
            OAUTH_STATE_BACKEND="memory",
        )
    )
    await context.start()
    app = create_app(context=context)
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client,
        ):
            response = await client.get("/oauth/google/start", params={"ticket": "x" * 32})
            assert response.status_code == 400
            assert response.headers["cache-control"] == "no-store"
            assert "Traceback" not in response.text
            response = await client.get(
                "/oauth/google/callback", params={"state": "x" * 32, "code": "secret-code" * 500}
            )
            assert response.status_code == 400
            assert "secret-code" not in response.text
    finally:
        await context.close()


async def test_oauth_http_cookie_and_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.app import create_app
    from app.core.application import ApplicationContext

    context = ApplicationContext(
        Settings(
            _env_file=None,
            DATABASE_URL=None,
            REDIS_URL=None,
            SECURITY_STATE_BACKEND="memory",
            OAUTH_STATE_BACKEND="memory",
        )
    )
    await context.start()
    app = create_app(context=context)
    try:
        context.calendar.oauth.begin = AsyncMock(
            return_value="https://accounts.google.com/o/oauth2/auth"
        )
        context.calendar.oauth.callback = AsyncMock()
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client,
        ):
            response = await client.get("/oauth/google/start", params={"ticket": "x" * 32})
            assert response.status_code == 303
            assert "HttpOnly" in response.headers["set-cookie"]
            assert "SameSite=lax" in response.headers["set-cookie"]
            browser = client.cookies["calendar_oauth"]
            response = await client.get(
                "/oauth/google/callback", params={"state": "s" * 32, "code": "secret-code"}
            )
            assert response.status_code == 200 and "connected" in response.text
            context.calendar.oauth.callback.assert_awaited_once_with(
                "s" * 32, "secret-code", browser
            )
            assert "calendar_oauth" not in client.cookies
    finally:
        await context.close()


@pytest.mark.parametrize("scope_as_list", [True, False])
async def test_official_flow_exchange_scope_formats(scope_as_list: bool) -> None:
    from app.modules.calendar.auth import SCOPES

    async with httpx.AsyncClient() as http:
        service = oauth(http)
        flow = Mock()
        flow.fetch_token.return_value = {
            "refresh_token": "private-refresh",
            "scope": SCOPES if scope_as_list else " ".join(SCOPES),
        }
        service.flow = Mock(return_value=flow)
        assert (
            await service.exchange("code", "state", "verifier")
        ).get_secret_value() == "private-refresh"
        flow.fetch_token.assert_called_once_with(code="code", timeout=15)
        flow.oauth2session.close.assert_called_once()
````

### C:/Users/USER/Documents/Agent/tests/bot/test_calendar_handlers.py

````python
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram.methods import SendMessage
from aiogram.types import Update

from app.bot.constants import DENIED, LOCKED
from app.modules.calendar.actions import CalendarActions
from app.modules.calendar.state import MemoryTemporaryStore

from .conftest import Harness


def attach(harness: Harness) -> Mock:
    calendar = Mock()
    calendar.settings.timezone = __import__("zoneinfo").ZoneInfo("Asia/Tashkent")
    calendar.settings.calendar_default_event_duration_minutes = 60
    calendar.settings.google_calendar_id = "primary"
    calendar.store.load = AsyncMock(return_value=None)
    calendar.service.create_event = AsyncMock()
    calendar.service.get_today_events = AsyncMock(return_value=[])
    calendar.service.get_tomorrow_events = AsyncMock(return_value=[])
    calendar.service.list_upcoming_events = AsyncMock(return_value=[])
    calendar.oauth.unlocked = AsyncMock()
    calendar.actions = CalendarActions(calendar.service, calendar.oauth, MemoryTemporaryStore(), 42)
    harness.context.calendar = calendar
    return calendar


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


@pytest.mark.parametrize(
    "command",
    [
        "/calendar",
        "/today",
        "/tomorrow",
        "/upcoming",
        "/event_add",
        "/event_update",
        "/event_delete",
        "/free",
        "/google_connect",
        "/google_disconnect",
    ],
)
async def test_calendar_owner_lock_boundary(harness: Harness, command: str) -> None:
    calendar = attach(harness)
    await harness.send(command, user_id=99)
    assert harness.replies[-1] == DENIED
    await harness.send(command)
    assert harness.replies[-1] == LOCKED
    calendar.service.create_event.assert_not_called()


async def test_create_fsm_and_double_click(harness: Harness) -> None:
    calendar = attach(harness)
    await harness.context.security.lock_state.unlock()
    for text in ["/event_add", "Meeting", "25.09.2026", "15:00", "-", "-"]:
        await harness.send(text)
    assert "saqlansinmi" in harness.replies[-1]
    calendar.service.create_event.assert_not_called()
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    data = prompt.reply_markup.inline_keyboard[0][0].callback_data
    await callback(harness, data)
    await callback(harness, data)
    calendar.service.create_event.assert_awaited_once()
    assert "Event yaratildi." in harness.replies


async def test_cancel_prevents_create(harness: Harness) -> None:
    calendar = attach(harness)
    await harness.context.security.lock_state.unlock()
    for text in ["/event_add", "Meeting", "25.09.2026", "15:00", "60", "10"]:
        await harness.send(text)
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    data = prompt.reply_markup.inline_keyboard[0][0].callback_data
    await harness.send("/cancel")
    await callback(harness, data)
    calendar.service.create_event.assert_not_called()


@pytest.mark.parametrize("command", ["/today", "/tomorrow", "/upcoming"])
async def test_empty_schedule(harness: Harness, command: str) -> None:
    attach(harness)
    await harness.context.security.lock_state.unlock()
    await harness.send(command)
    assert "reja yo'q" in harness.replies[-1]


async def test_delete_selection_and_confirmation(harness: Harness) -> None:
    from app.modules.calendar.schemas import CalendarEventView

    calendar = attach(harness)
    await harness.context.security.lock_state.unlock()
    event = CalendarEventView(
        id="abc123",
        etag="v1",
        title="Meeting",
        start=datetime(2026, 9, 25, 10, tzinfo=UTC),
        end=datetime(2026, 9, 25, 11, tzinfo=UTC),
    )
    calendar.service.list_upcoming_events.return_value = [event]
    calendar.service.get_event = AsyncMock(return_value=event)
    calendar.service.mutable_event = AsyncMock(return_value=event)
    calendar.service.delete_event = AsyncMock()
    await harness.send("/event_delete")
    await harness.send("1")
    calendar.service.delete_event.assert_not_called()
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    await callback(harness, prompt.reply_markup.inline_keyboard[0][0].callback_data)
    calendar.service.delete_event.assert_awaited_once_with("abc123", "v1")


async def test_update_title_confirmation(harness: Harness) -> None:
    from app.modules.calendar.schemas import CalendarEventView

    calendar = attach(harness)
    await harness.context.security.lock_state.unlock()
    event = CalendarEventView(
        id="abc123",
        etag="v1",
        title="Meeting",
        start=datetime(2026, 9, 25, 10, tzinfo=UTC),
        end=datetime(2026, 9, 25, 11, tzinfo=UTC),
    )
    calendar.service.list_upcoming_events.return_value = [event]
    calendar.service.get_event = AsyncMock(return_value=event)
    calendar.service.mutable_event = AsyncMock(return_value=event)
    calendar.service.update_event = AsyncMock()
    for text in ["/event_update", "1", "title", "Updated meeting"]:
        await harness.send(text)
    calendar.service.update_event.assert_not_called()
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    await callback(harness, prompt.reply_markup.inline_keyboard[0][0].callback_data)
    calendar.service.update_event.assert_awaited_once()
    assert calendar.service.update_event.call_args.args[1].fields == {"title"}


async def test_disconnect_confirmation(harness: Harness) -> None:
    calendar = attach(harness)
    calendar.oauth.disconnect = AsyncMock(return_value=True)
    await harness.context.security.lock_state.unlock()
    await harness.send("/google_disconnect")
    calendar.oauth.disconnect.assert_not_called()
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    await callback(harness, prompt.reply_markup.inline_keyboard[0][0].callback_data)
    calendar.oauth.disconnect.assert_awaited_once()


async def test_free_syntax_and_result(harness: Harness) -> None:
    from app.modules.calendar.schemas import FreeBusyResult, TimeInterval

    calendar = attach(harness)
    await harness.context.security.lock_state.unlock()
    await harness.send("/free invalid")
    assert "Format:" in harness.replies[-1]
    calendar.service.get_free_busy = AsyncMock(
        return_value=FreeBusyResult(
            busy=[],
            free=[TimeInterval(start="2026-09-25T14:00:00+05:00", end="2026-09-25T20:00:00+05:00")],
        )
    )
    await harness.send("/free 25.09.2026 14:00 20:00")
    assert "14:00-20:00" in harness.replies[-1]
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
            await self.service.create_event(CalendarEventCreate.model_validate(data), uuid4().hex)
            return "Event yaratildi."
        if kind == "update":
            await self.service.update_event(
                data["id"], CalendarEventUpdate.model_validate(data["event"]), data["etag"]
            )
            return "Event yangilandi."
        if kind == "delete":
            await self.service.delete_event(data["id"], data["etag"])
            return "Event o'chirildi."
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

### C:/Users/USER/Documents/Agent/app/modules/calendar/audit.py

````python
import asyncio
import logging

from app.core.logging import report_error
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.users.repository import UserRepository


class CalendarAudit:
    """Independent best-effort transaction AFTER provider success; never retries actions."""

    def __init__(self, database: DatabaseManager | None, owner: int | None) -> None:
        self.database, self.owner = database, owner

    async def record(self, action: AuditAction, event_id: str | None = None) -> None:
        if self.database is None or self.owner is None:
            logging.getLogger(__name__).warning("calendar_audit_database_unconfigured")
            return
        try:
            async with asyncio.timeout(5), self.database.session() as session:
                user = await UserRepository(session).get_by_telegram_user_id(self.owner)
                await AuditService(AuditRepository(session)).log_event(
                    action,
                    user_id=user.id if user else None,
                    entity_type="calendar",
                    entity_id=event_id,
                )
        except Exception as error:  # noqa: BLE001 - isolated best-effort audit boundary
            # External action already succeeded; audit errors must not imply retry is safe.
            report_error(logging.getLogger(__name__), error)
````

### C:/Users/USER/Documents/Agent/app/modules/calendar/auth.py

````python
"""Official Google refresh logic off the event loop; access tokens only in memory."""

import asyncio
from datetime import UTC, datetime, timedelta

import requests
from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.calendar.credentials import CredentialStore
from app.modules.calendar.exceptions import (
    CalendarConfigurationError,
    GoogleCalendarAuthenticationError,
    GoogleCalendarUnavailableError,
)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.freebusy",
]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def require_google(settings: Settings) -> None:
    if not settings.google_client_id or not settings.google_client_secret:
        raise CalendarConfigurationError("Google OAuth client settings are missing.")


class GoogleTokenProvider:
    def __init__(self, settings: Settings, store: CredentialStore) -> None:
        self.settings, self.store = settings, store
        self._lock = asyncio.Lock()
        self._credentials: Credentials | None = None
        self._source: SecretStr | None = None
        self._invalid: SecretStr | None = None

    def invalidate(self) -> None:
        self._credentials = None
        self._invalid = self._source

    async def access_token(self) -> str:
        require_google(self.settings)
        async with self._lock:
            # Re-read so disconnect/reconnect in another process invalidates the cache.
            refresh = await self.store.load()
            if refresh is None or refresh == self._invalid:
                raise GoogleCalendarAuthenticationError(
                    "Google Calendar: reconnect with /google_connect."
                )
            if (
                refresh == self._source
                and self._credentials is not None
                and self._credentials.expiry is not None
                and self._credentials.expiry
                > datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=1)
            ):
                return str(self._credentials.token)
            assert self.settings.google_client_id and self.settings.google_client_secret
            credentials = Credentials(
                token=None,
                refresh_token=refresh.get_secret_value(),
                token_uri=TOKEN_URI,
                client_id=self.settings.google_client_id.get_secret_value(),
                client_secret=self.settings.google_client_secret.get_secret_value(),
                scopes=SCOPES,
            )

            def refresh_sync() -> None:
                with requests.Session() as session:
                    request = Request(session=session)
                    credentials.refresh(lambda **kwargs: request(**{**kwargs, "timeout": 15}))

            try:
                await asyncio.to_thread(refresh_sync)
            except RefreshError as error:
                if not error.retryable:
                    self._invalid = refresh
                raise GoogleCalendarAuthenticationError(
                    "Google Calendar authorization failed; reconnect."
                ) from None
            except (TransportError, requests.RequestException):
                raise GoogleCalendarUnavailableError(
                    "Google temporarily unavailable. Try later."
                ) from None
            if (
                credentials.refresh_token
                and credentials.refresh_token != refresh.get_secret_value()
            ):
                replacement = SecretStr(credentials.refresh_token)
                if not await self.store.rotate(refresh, replacement):
                    raise GoogleCalendarAuthenticationError("Google connection changed. Try again.")
                refresh = replacement
            self._source, self._credentials, self._invalid = refresh, credentials, None
            return str(credentials.token)
````

### C:/Users/USER/Documents/Agent/app/modules/calendar/client.py

````python
"""Async Calendar REST transport; official google-auth owns token refresh."""

from typing import Any
from urllib.parse import quote

import httpx

from app.modules.calendar.auth import GoogleTokenProvider
from app.modules.calendar.exceptions import (
    CalendarConflictError,
    CalendarError,
    CalendarEventNotFoundError,
    GoogleCalendarAuthenticationError,
    GoogleCalendarPermissionError,
    GoogleCalendarUnavailableError,
)


class GoogleCalendarClient:
    def __init__(
        self, http: httpx.AsyncClient, tokens: GoogleTokenProvider, calendar_id: str
    ) -> None:
        self.http, self.tokens, self.calendar_id = http, tokens, calendar_id
        self.base = "https://www.googleapis.com/calendar/v3"
        self.events = f"/calendars/{quote(calendar_id, safe='')}/events"

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        etag: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {await self.tokens.access_token()}"}
        if etag:
            headers["If-Match"] = etag
        try:
            response = await self.http.request(
                method, self.base + path, params=params, json=body, headers=headers
            )
        except httpx.RequestError:
            raise GoogleCalendarUnavailableError(
                "Google temporarily unavailable. Try later."
            ) from None
        status = response.status_code
        if status == 401:
            self.tokens.invalidate()
            raise GoogleCalendarAuthenticationError("Google authorization expired. Reconnect.")
        if status == 403:
            try:
                reasons = str(response.json().get("error", {}).get("errors", []))
            except ValueError:
                reasons = ""
            if "rateLimitExceeded" in reasons or "userRateLimitExceeded" in reasons:
                raise GoogleCalendarUnavailableError("Google rate limit reached. Try later.")
            raise GoogleCalendarPermissionError("Calendar permission denied.")
        if status in (404, 410):
            raise CalendarEventNotFoundError("Calendar event not found.")
        if status in (409, 412):
            raise CalendarConflictError(
                "Event changed or action already submitted. Refresh the list."
            )
        if status == 429 or status >= 500:
            raise GoogleCalendarUnavailableError(
                "Google temporarily unavailable or rate limited. Try later."
            )
        if status >= 400:
            raise CalendarError("Google rejected the calendar request.")
        if status == 204:
            return {}
        try:
            return response.json()
        except ValueError:
            raise GoogleCalendarUnavailableError("Invalid Calendar response. Try later.") from None

    async def list_events(self, start: str, end: str | None, limit: int) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        params: dict[str, Any] = {
            "timeMin": start,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": min(limit, 250),
        }
        if end:
            params["timeMax"] = end
        while len(result) < limit:
            page = await self.request("GET", self.events, params=params)
            result.extend(
                item for item in page.get("items", []) if item.get("status") != "cancelled"
            )
            if not page.get("nextPageToken"):
                break
            params["pageToken"] = page["nextPageToken"]
        return result[:limit]

    async def create_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("POST", self.events, body=payload, params={"sendUpdates": "none"})

    async def get_event(self, event_id: str) -> dict[str, Any]:
        return await self.request("GET", f"{self.events}/{quote(event_id, safe='')}")

    async def update_event(
        self, event_id: str, payload: dict[str, Any], etag: str
    ) -> dict[str, Any]:
        return await self.request(
            "PATCH",
            f"{self.events}/{quote(event_id, safe='')}",
            body=payload,
            etag=etag,
            params={"sendUpdates": "none"},
        )

    async def delete_event(self, event_id: str, etag: str) -> None:
        await self.request(
            "DELETE",
            f"{self.events}/{quote(event_id, safe='')}",
            etag=etag,
            params={"sendUpdates": "none"},
        )

    async def free_busy(self, start: str, end: str, timezone: str) -> dict[str, Any]:
        return await self.request(
            "POST",
            "/freeBusy",
            body={
                "timeMin": start,
                "timeMax": end,
                "timeZone": timezone,
                "items": [{"id": self.calendar_id}],
            },
        )
````

### C:/Users/USER/Documents/Agent/app/modules/calendar/credentials.py

````python
import asyncio
from typing import Protocol

from pydantic import SecretStr

from app.core.encryption import CredentialEncryption
from app.database.session import DatabaseManager
from app.modules.calendar.exceptions import CalendarConfigurationError
from app.modules.calendar.repository import GoogleCredentialRepository
from app.modules.users.repository import UserRepository


class CredentialStore(Protocol):
    async def load(self) -> SecretStr | None: ...
    async def save(self, refresh_token: SecretStr) -> None: ...
    async def delete(self) -> None: ...
    async def rotate(self, previous: SecretStr, current: SecretStr) -> bool: ...


class GoogleCredentialStore:
    def __init__(
        self, database: DatabaseManager | None, owner: int | None, key: SecretStr | None
    ) -> None:
        self.database, self.owner, self.key = database, owner, key

    def require_configured(self) -> CredentialEncryption:
        if self.database is None or self.owner is None:
            raise CalendarConfigurationError("Calendar requires PostgreSQL and TELEGRAM_OWNER_ID.")
        return CredentialEncryption(self.key)

    async def load(self) -> SecretStr | None:
        cipher = self.require_configured()
        assert self.database is not None and self.owner is not None
        async with asyncio.timeout(10), self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner)
            row = await GoogleCredentialRepository(session).load(user.id) if user else None
            return (
                SecretStr(cipher.decrypt(row.refresh_token_encrypted, self.owner)) if row else None
            )

    async def save(self, refresh_token: SecretStr) -> None:
        cipher = self.require_configured()
        assert self.database is not None and self.owner is not None
        async with asyncio.timeout(10), self.database.session() as session:
            users = UserRepository(session)
            user = await users.get_by_telegram_user_id(self.owner)
            if user is None:
                user = await users.create(self.owner)
            await GoogleCredentialRepository(session).save(
                user.id, cipher.encrypt(refresh_token.get_secret_value(), self.owner)
            )

    async def delete(self) -> None:
        self.require_configured()
        assert self.database is not None and self.owner is not None
        async with asyncio.timeout(10), self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner)
            if user:
                await GoogleCredentialRepository(session).delete(user.id)

    async def rotate(self, previous: SecretStr, current: SecretStr) -> bool:
        """Compare-and-swap; delayed refresh must not resurrect a disconnected credential."""
        cipher = self.require_configured()
        assert self.database is not None and self.owner is not None
        async with asyncio.timeout(10), self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner)
            if user is None:
                return False
            repository = GoogleCredentialRepository(session)
            row = await repository.load(user.id)
            if (
                row is None
                or cipher.decrypt(row.refresh_token_encrypted, self.owner)
                != previous.get_secret_value()
            ):
                return False
            return await repository.replace(
                user.id,
                row.refresh_token_encrypted,
                cipher.encrypt(current.get_secret_value(), self.owner),
            )
````

### C:/Users/USER/Documents/Agent/app/modules/calendar/exceptions.py

````python
class CalendarError(Exception):
    """Safe public messages only; never include provider responses or credentials."""


class CalendarConfigurationError(CalendarError):
    pass


class GoogleCalendarAuthenticationError(CalendarError):
    pass


class GoogleCalendarPermissionError(CalendarError):
    pass


class CalendarEventNotFoundError(CalendarError):
    pass


class GoogleCalendarUnavailableError(CalendarError):
    pass


class CalendarConflictError(CalendarError):
    pass


class OAuthStateError(CalendarError):
    pass
````

### C:/Users/USER/Documents/Agent/app/modules/calendar/oauth.py

````python
"""Owner-issued start ticket, browser-bound state and PKCE; all tickets single use."""

import asyncio
import hashlib
import logging
import secrets
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx
from google_auth_oauthlib.flow import Flow
from pydantic import SecretStr

from app.core.config import Settings
from app.core.logging import report_error
from app.modules.audit.actions import AuditAction
from app.modules.calendar.audit import CalendarAudit
from app.modules.calendar.auth import SCOPES, TOKEN_URI, require_google
from app.modules.calendar.credentials import GoogleCredentialStore
from app.modules.calendar.exceptions import (
    CalendarConfigurationError,
    GoogleCalendarAuthenticationError,
    OAuthStateError,
)
from app.modules.calendar.state import TemporaryStore
from app.modules.security.lock_service import LockService


class GoogleOAuthService:
    def __init__(
        self,
        settings: Settings,
        store: GoogleCredentialStore,
        states: TemporaryStore,
        lock: LockService,
        audit: CalendarAudit,
        http: httpx.AsyncClient,
    ) -> None:
        self.settings, self.store, self.states = settings, store, states
        self.lock, self.audit, self.http = lock, audit, http

    def configured(self) -> None:
        require_google(self.settings)
        uri = urlsplit(self.settings.google_redirect_uri or "")
        local = uri.hostname in {"localhost", "127.0.0.1", "::1"}
        if (uri.scheme != "https" and not (local and uri.scheme == "http")) or (
            not uri.hostname
            or uri.path != "/oauth/google/callback"
            or uri.query
            or uri.fragment
            or uri.username is not None
            or uri.password is not None
        ):
            raise CalendarConfigurationError(
                "GOOGLE_REDIRECT_URI must use HTTPS or loopback HTTP and /oauth/google/callback."
            )
        self.store.require_configured()

    async def unlocked(self) -> None:
        if await self.lock.is_locked():
            raise OAuthStateError(
                "Owner session is locked. Unlock in Telegram and restart connection."
            )

    def flow(self, state: str, verifier: str) -> Flow:
        assert self.settings.google_client_id and self.settings.google_client_secret
        return Flow.from_client_config(
            {
                "web": {
                    "client_id": self.settings.google_client_id.get_secret_value(),
                    "client_secret": self.settings.google_client_secret.get_secret_value(),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": TOKEN_URI,
                }
            },
            scopes=SCOPES,
            state=state,
            code_verifier=verifier,
            redirect_uri=self.settings.google_redirect_uri,
        )

    async def connect_url(self) -> str:
        self.configured()
        await self.unlocked()
        ticket = await self.states.issue("start", {"owner": self.settings.telegram_owner_id})
        uri = urlsplit(self.settings.google_redirect_uri or "")
        return f"{uri.scheme}://{uri.netloc}/oauth/google/start?{urlencode({'ticket': ticket})}"

    async def begin(self, ticket: str, browser: str) -> str:
        self.configured()
        await self.unlocked()
        pending = await self.states.consume("start", ticket)
        if not pending or pending["owner"] != self.settings.telegram_owner_id:
            raise OAuthStateError("Invalid or expired connection link. Use /google_connect again.")
        verifier = secrets.token_urlsafe(64)
        state = await self.states.issue(
            "oauth",
            {
                "owner": self.settings.telegram_owner_id,
                "verifier": verifier,
                "browser": hashlib.sha256(browser.encode()).hexdigest(),
            },
        )
        flow = self.flow(state, verifier)
        try:
            url, _ = flow.authorization_url(access_type="offline", prompt="consent", state=state)
            return url
        finally:
            flow.oauth2session.close()

    async def exchange(self, code: str, state: str, verifier: str) -> SecretStr:
        def exchange_sync() -> SecretStr:
            flow = self.flow(state, verifier)
            try:
                token: dict[str, Any] = flow.fetch_token(code=code, timeout=15)
                scope = token.get("scope", [])
                granted = set(scope.split() if isinstance(scope, str) else scope)
                if not token.get("refresh_token") or not set(SCOPES).issubset(granted):
                    raise GoogleCalendarAuthenticationError(
                        "Required Calendar permissions were not granted."
                    )
                return SecretStr(token["refresh_token"])
            finally:
                flow.oauth2session.close()

        try:
            return await asyncio.to_thread(exchange_sync)
        except Exception as error:  # noqa: BLE001 - SDK boundary, safely logged without payloads
            report_error(logging.getLogger(__name__), error)
            raise GoogleCalendarAuthenticationError(
                "Google authorization failed. Use /google_connect again."
            ) from None

    async def callback(self, state: str, code: str, browser: str) -> None:
        self.configured()
        pending = await self.states.consume("oauth", state)
        if (
            not pending
            or pending["owner"] != self.settings.telegram_owner_id
            or not secrets.compare_digest(
                pending["browser"], hashlib.sha256(browser.encode()).hexdigest()
            )
        ):
            raise OAuthStateError("Invalid or expired OAuth state.")
        await self.unlocked()
        if not code:
            raise OAuthStateError("Google authorization was cancelled. Use /google_connect again.")
        token = await self.exchange(code, state, pending["verifier"])
        await self.unlocked()
        await self.store.save(token)
        await self.audit.record(AuditAction.GOOGLE_CALENDAR_CONNECTED)

    async def disconnect(self) -> bool:
        token = await self.store.load()
        # Delete locally first: remote revocation outage must never retain the stored token.
        await self.store.delete()
        revoked = token is None
        if token:
            try:
                response = await self.http.post(
                    "https://oauth2.googleapis.com/revoke", data={"token": token.get_secret_value()}
                )
                revoked = response.status_code == 200
            except httpx.RequestError:
                logging.getLogger(__name__).warning("google_revocation_unavailable")
        await self.audit.record(AuditAction.GOOGLE_CALENDAR_DISCONNECTED)
        return revoked
````

### C:/Users/USER/Documents/Agent/app/modules/calendar/repository.py

````python
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import GoogleCredential


class GoogleCredentialRepository:
    """Caller owns transaction; repository only accepts encrypted bytes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load(self, user_id: int) -> GoogleCredential | None:
        return await self.session.scalar(
            select(GoogleCredential).where(
                GoogleCredential.user_id == user_id,
                GoogleCredential.provider == "google_calendar",
            )
        )

    async def save(self, user_id: int, encrypted: bytes) -> None:
        row = await self.load(user_id)
        if row is None:
            row = GoogleCredential(user_id=user_id, provider="google_calendar")
            self.session.add(row)
        row.refresh_token_encrypted = encrypted
        await self.session.flush()

    async def delete(self, user_id: int) -> None:
        await self.session.execute(
            delete(GoogleCredential).where(
                GoogleCredential.user_id == user_id,
                GoogleCredential.provider == "google_calendar",
            )
        )

    async def replace(self, user_id: int, expected: bytes, encrypted: bytes) -> bool:
        result = await self.session.execute(
            update(GoogleCredential)
            .where(
                GoogleCredential.user_id == user_id,
                GoogleCredential.provider == "google_calendar",
                GoogleCredential.refresh_token_encrypted == expected,
            )
            .values(refresh_token_encrypted=encrypted)
            .returning(GoogleCredential.id)
        )
        return result.scalar_one_or_none() is not None
````

### C:/Users/USER/Documents/Agent/app/modules/calendar/runtime.py

````python
"""Small Calendar composition root borrowing shared DB, Redis and lock resources."""

import httpx

from app.core.config import Settings
from app.database.session import DatabaseManager
from app.modules.calendar.actions import CalendarActions
from app.modules.calendar.audit import CalendarAudit
from app.modules.calendar.auth import GoogleTokenProvider
from app.modules.calendar.client import GoogleCalendarClient
from app.modules.calendar.credentials import GoogleCredentialStore
from app.modules.calendar.exceptions import CalendarConfigurationError
from app.modules.calendar.oauth import GoogleOAuthService
from app.modules.calendar.service import CalendarService
from app.modules.calendar.state import MemoryTemporaryStore, RedisTemporaryStore, TemporaryStore
from app.modules.security.lock_service import LockService
from app.redis.manager import RedisManager


class CalendarRuntime:
    def __init__(
        self,
        settings: Settings,
        database: DatabaseManager | None,
        redis: RedisManager | None,
        lock: LockService,
    ) -> None:
        self.settings = settings
        self.store = GoogleCredentialStore(
            database, settings.telegram_owner_id, settings.data_encryption_key
        )
        self.states: TemporaryStore = MemoryTemporaryStore()
        if settings.oauth_state_backend == "redis":
            if redis is None:
                raise CalendarConfigurationError("OAUTH_STATE_BACKEND=redis requires REDIS_URL.")
            self.states = RedisTemporaryStore(
                redis.client, settings.redis_key_prefix, settings.telegram_owner_id or 0
            )
        self.http = httpx.AsyncClient(timeout=20, follow_redirects=False)
        audit = CalendarAudit(database, settings.telegram_owner_id)
        self.tokens = GoogleTokenProvider(settings, self.store)
        self.service = CalendarService(
            GoogleCalendarClient(self.http, self.tokens, settings.google_calendar_id),
            audit,
            settings.timezone,
        )
        self.oauth = GoogleOAuthService(settings, self.store, self.states, lock, audit, self.http)
        self.actions = CalendarActions(
            self.service, self.oauth, self.states, settings.telegram_owner_id
        )

    async def close(self) -> None:
        await self.http.aclose()
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
from typing import Any
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


class CalendarService:
    """Validated domain operations; Telegram confirmation is a separate action boundary."""

    def __init__(
        self, client: GoogleCalendarClient, audit: CalendarAudit, timezone: ZoneInfo
    ) -> None:
        self.client, self.audit, self.timezone = client, audit, timezone

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
        return result

    async def delete_event(self, event_id: str, etag: str) -> None:
        await self.mutable_event(event_id, etag)
        await self.client.delete_event(event_id, etag)
        await self.audit.record(AuditAction.CALENDAR_EVENT_DELETED, event_id)

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

### C:/Users/USER/Documents/Agent/app/modules/calendar/state.py

````python
"""Single-use opaque capabilities, with native Redis expiration when selected."""

import hashlib
import json
import secrets
import time
from typing import Any, Protocol

from redis.asyncio import Redis


class TemporaryStore(Protocol):
    async def issue(self, purpose: str, data: dict[str, Any], ttl: int = 600) -> str: ...
    async def consume(self, purpose: str, token: str) -> dict[str, Any] | None: ...


class MemoryTemporaryStore:
    """Explicit single-process development store. Restart invalidates all actions."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}

    async def issue(self, purpose: str, data: dict[str, Any], ttl: int = 600) -> str:
        now = time.monotonic()
        self._items = {key: value for key, value in self._items.items() if value[0] > now}
        token = secrets.token_urlsafe(24)
        self._items[purpose, token] = (now + ttl, data)
        return token

    async def consume(self, purpose: str, token: str) -> dict[str, Any] | None:
        item = self._items.pop((purpose, token), None)
        return item[1] if item and item[0] > time.monotonic() else None


class RedisTemporaryStore:
    def __init__(self, client: Redis, prefix: str, owner: int) -> None:
        self.client = client
        self.prefix = f"{prefix}:calendar:{{{owner}}}"

    def key(self, purpose: str, token: str) -> str:
        return f"{self.prefix}:{purpose}:{hashlib.sha256(token.encode()).hexdigest()}"

    async def issue(self, purpose: str, data: dict[str, Any], ttl: int = 600) -> str:
        token = secrets.token_urlsafe(24)
        await self.client.set(self.key(purpose, token), json.dumps(data), ex=ttl, nx=True)
        return token

    async def consume(self, purpose: str, token: str) -> dict[str, Any] | None:
        raw = await self.client.getdel(self.key(purpose, token))
        return json.loads(raw) if raw else None
````

### C:/Users/USER/Documents/Agent/app/modules/calendar/utils.py

````python
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.modules.calendar.schemas import CalendarEventView, TimeInterval


def day_range(day: date, timezone: ZoneInfo) -> TimeInterval:
    return TimeInterval(
        start=datetime.combine(day, time.min, timezone),
        end=datetime.combine(day + timedelta(days=1), time.min, timezone),
    )


def parse_local(day: str, clock: str, timezone: ZoneInfo) -> datetime:
    aware = datetime.strptime(f"{day} {clock}", "%d.%m.%Y %H:%M").replace(tzinfo=timezone)
    # Reject ambiguous/nonexistent wall time rather than silently choosing a DST fold.
    if aware.utcoffset() != aware.replace(fold=1).utcoffset():
        raise ValueError("Ambiguous or nonexistent local time")
    return aware


def event_view(raw: dict[str, Any]) -> CalendarEventView:
    all_day = "date" in raw["start"]
    parse = date.fromisoformat if all_day else datetime.fromisoformat
    field = "date" if all_day else "dateTime"
    return CalendarEventView(
        id=raw["id"],
        etag=raw.get("etag", ""),
        title=raw.get("summary", "(Untitled)"),
        start=parse(raw["start"][field]),
        end=parse(raw["end"][field]),
        all_day=all_day,
        recurring=bool(raw.get("recurringEventId") or raw.get("recurrence")),
        description=raw.get("description", ""),
        location=raw.get("location", ""),
        reminders=[
            r["minutes"]
            for r in raw.get("reminders", {}).get("overrides", [])
            if r.get("method") == "popup"
        ],
    )


def free_intervals(window: TimeInterval, busy: list[TimeInterval]) -> list[TimeInterval]:
    """Clip and merge overlapping/adjacent busy intervals; return their complement."""
    cursor = window.start
    result: list[TimeInterval] = []
    for interval in sorted(busy, key=lambda item: item.start):
        start, end = max(interval.start, window.start), min(interval.end, window.end)
        if end <= start:
            continue
        if start > cursor:
            result.append(TimeInterval(start=cursor, end=start))
        cursor = max(cursor, end)
    if cursor < window.end:
        result.append(TimeInterval(start=cursor, end=window.end))
    return result


def event_label(event: CalendarEventView, timezone: ZoneInfo) -> str:
    when = (
        f"{event.start:%d.%m.%Y} All day"
        if event.all_day
        else event.start.astimezone(timezone).strftime("%d.%m.%Y %H:%M")
    )
    return f"{when} - {event.title[:200]}"
````

### C:/Users/USER/Documents/Agent/app/modules/calendar/__init__.py

````python
"""Deterministic Calendar domain; no AI execution or import-time connections."""
````


