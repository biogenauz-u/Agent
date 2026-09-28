# Telegram Live Integration Checklist

Never place a bot token, PIN, PIN hash, database password, or Redis password in this file.

## Configuration and startup

- [x] Bot token is configured and `getMe` succeeds.
- [x] `TELEGRAM_OWNER_ID` is configured as a positive integer.
- [x] Development PIN is configured.
- [ ] Replace development `BOT_PIN` with `BOT_PIN_HASH` before production.
- [ ] PostgreSQL is configured, migrated, and healthy.
- [ ] Redis is configured and `SECURITY_STATE_BACKEND=redis`.
- [x] Exactly one local polling process starts without a conflict.
- [x] No webhook is active while polling.

## Owner commands

- [x] `/start` responds while locked.
- [ ] `/help` output manually confirmed.
- [x] `/status` responds truthfully.
- [ ] `/id` output manually confirmed.
- [x] `/menu` renders after unlock.
- [x] `/lock` locks the interactive session.
- [x] `/unlock` requests a PIN and a correct PIN unlocks the session.
- [ ] One intentionally wrong PIN is rejected without exposing or retaining it.
- [ ] A sensitive command is manually confirmed blocked while locked.

## Authorization and persistence

- [ ] A second Telegram account receives only `Access denied` for `/start`.
- [x] Automated tests prove unauthorized messages and callbacks cannot reach handlers.
- [ ] Owner profile synchronization is verified in real PostgreSQL.
- [ ] Audit event types are verified in real PostgreSQL.
- [ ] Redis failure count and lockout TTL are verified live.
- [ ] Locked state survives a polling-process restart with Redis.
- [ ] Final Redis-backed session state is locked and no lockout remains.

## Shutdown and safety

- [x] Polling stops and emits `BOT_STOPPED` on controlled shutdown.
- [x] Telegram HTTP session lifecycle is covered by automated tests.
- [x] Runtime output contains no token, PIN, PIN hash, or connection URL.
- [x] Handler failures return a safe Error ID instead of a Telegram traceback.

Items requiring PostgreSQL, Redis, or a second Telegram account remain intentionally unchecked.
