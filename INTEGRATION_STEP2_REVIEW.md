# Stage 1.5 - Integration Step 2 Review

## Architecture audit

- Entrypoint: `python -m app.bot.run`.
- Polling is explicit and uses the shared `ApplicationContext`; imports do not start polling.
- Middleware order is safe error handling, central owner authorization, FSM, then lock enforcement.
- Both messages and callback queries require the configured owner in the owner's private chat.
- Lock state defaults to locked. The configured runtime currently uses the memory backend.
- PIN verification uses Argon2id. The current `.env` uses development-only `BOT_PIN`; no PIN value
  is logged or persisted.
- Unlock protection defaults to five attempts and a 300-second lockout. Redis mode uses atomic Lua
  operations and native TTL; memory mode resets on process restart.
- Owner `/start` synchronization is idempotent through the unique Telegram user ID.
- Security audit actions include authorized/unauthorized access, command receipt, login success or
  failure, session lock/unlock, and bot start/stop.

## Live verification

- `getMe`: connected as `@Agent_Azizbek_bot` (bot ID `8938691276`).
- Webhook: inactive, compatible with polling.
- Polling: started successfully with one local instance and stopped after the manual test.
- Owner commands, correct PIN unlock, menu, lock flow, and safe shutdown were observed live.
- Runtime logs recorded command/security event types without message or PIN contents.
- PostgreSQL was not configured, so audit events and owner synchronization could not persist.
- Redis was not configured, so lock persistence, live TTL, lockout, and restart recovery could not
  be accepted.
- A second-account rejection and a deliberate live wrong-PIN attempt were not performed. Their
  middleware, callback, PIN deletion, failure counter, lockout, and safe-error behaviors are covered
  by the offline automated suite.

## Verification commands

- Telegram diagnostic: PASS.
- Full suite: 433 passed, 2 infrastructure integration tests skipped.
- `compileall app tests migrations scripts`: PASS.
- `pip check`: PASS.
- `ruff check .`: PASS.

## Required follow-up

1. Configure real PostgreSQL and apply migration head `0009`.
2. Configure real Redis and set `SECURITY_STATE_BACKEND=redis`.
3. Replace development `BOT_PIN` with a generated `BOT_PIN_HASH`.
4. Complete the unchecked items in `TELEGRAM_LIVE_TEST.md`, ending with `/lock`.

No secret value is included in this review.
