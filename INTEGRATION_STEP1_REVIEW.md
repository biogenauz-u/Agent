# Stage 1.5 - Integration Step 1 Review

## Scope

This review covers only local core runtime integration: Python, dependencies, PostgreSQL, Redis,
Alembic, FastAPI, health endpoints, diagnostics, and tests. No external account credentials or new
product features were added.

## Repository and runtime audit

- Required Python: 3.12 or newer; active virtual environment: Python 3.12.10.
- Dependency management: `pyproject.toml`, editable install with the `dev` extra.
- Database URL contract: `postgresql+asyncpg://...`; secret-wrapped and validated lazily.
- Redis URL contract: `redis://...` or `rediss://...`; secret-wrapped and validated lazily.
- Migration chain: linear `0001` through `0009`, one head (`0009`), nine migrations.
- Database and Redis managers already use explicit initialization and lifecycle-owned cleanup.
- FastAPI entrypoint: `python -m app.run_api`.
- Telegram entrypoint: `python -m app.bot.run`.
- Combined entrypoint: `python -m app.run_all`.
- `.env` exists and remains ignored. `DATABASE_URL` and `REDIS_URL` are empty;
  `SECURITY_STATE_BACKEND` and `REDIS_KEY_PREFIX` are absent, so validated defaults apply.
- Local PostgreSQL, Redis, Docker, and a usable WSL distribution were not available. Ports 5432
  and 6379 were closed. No OS-level installation was attempted.

## Changes

- Added a secret-safe runtime diagnostic using the application's existing managers.
- Added opt-in, non-destructive real PostgreSQL and Redis integration tests.
- Registered the `integration` pytest marker.
- Added PowerShell-first local PostgreSQL/Redis setup and verification documentation.

## Verification

- Dependency install: PASS (`pip install -e ".[dev]`).
- `pip check`: PASS, no broken requirements.
- `compileall app tests migrations scripts`: PASS.
- `ruff check .`: PASS.
- Default suite: 433 passed, 2 integration tests skipped.
- Explicit integration selection: 2 skipped, 433 deselected because URLs/services are absent.
- Alembic head/history: PASS; one head at `0009`.
- Alembic offline upgrade SQL through head: PASS.
- Alembic `current` and real `upgrade head`: BLOCKED by missing `DATABASE_URL`.
- FastAPI real process startup on `127.0.0.1:8000`: PASS.
- `GET /`: HTTP 200, expected application identity.
- `GET /health`: HTTP 200, `degraded`; database and Redis truthfully `not_configured`.
- `GET /health/live`: HTTP 200, `alive`.
- `GET /health/ready`: HTTP 200, `ready` under the current optional-dependency configuration.
- Runtime diagnostic: PASS as a diagnostic; it safely reports both infrastructure checks BLOCKED.
- API process stopped and port 8000 was released.

## Expected schema

The migrations define 19 application tables, plus PostgreSQL's `alembic_version` table after
upgrade: `users`, `audit_logs`, `google_credentials`, `reminders`, `emails`,
`integration_states`, `telegram_sessions`, `telegram_messages`, `telegram_reply_drafts`,
`finance_categories`, `finance_transactions`, `notebook_projects`, `notebook_tags`,
`notebook_entries`, `notebook_entry_tags`, `notebook_attachments`, `tasks`, `daily_settings`, and
`daily_deliveries`.

## Blockers

1. Install and start PostgreSQL 16 or 17, create the dedicated `personal_ai_app` role and
   `personal_ai` database, then set `DATABASE_URL` in `.env`.
2. Install and start Redis through WSL2 (recommended on this Windows host), then set `REDIS_URL`,
   `REDIS_KEY_PREFIX=personal_ai`, and `SECURITY_STATE_BACKEND=redis` in `.env`.
3. Run `python scripts/check_runtime.py`, `alembic upgrade head`, and the integration-marked tests
   again. Until then, server versions, live table count, Redis DB selection, TTL behavior, and
   persistent lock state cannot be truthfully accepted.

No passwords, URLs, tokens, PINs, or key material are recorded in this report.
