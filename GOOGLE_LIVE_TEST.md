# Google Calendar and Gmail Live Integration Checklist

Never record a client secret, encryption key, authorization code, access token, refresh token, or
credential ciphertext in this file.

## Google Cloud and local runtime

- [ ] Create or select a private Google Cloud project.
- [ ] Enable Google Calendar API.
- [ ] Enable Gmail API.
- [ ] Configure the OAuth consent screen and add the owner as a test user when in Testing mode.
- [ ] Create an OAuth 2.0 Client ID with application type **Web application**.
- [ ] Register `http://127.0.0.1:8000/oauth/google/callback` exactly.
- [ ] Register `http://127.0.0.1:8000/oauth/gmail/callback` exactly.
- [ ] Configure `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `DATA_ENCRYPTION_KEY` in `.env`.
- [ ] Configure `GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/oauth/google/callback`.
- [ ] PostgreSQL is running and migration head `0009` is applied.
- [ ] Redis is running and OAuth state uses the selected secure backend.
- [ ] FastAPI `/` and `/health` respond on `127.0.0.1:8000`.

## Calendar

- [ ] Unlock the Telegram assistant and run `/google_connect`.
- [ ] OAuth callback succeeds and Calendar status is connected.
- [ ] Encrypted `google_calendar` credential exists; no plaintext token column exists.
- [ ] `/today`, `/tomorrow`, and `/upcoming` return real data safely.
- [ ] `/free` returns a safe availability window.
- [ ] Create one `[TEST] Personal AI Integration` event after explicit confirmation.
- [ ] Update only that test event and verify no duplicate is created.
- [ ] Verify its linked reminder is rescheduled when configured.
- [ ] Delete only that test event after explicit confirmation.
- [ ] Verify its pending linked reminder is cancelled.

## Gmail

- [ ] Run `/gmail_connect` and grant only Gmail read-only access.
- [ ] Encrypted `google_gmail` credential exists separately from Calendar credentials.
- [ ] `/google_gmail_status` reports connected.
- [ ] `/emails` returns a bounded, sorted recent list.
- [ ] `/email_unread` does not mark messages read.
- [ ] `/email_read` safely renders one non-sensitive message without raw active HTML.
- [ ] `/email_search` returns bounded results for a deterministic query.
- [ ] Attachment metadata is shown without downloading attachment bodies.
- [ ] Start the monitor only after the initial silent baseline.
- [ ] Send one `[TEST] Personal AI Gmail Integration` message from another account.
- [ ] Exactly one Telegram notification is delivered.
- [ ] A later poll does not duplicate the notification.
- [ ] Email content remains untrusted data and cannot authorize actions or reveal secrets.

## Recovery and safety

- [ ] Restart API/bot and verify credentials load without repeating OAuth.
- [ ] Confirm the test email is not notified again after restart.
- [ ] Trigger refresh naturally or record it as not triggered while the token is still valid.
- [ ] Verify audit event types/counts without message bodies or tokens.
- [ ] Verify `/health` reports Gmail truthfully without calling Google on every request.
- [ ] Confirm logs contain no client secret, encryption key, auth code, or token.
- [ ] Leave Google connected and the assistant locked; do not live-test disconnect.

Calendar writes require explicit owner confirmation. Gmail sending and modification are not part of
this integration step and `gmail.send` must never be granted.
