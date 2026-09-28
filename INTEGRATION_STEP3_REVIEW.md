# Stage 1.5 - Integration Step 3 Review

## Existing architecture

- Calendar and Gmail use separate OAuth flows and separate encrypted credential providers:
  `google_calendar` and `google_gmail`.
- Calendar scopes are `calendar.events` and `calendar.freebusy`.
- Gmail scope is only `gmail.readonly`; neither send nor modify scope exists.
- OAuth uses a Web application client, PKCE, cryptographic state, browser binding, single-use state,
  ten-minute state/cookie lifetime, offline access, and an HttpOnly SameSite cookie.
- Refresh tokens are AES-256-GCM encrypted with a versioned random-nonce envelope bound to owner and
  provider. Access tokens remain in memory. Refresh-token rotation uses compare-and-swap.
- Calendar supports list/create/get/update/delete and free/busy through an async REST client.
- Gmail supports profile, bounded list/search, message/thread reads, and history polling without
  attachment downloads. Initial sync is silent and persistent state prevents duplicate alerts.
- Telegram exposes the implemented Calendar and Gmail commands behind owner and lock middleware.

## Current configuration and blockers

The existing `.env` was inspected by variable name/status only. Google client ID, client secret,
redirect URI, encryption key, and Gmail monitor setting are absent. PostgreSQL and Redis URLs are
empty. Therefore no real authorization, credential row, Calendar mutation, Gmail read, monitor,
restart recovery, or persistent audit can be truthfully verified.

Required Google Cloud redirect URIs:

1. `http://127.0.0.1:8000/oauth/google/callback`
2. `http://127.0.0.1:8000/oauth/gmail/callback`

`GOOGLE_REDIRECT_URI` must be the first URI. The Gmail flow safely derives the second URI from the
same origin. Both must be registered on the same Web application OAuth client.

## Changes and verification

- Added a read-only, secret-safe Google configuration and encrypted-row diagnostic.
- Added a manual Calendar/Gmail live checklist.
- Added exact Google Cloud, environment, callback, consent, and troubleshooting documentation.
- Diagnostic result: OAuth `NOT_CONFIGURED`, database `NOT_CONFIGURED`, both credentials `BLOCKED`.
- Confirmed Calendar least-privilege scopes and Gmail read-only scope; `gmail.send` is absent.
- Full suite: 433 passed, 2 infrastructure tests skipped.
- Compile, dependency consistency, and Ruff checks: PASS.

No live event or email was created, modified, deleted, downloaded, or sent. No OAuth state key or
Google credential was created. No secret value is included in this report.
