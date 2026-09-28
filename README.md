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
# Stage 1 - Step 7: Gmail read-only integration

Step 7 adds a privacy-oriented Gmail index and polling monitor. It requests only
`https://www.googleapis.com/auth/gmail.readonly`; `gmail.send` and `gmail.modify` are not
requested. Gmail uses a separate encrypted `google_gmail` credential, so enabling or
disconnecting Gmail does not overwrite the Calendar authorization. Google will ask for consent
again when Gmail is first connected.

Email metadata, attachment metadata, snippet, and SHA-256 body fingerprint are indexed. Cleaned
body text and deterministic summary are encrypted with AES-256-GCM using provider-specific
authenticated contexts. Raw MIME, raw HTML, remote images, and attachment contents are never
stored or fetched. Incoming email is untrusted external DATA: its text cannot authorize tools,
change system instructions, or execute actions. Sending email is intentionally unavailable.

Configuration:

```dotenv
RUN_GMAIL_MONITOR=false
GMAIL_POLL_INTERVAL_SECONDS=60
GMAIL_INITIAL_SYNC_LIMIT=30
GMAIL_RECENT_LIST_LIMIT=10
GMAIL_NOTIFY_MODE=all
```

`GMAIL_POLL_INTERVAL_SECONDS` must be 30-3600. Notification modes are `all`, `important`, and
`unread`. Enable monitoring only after PostgreSQL migrations and Gmail authorization are ready.
The initial sync indexes a bounded recent baseline and sends no historical alerts. Later polls
use the persisted Gmail history checkpoint and `notified_at` to prevent duplicate alerts. The
monitor backs off up to 300 seconds after provider failures.

PowerShell setup and migration:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.run_all
```

After unlocking the bot, run `/gmail_connect`. Register
`http://127.0.0.1:8000/oauth/gmail/callback` (or its HTTPS production equivalent) in the same
Google OAuth client. Available commands are `/email`, `/emails`, `/email_unread`, `/email_read`,
`/email_search`, `/email_reply`, `/google_gmail_status`, `/gmail_connect`, and
`/gmail_disconnect`. Full reading, searching, drafting, and callbacks require an unlocked session.
New-email previews may be delivered while locked; opening the full content remains blocked.

Reply drafts are local deterministic containers only. The owner supplies the text and receives a
preview explicitly stating that sending is disabled. Attachment download, Gmail mutations,
LLM summarization, Pub/Sub, and autonomous replies are outside Step 7.

Run verification:

```powershell
.\.venv\Scripts\python.exe -m compileall app tests migrations
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\ruff.exe check .
```
# Stage 1 - Step 8: Personal Telegram through MTProto

Step 8 connects the owner's personal Telegram account using Telethon/MTProto. This is completely
separate from the Aiogram assistant bot:

- `TELEGRAM_BOT_TOKEN` controls the private assistant bot.
- `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` identify the owner's MTProto developer application.
- The assistant bot is the authenticated control channel. Personal Telegram messages are external,
  untrusted DATA and can never authorize actions or override system instructions.

Obtain API ID/hash from Telegram's official developer application portal. Keep the API hash private;
never paste it into source code, logs, chat messages, or documentation.

## Configuration

```dotenv
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
PERSONAL_TELEGRAM_ENABLED=false
PERSONAL_TELEGRAM_SESSION_BACKEND=database
RUN_PERSONAL_TELEGRAM_MONITOR=true
PERSONAL_TELEGRAM_INITIAL_SYNC_LIMIT=30
PERSONAL_TELEGRAM_RECENT_LIMIT=10
PERSONAL_TELEGRAM_MONITOR_SCOPE=private
```

The default scope is `private`; group/channel monitoring is not enabled by default. Set
`PERSONAL_TELEGRAM_ENABLED=true` only after PostgreSQL, migrations, `DATA_ENCRYPTION_KEY`, API
credentials, and the assistant bot are ready.

## Secure connection

1. Unlock the assistant and run `/telegram_connect`.
2. Enter the account phone in international format. The assistant attempts to delete that message.
3. Enter Telegram's login code. It is used in memory, never persisted, and its bot message is
   deleted where Telegram permissions allow.
4. If Telegram cloud 2FA is enabled, enter the password in the separate prompt. It is neither
   logged nor stored and its message is deleted where possible.
5. Telethon produces a `StringSession`; the application immediately encrypts it with AES-256-GCM
   and the `personal_telegram_session` authenticated context before PostgreSQL persistence.

No plaintext `.session` file is created. `.gitignore` also blocks accidental `*.session` and
`*.session-journal` files. On startup, the encrypted session is decrypted in memory, reconnected,
and checked for authorization. Revoked/unauthorized sessions become `not_connected` and require an
explicit reconnect; login codes are never requested automatically.

`/telegram_disconnect` removes only this assistant's stored session after confirmation. It does not
log out or revoke the owner's other Telegram devices.

## Monitoring and commands

The first connection performs a bounded silent baseline sync. Historical messages are indexed
without notifications. Afterward, incoming private `NewMessage` events are deduplicated by
`(telegram_chat_id, telegram_message_id)` and may produce an assistant-bot preview. Notifications
may arrive while the assistant is locked, but full reads, searches, drafts, callbacks, and sends are
blocked by the existing owner/lock middleware.

Commands:

- `/telegram` and `/telegram_status`: connection and monitor state.
- `/telegram_connect` and `/telegram_disconnect`: explicit local session management.
- `/tg_recent`: at most the configured recent-message limit.
- `/tg_read`: decrypt and display one selected message in Telegram-safe chunks.
- `/tg_search`: bounded Telethon search; query text is never treated as SQL or shell input.
- `/tg_reply`: select an indexed message and prepare an exact-text reply draft.

Message text and draft text are encrypted at rest. A short sanitized message preview and media type
may be stored for lists and notifications. Photo, video, voice, audio, document, and sticker metadata
is detected, but media is never downloaded or executed in Step 8.

## Confirmation-before-send rule

There is no auto-reply. `/tg_reply` uses the owner's exact text; no LLM rewriting is claimed or
performed. The database stores the encrypted draft as `DRAFT`. Only the owner pressing `Yuborish`
can atomically move it to `SENDING` and invoke MTProto `send_message` with the original
`reply_to_message_id`. A second click, cancelled draft, failed draft, or forged callback ID cannot
send.

If Telegram succeeds and the process crashes before PostgreSQL records `SENT`, perfect exactly-once
delivery is impossible. The draft remains `SENDING`, preventing automatic or second-click resend,
and requires operator review. Flood waits and write restrictions fail safely; the handler never
sleeps for hours or automatically retries a personal message.

## Run and verify

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.run_all
```

Offline verification:

```powershell
.\.venv\Scripts\python.exe -m compileall app tests migrations
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\ruff.exe check .
```

Step 8 does not implement autonomous replies, LLM generation, voice instructions, media download,
CRM, group analytics, or channel monitoring by default. The next planned stage is personal finance
tracking and reporting.

# Stage 1 - Step 9: Personal finance

Step 9 adds owner-scoped expense and income tracking. Monetary input is parsed directly into
`Decimal` and PostgreSQL stores it as `NUMERIC(20, 2)`; binary floating-point is never used for
money. UZS, USD, and EUR are reported independently. The application performs no implicit exchange
rate conversion and never adds different currencies together.

## Configuration

```dotenv
FINANCE_DEFAULT_CURRENCY=UZS
FINANCE_RECENT_LIMIT=10
FINANCE_TOP_CATEGORY_LIMIT=5
```

Apply the new schema and start the combined service:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.run_all
```

The first database-backed application startup idempotently creates 11 expense categories and five
income categories for the owner. Custom categories are supported. Deactivation preserves historical
transactions, and system categories cannot be deactivated.

## Telegram commands

- `/finance`: finance menu and current defaults.
- `/expense` and `/income`: guided entry with amount, currency, category, optional description,
  local date, and an explicit final confirmation.
- `/transactions`: recent non-deleted transactions.
- `/finance_today`, `/finance_week`, `/finance_month`, `/finance_year`: SQL-aggregated reports in
  `Asia/Tashkent`, with totals and top categories separated by currency.
- `/finance_categories`: list, create, or deactivate eligible custom categories.
- `/finance_edit`: edit amount, category, description, or date after confirmation.
- `/finance_delete`: soft-delete a selected transaction after confirmation.

All commands pass through the existing owner authorization and lock middleware. Mutation callbacks
carry a short-lived opaque token, not transaction contents, and each confirmation is single-use.
Dates are interpreted in the configured application timezone. Time-aware event values are stored in
UTC where present. Deleted transactions remain available for audit/history but are excluded from
normal lists and analytics.

Finance audit events contain internal identifiers, transaction type, amount/currency where needed,
and operation state. They do not contain free-text descriptions. Reports are computed by SQL
aggregation rather than loading all transactions into Python.

Offline verification:

```powershell
.\.venv\Scripts\python.exe -m compileall app tests migrations
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe -m alembic upgrade head --sql
```

Step 9 does not include bank synchronization, exchange-rate conversion, OCR, receipt scanning,
budgets, investments, tax calculation, payment execution, or AI financial advice. The next planned
stage is the personal notebook and knowledge-storage foundation.

# Stage 1 - Step 10: Encrypted personal notebook

The Notebook stores journal entries as encrypted AES-256-GCM values in PostgreSQL. There is no
plaintext content preview or full-text index. Projects and normalized tags are metadata; entry text
and link targets remain encrypted. Search decrypts at most a configured number of the owner's most
recent active entries and performs a deterministic case-insensitive substring match.

## Configuration

```dotenv
NOTEBOOK_STORAGE_PATH=./data/notebook
NOTEBOOK_MAX_FILE_SIZE_MB=25
NOTEBOOK_SEARCH_SCAN_LIMIT=500
NOTEBOOK_RECENT_LIMIT=10
NOTEBOOK_ALLOWED_URL_SCHEMES=http,https
```

`DATABASE_URL`, `TELEGRAM_OWNER_ID`, and a Base64-encoded 32-byte `DATA_ENCRYPTION_KEY` are also
required to initialize Notebook. Missing configuration leaves imports and other services working,
while `/health` reports `notebook_storage: not_configured`. A configured but unwritable directory is
reported as unavailable/error rather than healthy.

Apply the schema and start the service:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.run_all
```

Commands are `/notebook`, `/note`, `/notes`, `/note_today`, `/note_date`, `/note_project`,
`/note_tag`, `/note_search`, `/note_attach`, `/note_edit`, `/note_delete`, `/notebook_projects`, and
`/notebook_tags`. The shortcut `/note MATN` still presents an explicit confirmation before saving.
All Notebook messages, callbacks, searches, and attachment downloads require the authorized owner
and an unlocked session.

`/note_attach NOTE_ID` opens an explicit capture session. Images, original OGG/OPUS voice messages,
videos, PDFs, Word/Excel documents, Telegram files, and http/https links can be grouped on that one
entry. Binary files are treated as opaque untrusted data: no execution, macro handling, archive
extraction, OCR, EXIF processing, transcription, or remote URL fetching occurs.

Files are stored below the configured root as `<owner>/<year>/<month>/<uuid>.enc`; user filenames
never become filesystem paths. Each file has a fresh AES-GCM nonce and a plaintext SHA-256 checksum
for retrieval-time integrity validation. PostgreSQL keeps metadata and relative encrypted paths, not
file bytes or absolute server paths. Duplicate checks are scoped to one entry. Failed metadata
commits remove newly written encrypted files.

The current AES-GCM API buffers a bounded file in memory after the Telegram metadata size precheck;
the default limit is 25 MB. Atomic temporary encrypted writes are removed after replacement.
Retrieved plaintext uses an OS temporary file and is deleted in `finally`. An abrupt process or OS
crash can still leave an OS temp artifact; startup scavenging is a future hardening item.

Backups must include both PostgreSQL and the encrypted storage root, plus a separately protected copy
of `DATA_ENCRYPTION_KEY`. Losing the key makes notes and attachments unrecoverable. On Linux, grant
storage access only to the application user. On Windows, use a private application directory rather
than a public/shared folder. Never expose the storage root through a web server.

Offline verification:

```powershell
.\.venv\Scripts\python.exe -m compileall app tests migrations
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe -m alembic upgrade head --sql
```

Step 10 intentionally excludes embeddings, vector databases, LLM semantic search, OCR, document
parsing, voice transcription, automatic tags/summaries, public sharing, and permanent purge. Future
extracted file content remains untrusted data and must never become system instructions or authorize
actions. The next planned stage is task management with due dates, priorities, and reminder/calendar
integration.

# Stage 1 - Step 11: Tasks

Tasks are owner-scoped PostgreSQL records with central `TODO`, `IN_PROGRESS`, `DONE`, and
`CANCELLED` statuses and `LOW`, `NORMAL`, `HIGH`, and `URGENT` priorities. Descriptions are encrypted
with the existing versioned AES-256-GCM service; titles are metadata and are deliberately excluded
from generic logs and task audit details.

```dotenv
TASK_DEFAULT_PRIORITY=NORMAL
TASK_DEFAULT_REMINDER_MINUTES=60
TASK_DATE_ONLY_REMINDER_TIME=09:00
TASK_RECENT_LIMIT=10
```

Apply migration `0008` and run the combined application:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.run_all
```

Commands are `/tasks_menu`, `/task`, `/tasks`, `/task_today`, `/task_tomorrow`, `/task_overdue`,
`/task_done`, `/task_edit`, `/task_delete`, `/task_priority`, `/task_calendar`, and `/task_carry`.
`/task TITLE` starts a quick draft but still asks for due date/time, priority, reminder, Calendar,
and explicit confirmation. All interactive task operations require the authorized owner and an
unlocked session. Existing scheduled reminders can still be delivered while locked.

Timed task values are interpreted in `Asia/Tashkent` and stored as UTC-aware datetimes. Date-only
tasks become overdue after the local day ends. When enabled, a timed reminder defaults to 60 minutes
before due time; a date-only task instead reminds at 09:00 local time on its due date. Past reminder
moments are rejected.

Calendar sync is optional and currently requires a due time. Creation uses a deterministic operation
ID to prevent duplicate Google events; edits and carry-forward update the existing linked event via
its current `etag`. Completing a task leaves its Calendar event unchanged. Deletion soft-deletes the
task and cancels pending reminders but never deletes the Calendar event automatically.

Task metadata is committed before external Reminder/Calendar work. Successful external identifiers
are linked back to the task. If an external service fails, the task remains saved and the caller gets
a warning; this avoids losing the primary task record. Completion and deletion remain authoritative
even if reminder cancellation temporarily fails.

`/task_carry` gathers unfinished tasks due today or earlier and proposes tomorrow. Nothing moves
without a single-use confirmation. Carry-forward preserves a timed task's local wall-clock time and
resynchronizes linked reminders/events. `get_daily_summary()` provides total, done, remaining,
overdue, and urgent counts for future briefing modules.

Step 11 reserves nullable recurrence fields but does not execute recurring tasks. It also excludes
AI/NLP parsing, voice commands, task dependencies, subtasks, Kanban, shared tasks, automatic
carry-forward, and briefing schedulers.

# Stage 1 - Step 12: Assistant and Voice Input

Step 12 adds a replaceable structured-action model client and speech-to-text client. The concrete
development adapters use OpenAI's current Responses structured-output endpoint and audio
transcription endpoint through the existing `httpx` dependency. Imports never contact a provider.
Leave the following values blank to keep AI and STT disabled:

```dotenv
AI_PROVIDER=openai
AI_MODEL=
AI_API_KEY=
AI_TIMEOUT_SECONDS=30
AI_MAX_RETRIES=2
AI_ACTION_CONFIDENCE_THRESHOLD=0.75
AI_MAX_REQUESTS_PER_MINUTE=30
STT_PROVIDER=openai
STT_MODEL=
STT_API_KEY=
STT_MAX_FILE_SIZE_MB=20
STT_TIMEOUT_SECONDS=60
ASSISTANT_CONTEXT_TTL_SECONDS=3600
ASSISTANT_CONTEXT_MAX_MESSAGES=10
```

Normal owner text and Telegram voice messages pass through the same owner and lock middleware.
Voice bytes are size-limited, written to a temporary file only for transcription, and removed in a
`finally` block. The transcript is shown to the owner before routing. Neither transcripts nor input
text are written to audit details.

The model can only return the strict Pydantic discriminated union in
`app/modules/assistant/schemas.py`. It has no service, database, filesystem, shell, Telegram, Gmail,
or Calendar credentials. The backend validates the result, applies a hard-coded confirmation
policy, and invokes an allowlisted existing service method. Creation, mutation, cancellation,
completion, and reply-draft persistence require owner confirmation. Read-only actions execute
immediately after validation. Model-provided `requires_confirmation` and confidence never grant
authorization.

Pending actions are serialized as JSON, expire after 15 minutes, are owner-bound, and are consumed
once. Redis is used when configured; otherwise the development memory store is used and resets on
restart. Conversation context is bounded, expires, and is limited to short owner request excerpts.
Email, Telegram, notebook, document, and web content is untrusted data and may never become system
instructions or authorize actions.

No `SEND_EMAIL` or personal Telegram send action exists. Draft actions only call the existing draft
services. There are no autonomous loops, direct SQL, arbitrary HTTP tools, shell execution,
filesystem tools, plugin execution, or dynamic code execution in the AI layer.

Run the offline suite:

```powershell
.\.venv\Scripts\python.exe -m compileall app tests migrations
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\ruff.exe check .
```

Live AI/STT verification requires explicit provider credentials and should use non-sensitive test
data. Step 12 introduces no database migration. Morning/evening briefing automation remains out of
scope for the next stage.

# Stage 1 - Step 13: Daily Automation

Daily automation produces concise owner-only Morning Briefings and Evening Summaries. Defaults are
08:00 and 20:00 in `Asia/Tashkent`; owner settings are persisted in `daily_settings`. Delivery
identity is persisted in `daily_deliveries` with a unique owner/type/date constraint, preventing a
restart or duplicate scheduler fire from sending the same scheduled report twice.

```dotenv
RUN_DAILY_AUTOMATION=false
DAILY_MORNING_DEFAULT_TIME=08:00
DAILY_EVENING_DEFAULT_TIME=20:00
DAILY_AUTOMATION_GRACE_MINUTES=120
DAILY_DELIVERY_MAX_ATTEMPTS=3
```

Enable `RUN_DAILY_AUTOMATION` only in the Telegram/combined process designated to own scheduled
jobs. When the reminder scheduler exists, daily cron jobs share its APScheduler instance. Otherwise
the daily runtime owns one scheduler. Stable IDs are `daily:morning:<owner>` and
`daily:evening:<owner>`. Startup restores jobs and sends one catch-up report only within the
configured grace window.

Commands are `/daily`, `/daily_settings`, `/morning_now`, and `/evening_now`. Settings and manual
reports require the authenticated owner and an unlocked session. Scheduled reports are delivered to
the configured owner even while locked. Evening task carry-forward uses an opaque, expiring,
single-use confirmation and delegates to `TaskService`; tasks never move automatically.

Sections use existing Calendar, Tasks, Gmail, Reminder, Finance, Notebook, and Personal Telegram
services. Each is isolated so one unavailable integration produces a short unavailable label while
the remaining report is still delivered. Reports contain counts and short Calendar/task metadata,
never email bodies, note content, private message bodies, or audit copies of report text. Finance is
grouped by currency without FX conversion.

Apply migration `0009` and run:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.run_all
```

Offline verification remains `pytest`, `ruff`, `pip check`, `compileall`, and `alembic upgrade head
--sql`. Live scheduled delivery requires PostgreSQL, Telegram credentials, and an available bot.
Step 13 completes the planned Stage 1 code foundation; live integration acceptance remains required
before production deployment.

# Stage 1.5 - Local Runtime Integration

This step verifies the existing application against real local PostgreSQL and Redis services. It
does not configure Telegram, Google, AI, or other external accounts. Use Python 3.12 or newer and
keep all credentials only in the ignored `.env` file.

## Python and dependencies

PowerShell:

```powershell
Set-Location C:\Users\USER\Documents\Agent
python -m venv .venv  # only when .venv does not already exist
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pip check
```

## PostgreSQL development database

Install PostgreSQL 16 or 17 from the official PostgreSQL Windows installer. Use a dedicated,
non-superuser application role. In `psql`, connected as a local administrator, choose your own
strong password and run:

```sql
CREATE USER personal_ai_app WITH LOGIN PASSWORD '<CHOOSE_STRONG_PASSWORD>';
CREATE DATABASE personal_ai OWNER personal_ai_app;
```

Configure `.env` without committing or logging the password:

```dotenv
DATABASE_URL=postgresql+asyncpg://personal_ai_app:<PASSWORD>@localhost:5432/personal_ai
```

Apply and inspect the complete migration chain:

```powershell
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic history
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic upgrade head
```

PostgreSQL should listen only on trusted local/private interfaces. The application URL must use
`postgresql+asyncpg`; SQLAlchemy hides query parameters and the application never logs the URL.

## Redis on Windows

Do not use abandoned unofficial native Windows Redis builds. WSL2 is the preferred local option
when Docker is unavailable. From an administrator PowerShell, install WSL2 and Ubuntu if needed:

```powershell
wsl --install -d Ubuntu
```

After any requested reboot, run inside Ubuntu:

```bash
sudo apt update
sudo apt install redis-server
sudo service redis-server start
redis-cli ping
```

Then configure the Windows application's `.env`:

```dotenv
REDIS_URL=redis://localhost:6379/0
REDIS_KEY_PREFIX=personal_ai
SECURITY_STATE_BACKEND=redis
```

If Redis is explicitly selected and unreachable, startup fails instead of silently falling back to
memory. The memory backend remains suitable only for offline development and loses state on restart.

## Diagnostics, API, and health

The diagnostic uses the application's own managers, redacts connection details, creates only a
short-lived namespaced Redis key, and cleans it up:

```powershell
.\.venv\Scripts\python.exe scripts\check_runtime.py
```

Start the API on the local interface:

```powershell
.\.venv\Scripts\python.exe -m app.run_api
```

Verify `http://127.0.0.1:8000/`, `/health`, `/health/live`, and `/health/ready`. Health output
reports actual dependency states without exposing URLs, IDs, or tokens. Optional external services
may be disabled or not configured; core readiness follows the dependencies selected by runtime
configuration.

Run offline and explicitly enabled real-infrastructure tests separately:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
$env:RUN_INTEGRATION_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest -m integration -v
Remove-Item Env:RUN_INTEGRATION_TESTS
.\.venv\Scripts\python.exe -m compileall app tests migrations scripts
.\.venv\Scripts\python.exe -m ruff check .
```

If diagnostics report `BLOCKED`, confirm the service is running, the localhost port is reachable,
and the corresponding `.env` variable is populated. Never paste full URLs containing passwords into
issues or logs. Integration tests do not mutate application rows; Redis tests use random namespaces,
restore a locked state, and remove their temporary keys.

# Stage 1.5 - Telegram Live Integration

Create the private bot with BotFather, place its token and the fixed numeric owner ID only in the
ignored `.env`, and never paste the token into source, documentation, issues, or logs:

```dotenv
TELEGRAM_BOT_TOKEN=
TELEGRAM_OWNER_ID=
BOT_PIN=
BOT_PIN_HASH=
```

For local development, `BOT_PIN` is accepted and converted to an in-memory Argon2id hash at startup.
The preferred configuration is a persistent Argon2id hash generated through the hidden prompt:

```powershell
.\.venv\Scripts\python.exe scripts\hash_pin.py
```

Put its output in `BOT_PIN_HASH`, clear `BOT_PIN`, and treat the hash as sensitive. Run the read-only
diagnostic, which performs `getMe` and webhook inspection but sends no message:

```powershell
.\.venv\Scripts\python.exe scripts\check_telegram_runtime.py
```

For persistent lock state and audit/user synchronization, first complete the PostgreSQL and Redis
setup above, apply migrations, and configure:

```dotenv
SECURITY_STATE_BACKEND=redis
REDIS_KEY_PREFIX=personal_ai
```

An explicitly selected Redis backend never falls back to memory. A missing Redis lock key means
locked. Failed PIN attempts use namespaced counters and native TTL lockout; no PIN or hash is stored
in Redis. Start exactly one polling process:

```powershell
.\.venv\Scripts\python.exe -m app.bot.run
```

Use the owner account to verify `/start`, `/help`, `/status`, `/id`, `/menu`, `/lock`, a sensitive
command while locked, one wrong PIN, and a correct `/unlock`. From a separate account, `/start` must
return only `Access denied`. Messages and callbacks pass through the same central owner middleware.
Follow [TELEGRAM_LIVE_TEST.md](TELEGRAM_LIVE_TEST.md) and leave the session locked after testing.

Polling registers the implemented command list for the owner chat. If Telegram reports a polling
conflict, stop the duplicate local process. If a webhook was previously configured, inspect it with
the diagnostic and remove it deliberately before polling; this step does not configure production
webhooks. Ctrl+C closes polling, FSM storage, the bot HTTP session, Redis, and the database through
the shared application lifecycle.

Audit rows contain event type and bounded identifiers/command names, never PIN input or message
content. Verify `AUTHORIZED_ACCESS`, `UNAUTHORIZED_ACCESS`, `COMMAND_RECEIVED`, `LOGIN_FAILED`,
`LOGIN_SUCCESS`, `SESSION_LOCKED`, and `SESSION_UNLOCKED` by event type/count only. Do not print full
Settings objects or secret-bearing URLs while troubleshooting.

# Stage 1.5 - Google Calendar and Gmail Live Integration

The existing implementation uses two least-privilege OAuth grants stored as separate encrypted
provider records. Calendar requests `calendar.events` and `calendar.freebusy`; Gmail requests only
`gmail.readonly`. No Gmail send or modify permission is requested, and this project cannot send
email in this stage.

In Google Cloud Console, create/select a project, enable **Google Calendar API** and **Gmail API**,
configure the OAuth consent screen, and add the owner as a test user while the app is in Testing.
Create an OAuth 2.0 **Web application** client and register both redirect URIs exactly:

```text
http://127.0.0.1:8000/oauth/google/callback
http://127.0.0.1:8000/oauth/gmail/callback
```

Configure the ignored `.env`; never commit the values or downloaded client JSON:

```dotenv
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/oauth/google/callback
GOOGLE_CALENDAR_ID=primary
DATA_ENCRYPTION_KEY=
OAUTH_STATE_BACKEND=redis
RUN_GMAIL_MONITOR=false
```

Generate a Base64 URL-safe 32-byte encryption key locally and place only its output in `.env`:

```powershell
.\.venv\Scripts\python.exe -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

PostgreSQL is required for encrypted refresh-token persistence and indexed emails. Redis is
recommended for one-time OAuth state across API/bot processes. Apply migrations, start FastAPI on
`127.0.0.1`, and run the read-only diagnostic:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.run_api
# In another PowerShell window:
.\.venv\Scripts\python.exe scripts\check_google_runtime.py
```

Start the Telegram bot, unlock it, run `/google_connect`, and complete Calendar consent. Gmail uses
the separate `/gmail_connect` flow because expanding an existing Calendar grant cannot silently add
Gmail access. Both flows use PKCE, cryptographic single-use state, a browser-bound HttpOnly cookie,
a ten-minute TTL, offline access, and explicit consent for a refresh token.

After connecting, follow [GOOGLE_LIVE_TEST.md](GOOGLE_LIVE_TEST.md). Calendar mutations operate only
on the clearly named test event and require Telegram confirmation. Gmail tests are read-only;
attachments are metadata-only and incoming email is untrusted data. Enable `RUN_GMAIL_MONITOR=true`
only after the silent initial baseline is established. The persisted checkpoint and unique Gmail
message ID prevent historical floods and duplicate notifications.

If OAuth returns `redirect_uri_mismatch`, compare scheme, host, port, and path character-for-character;
`localhost` and `127.0.0.1` are not interchangeable. If access is denied in Testing mode, add the
Google account as an OAuth test user. Do not repeatedly force refresh or disconnect a working real
account merely for testing. Token refresh uses the official Google authentication library and
rotates an updated refresh token with compare-and-swap semantics.
