# Stage 1 - Step 11 Review

## Architecture

The Tasks module contains typed schemas, repository queries, encrypted-description service logic,
SQL daily summaries, Reminder and Calendar adapters, audit, single-use confirmation actions, and a
small runtime composition root. Telegram handlers only collect deterministic input and call actions.

## Persistence

Migration `0008` follows `0007` and creates `tasks` with owner, status, priority, date/time,
completion, integration linkage, future recurrence fields, and soft-delete state. Indexes cover
owner, status, priority, due date/time, deletion, and common owner/status/due queries. Previous
migrations were not edited.

Descriptions are AES-256-GCM encrypted with owner/purpose AAD. Audit metadata contains IDs, status,
priority, and due date where required, never the description or title.

## Reminder and Calendar behavior

- The existing persistent ReminderService/scheduler is reused; no second scheduler exists.
- Timed reminders use the selected/default offset. Date-only tasks use 09:00 local by default.
- Complete/delete cancels a pending linked reminder; delivered history remains intact.
- Calendar create uses a deterministic task operation ID and updates use the current `etag`.
- Calendar sync requires due time in this stage. Completion never deletes its Calendar event.
- Carry-forward reschedules the linked reminder and updates the existing Calendar event.
- Primary task persistence survives external failures and reports warnings.

## Changed files

- `.env.example`, `README.md`
- `app/core/config.py`, `app/core/application.py`
- `app/database/models/__init__.py`, `app/database/models/task.py`
- `app/modules/audit/actions.py`
- `app/modules/tasks/__init__.py`, `actions.py`, `audit.py`, `calendar_sync.py`, `exceptions.py`,
  `reminders.py`, `reports.py`, `repository.py`, `runtime.py`, `schemas.py`, `service.py`, `utils.py`
- `app/bot/constants.py`, `context.py`, `dispatcher.py`, `lifecycle.py`
- `app/bot/handlers/tasks.py`, `app/bot/keyboards/tasks.py`
- `migrations/versions/0008_tasks.py`
- `tests/test_audit_service.py`, `tests/test_task_actions.py`, `tests/test_task_reminders.py`,
  `tests/test_task_service.py`, `tests/bot/test_task_security.py`

## Verification

- Task-focused offline suite: 30 passed.
- Complete offline regression suite: 379 passed.
- Ruff, compileall, and dependency checks: passed.
- Local FastAPI root/health smoke test: passed with unconfigured dependencies reported truthfully.
- Alembic offline upgrade SQL through `0008`: passed.
- Final regression and quality results are recorded in the completion response.

## Runtime blockers

Live PostgreSQL, Google Calendar, Telegram commands, scheduled delivery, and full combined runtime
verification require the owner's real infrastructure and credentials. Unit tests use SQLite,
test-only encryption keys, controlled UTC time, and mocked Calendar/Reminder ports.
