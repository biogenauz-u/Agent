# Stage 1 - Step 10 Review

## Architecture

The Notebook module separates ORM persistence, bounded decrypted search, encrypted local storage,
domain validation, confirmation actions, audit, lifecycle, and Telegram presentation. Handlers never
receive storage paths. Every database operation is scoped through the configured owner's internal
user record.

## Encryption and storage

- Note content and link targets use versioned AES-256-GCM envelopes with owner/purpose AAD.
- Files use a fresh nonce and purpose bound to their random storage UUID.
- Files live under `<root>/<owner>/<year>/<month>/<uuid>.enc`.
- Original names are metadata only and are reduced to their final safe path component.
- SHA-256 is calculated over plaintext and checked after decryption.
- The 25 MB default bound limits memory use; metadata is checked before Telegram download when
  available and actual bytes are checked again before storage.
- Writes use a temporary encrypted file, `fsync`, and atomic replacement. DB failures compensate by
  removing the new encrypted file. Retrieval temp files are removed in `finally`.
- Attachments are opaque, untrusted binary data. No parsing, execution, OCR, extraction, or URL fetch
  occurs.

## Database

Migration `0007` follows `0006` and creates `notebook_projects`, `notebook_tags`,
`notebook_entries`, `notebook_entry_tags`, and `notebook_attachments`, including owner/date/project,
tag uniqueness, entry/checksum uniqueness, and attachment indexes. Earlier migrations were not
changed.

## Changed files

- `.env.example`, `.gitignore`, `README.md`
- `app/core/config.py`, `app/core/encryption.py`, `app/core/runtime.py`, `app/core/application.py`
- `app/database/models/__init__.py`, `app/database/models/notebook.py`
- `app/modules/audit/actions.py`
- `app/modules/notebook/__init__.py`, `actions.py`, `audit.py`, `exceptions.py`, `repository.py`,
  `runtime.py`, `schemas.py`, `search.py`, `service.py`, `storage.py`, `utils.py`
- `app/bot/constants.py`, `context.py`, `dispatcher.py`, `lifecycle.py`
- `app/bot/handlers/notebook.py`, `app/bot/keyboards/notebook.py`
- `app/api/routes/health.py`, `app/api/schemas/health.py`
- `migrations/versions/0007_notebook.py`
- `tests/test_api.py`, `tests/test_audit_service.py`
- `tests/test_notebook_actions.py`, `tests/test_notebook_service.py`,
  `tests/test_notebook_storage.py`, `tests/bot/test_notebook_security.py`

## Verification

- Notebook-focused suite: 36 passed.
- Complete offline regression suite: 349 passed.
- Ruff, compileall, and pip dependency checks: passed.
- Local FastAPI root/health smoke test: passed; Notebook truthfully reported `not_configured`
  without live infrastructure.
- Alembic upgrade SQL through `0007`: passed offline.
- Final suite and quality command results are recorded in the completion response.

## Runtime blockers

Live PostgreSQL, Telegram file transfer, and full combined runtime verification require the owner's
real local infrastructure and credentials. Automated tests use isolated SQLite, temporary
directories, test-only encryption keys, and offline Telegram transport.
