# Stage 1 - Step 7 Review

## Architecture

Gmail is a read-only module composed by the existing `ApplicationContext`. It reuses the shared
database, Redis-backed OAuth state when selected, lock service, Telegram bot, audit layer, and
AES-GCM key infrastructure. Calendar and Gmail credentials remain separate provider records.
The monitor is explicit, cancellation-safe, bounded by configuration, and starts only when both
monitoring is enabled and a Gmail credential exists.

## Privacy and safety decisions

- OAuth scope is exactly `gmail.readonly`; the code has no email-send method.
- Clean text and summaries are encrypted with distinct authenticated encryption contexts.
- Raw MIME, HTML, remote resources, and attachment bodies are not stored or downloaded.
- Attachment filename/type/size/id metadata only is indexed.
- Email is untrusted data and cannot trigger tools or override system instructions.
- Initial synchronization sends no Telegram notifications.
- Full reads and draft interactions pass through the existing owner and lock middleware.
- Audit records contain internal IDs only, never email bodies, OAuth codes, or tokens.

## Files created

- `app/database/models/email.py`
- `app/modules/email/__init__.py`
- `app/modules/email/audit.py`
- `app/modules/email/client.py`
- `app/modules/email/delivery.py`
- `app/modules/email/drafts.py`
- `app/modules/email/exceptions.py`
- `app/modules/email/monitor.py`
- `app/modules/email/oauth.py`
- `app/modules/email/parser.py`
- `app/modules/email/repository.py`
- `app/modules/email/runtime.py`
- `app/modules/email/schemas.py`
- `app/modules/email/service.py`
- `app/modules/email/summarizer.py`
- `app/modules/email/utils.py`
- `app/bot/handlers/email.py`
- `app/api/routes/gmail_oauth.py`
- `migrations/versions/0004_emails.py`
- `tests/test_email_foundation.py`
- `tests/test_email_model.py`
- `tests/test_email_parser.py`
- `tests/test_gmail_client.py`
- `STEP7_REVIEW.md`

## Files changed

- `.env.example`
- `README.md`
- `app/api/app.py`
- `app/api/routes/health.py`
- `app/api/schemas/health.py`
- `app/bot/constants.py`
- `app/bot/context.py`
- `app/bot/dispatcher.py`
- `app/bot/lifecycle.py`
- `app/core/application.py`
- `app/core/config.py`
- `app/core/encryption.py`
- `app/core/runtime.py`
- `app/database/models/__init__.py`
- `app/modules/audit/actions.py`
- `app/modules/calendar/credentials.py`
- `app/modules/calendar/repository.py`
- `tests/test_api.py`
- `tests/test_audit_service.py`

All complete final contents are in the listed repository paths; no generated fragment or omitted
placeholder was used.

## Migration

Revision `0004` creates `emails` and `integration_states`, with the Gmail ID uniqueness,
thread/date/unread indexes, owner/date composite index, encrypted payload columns, notification
checkpoint, and persistent history checkpoint. Previous migrations were not modified.

## Verification

- Compile: PASS
- Ruff: PASS
- Alembic offline upgrade SQL: PASS
- Unit and regression suite: 235 PASS
- Live PostgreSQL: BLOCKED unless a configured server is reachable
- Live Gmail OAuth and monitoring: BLOCKED without owner consent and Google credentials

## Runtime notes

Register the derived `/oauth/gmail/callback` URI in Google Cloud, migrate PostgreSQL, use
`/gmail_connect`, then enable `RUN_GMAIL_MONITOR=true`. No email is sent by Step 7.
