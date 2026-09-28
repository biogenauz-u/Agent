# Stage 1 - Step 8 Review

## Architecture

The assistant bot remains the sole authenticated control channel. A dedicated Telethon-based
personal-account module owns MTProto client construction, encrypted session persistence, incoming
event normalization, bounded initial synchronization, local message indexing, reply drafts, and
explicitly confirmed sends. The shared `ApplicationContext` creates at most one personal client and
closes its monitor/client before shared database shutdown.

## Session security

- Telethon uses `StringSession`; no plaintext `.session` file is created.
- The StringSession is encrypted through the existing AES-256-GCM facility with a distinct
  `personal_telegram_session` authenticated context.
- API hash, login code, 2FA password, and StringSession never enter audit records or health output.
- Login code and password live only for the active call; assistant messages containing them are
  deleted where Bot API permissions allow.
- Session `repr` is redacted through `SecretStr` and `repr=False` containers.
- Local disconnect removes this assistant's stored session without revoking other Telegram devices.

## Database changes

Migration `0005` adds:

- `telegram_sessions`: one encrypted active session per owner.
- `telegram_messages`: encrypted text, bounded preview, media metadata, and unique remote identity.
- `telegram_reply_drafts`: encrypted drafts with DRAFT/SENDING/SENT/CANCELLED/FAILED states.

All Telegram peer/account/message identifiers use BIGINT. Previous migrations were not changed.

## Confirmation workflow

Owner input creates an encrypted DRAFT without sending. The send callback contains only an internal
draft ID. Service-side owner/status/target validation atomically claims DRAFT as SENDING, then calls
Telethon with the persisted chat and reply IDs. Success becomes SENT; a provider failure becomes
FAILED. No automatic retry exists. A process crash after remote success but before local SENT can
leave SENDING; this deliberately prevents blind duplicate delivery and needs manual review.

## Prompt-injection boundary

Personal Telegram content is untrusted external DATA. It may be encrypted, indexed, displayed, or
used later by a constrained summarizer, but it cannot authorize tools, sending, secret disclosure,
or system actions. Only authenticated, unlocked owner interaction in the assistant bot may confirm
a send.

## Files created

- `app/database/models/personal_telegram.py`
- `app/modules/personal_telegram/__init__.py`
- `app/modules/personal_telegram/audit.py`
- `app/modules/personal_telegram/client.py`
- `app/modules/personal_telegram/delivery.py`
- `app/modules/personal_telegram/draft_service.py`
- `app/modules/personal_telegram/exceptions.py`
- `app/modules/personal_telegram/monitor.py`
- `app/modules/personal_telegram/repository.py`
- `app/modules/personal_telegram/runtime.py`
- `app/modules/personal_telegram/schemas.py`
- `app/modules/personal_telegram/service.py`
- `app/modules/personal_telegram/session_store.py`
- `app/modules/personal_telegram/utils.py`
- `app/bot/handlers/personal_telegram.py`
- `app/bot/keyboards/personal_telegram.py`
- `migrations/versions/0005_personal_telegram.py`
- `tests/test_personal_telegram_client.py`
- `tests/test_personal_telegram_monitor.py`
- `tests/test_personal_telegram_service.py`
- `tests/test_personal_telegram_session.py`
- `tests/bot/test_personal_telegram_security.py`
- `STEP8_REVIEW.md`

## Files changed

- `.env.example`
- `.gitignore`
- `README.md`
- `pyproject.toml`
- `app/api/routes/health.py`
- `app/api/schemas/health.py`
- `app/bot/constants.py`
- `app/bot/context.py`
- `app/bot/dispatcher.py`
- `app/bot/lifecycle.py`
- `app/core/application.py`
- `app/core/config.py`
- `app/core/runtime.py`
- `app/database/models/__init__.py`
- `app/modules/audit/actions.py`
- `tests/test_api.py`
- `tests/test_audit_service.py`

Complete final contents live at the paths above; implementation files contain no omitted-code
placeholders.

## Verification

- Existing and new offline tests: 272 PASS.
- Ruff: PASS.
- Python compilation: PASS.
- Telethon dependency installation: PASS.
- Live PostgreSQL, MTProto authorization, incoming monitoring, and confirmed send require owner
  infrastructure/consent and were not claimed as verified.
