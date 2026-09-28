# Stage 1 - Step 9 Review

## Architecture summary

The finance module owns categories, transactions, reporting, confirmation actions, audit metadata,
and lifecycle seeding. Telegram handlers only coordinate FSM input and presentation; persistence and
validation remain in the service/repository layer. Every query is scoped to the configured owner.

Money uses `Decimal` end to end and `NUMERIC(20, 2)` in PostgreSQL. UZS, USD, and EUR are aggregated
separately without conversion. Transactions are soft-deleted. Create, update, category changes, and
delete operations cross a short-lived, single-use confirmation boundary before persistence.

## Changed files

- `.env.example`
- `README.md`
- `app/core/config.py`
- `app/core/application.py`
- `app/database/models/__init__.py`
- `app/database/models/finance.py`
- `app/modules/audit/actions.py`
- `app/modules/finance/__init__.py`
- `app/modules/finance/actions.py`
- `app/modules/finance/audit.py`
- `app/modules/finance/categories.py`
- `app/modules/finance/exceptions.py`
- `app/modules/finance/repository.py`
- `app/modules/finance/reports.py`
- `app/modules/finance/runtime.py`
- `app/modules/finance/schemas.py`
- `app/modules/finance/service.py`
- `app/modules/finance/utils.py`
- `app/bot/constants.py`
- `app/bot/context.py`
- `app/bot/dispatcher.py`
- `app/bot/runtime.py`
- `app/bot/handlers/finance.py`
- `app/bot/keyboards/finance.py`
- `migrations/versions/0006_finance.py`
- `tests/test_audit_service.py`
- `tests/test_application_lifecycle.py`
- `tests/test_reminder_config_health.py`
- `tests/test_finance_actions.py`
- `tests/test_finance_reports.py`
- `tests/test_finance_service.py`
- `tests/test_finance_utils.py`
- `tests/bot/test_finance_security.py`

## Migration

Migration `0006` creates `finance_categories` and `finance_transactions`, foreign keys, owner/date
indexes, enum constraints, and a positive-amount check. It follows `0005`; no previous migration was
modified. Downgrade removes only the two Step 9 tables.

## Security and privacy decisions

- No bank credentials, payment APIs, or external finance services exist in this stage.
- Free-text transaction descriptions are not copied into audit metadata.
- Locked sessions cannot access finance commands or callbacks.
- Mutation callbacks use opaque action tokens and are idempotent after first use.
- Reports never merge currencies and do not imply exchange rates.
- Soft deletion preserves the audit trail while excluding data from ordinary reports.

## Verification

- Finance-focused tests: 41 passed.
- Full offline suite: 313 passed.
- Live PostgreSQL migration/runtime verification depends on a configured reachable PostgreSQL
  instance and is reported separately from offline validation.

## Current limitations

There is no bank sync, currency conversion, receipt OCR, budgeting, investment tracking, tax logic,
payment initiation, or AI financial advice. PostgreSQL live verification and complete service startup
also require the owner's local infrastructure and credentials.
