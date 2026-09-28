"""Owner-issued start ticket, browser-bound state and PKCE; all tickets single use."""

import asyncio
import hashlib
import logging
import secrets
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx
from google_auth_oauthlib.flow import Flow
from pydantic import SecretStr

from app.core.config import Settings
from app.core.logging import report_error
from app.modules.audit.actions import AuditAction
from app.modules.calendar.audit import CalendarAudit
from app.modules.calendar.auth import SCOPES, TOKEN_URI, require_google
from app.modules.calendar.credentials import GoogleCredentialStore
from app.modules.calendar.exceptions import (
    CalendarConfigurationError,
    GoogleCalendarAuthenticationError,
    OAuthStateError,
)
from app.modules.calendar.state import TemporaryStore
from app.modules.security.lock_service import LockService


class GoogleOAuthService:
    def __init__(
        self,
        settings: Settings,
        store: GoogleCredentialStore,
        states: TemporaryStore,
        lock: LockService,
        audit: CalendarAudit,
        http: httpx.AsyncClient,
    ) -> None:
        self.settings, self.store, self.states = settings, store, states
        self.lock, self.audit, self.http = lock, audit, http

    def configured(self) -> None:
        require_google(self.settings)
        uri = urlsplit(self.settings.google_redirect_uri or "")
        local = uri.hostname in {"localhost", "127.0.0.1", "::1"}
        if (uri.scheme != "https" and not (local and uri.scheme == "http")) or (
            not uri.hostname
            or uri.path != "/oauth/google/callback"
            or uri.query
            or uri.fragment
            or uri.username is not None
            or uri.password is not None
        ):
            raise CalendarConfigurationError(
                "GOOGLE_REDIRECT_URI must use HTTPS or loopback HTTP and /oauth/google/callback."
            )
        self.store.require_configured()

    async def unlocked(self) -> None:
        if await self.lock.is_locked():
            raise OAuthStateError(
                "Owner session is locked. Unlock in Telegram and restart connection."
            )

    def flow(self, state: str, verifier: str) -> Flow:
        assert self.settings.google_client_id and self.settings.google_client_secret
        return Flow.from_client_config(
            {
                "web": {
                    "client_id": self.settings.google_client_id.get_secret_value(),
                    "client_secret": self.settings.google_client_secret.get_secret_value(),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": TOKEN_URI,
                }
            },
            scopes=SCOPES,
            state=state,
            code_verifier=verifier,
            redirect_uri=self.settings.google_redirect_uri,
        )

    async def connect_url(self) -> str:
        self.configured()
        await self.unlocked()
        ticket = await self.states.issue("start", {"owner": self.settings.telegram_owner_id})
        uri = urlsplit(self.settings.google_redirect_uri or "")
        return f"{uri.scheme}://{uri.netloc}/oauth/google/start?{urlencode({'ticket': ticket})}"

    async def begin(self, ticket: str, browser: str) -> str:
        self.configured()
        await self.unlocked()
        pending = await self.states.consume("start", ticket)
        if not pending or pending["owner"] != self.settings.telegram_owner_id:
            raise OAuthStateError("Invalid or expired connection link. Use /google_connect again.")
        verifier = secrets.token_urlsafe(64)
        state = await self.states.issue(
            "oauth",
            {
                "owner": self.settings.telegram_owner_id,
                "verifier": verifier,
                "browser": hashlib.sha256(browser.encode()).hexdigest(),
            },
        )
        flow = self.flow(state, verifier)
        try:
            url, _ = flow.authorization_url(access_type="offline", prompt="consent", state=state)
            return url
        finally:
            flow.oauth2session.close()

    async def exchange(self, code: str, state: str, verifier: str) -> SecretStr:
        def exchange_sync() -> SecretStr:
            flow = self.flow(state, verifier)
            try:
                token: dict[str, Any] = flow.fetch_token(code=code, timeout=15)
                scope = token.get("scope", [])
                granted = set(scope.split() if isinstance(scope, str) else scope)
                if not token.get("refresh_token") or not set(SCOPES).issubset(granted):
                    raise GoogleCalendarAuthenticationError(
                        "Required Calendar permissions were not granted."
                    )
                return SecretStr(token["refresh_token"])
            finally:
                flow.oauth2session.close()

        try:
            return await asyncio.to_thread(exchange_sync)
        except Exception as error:  # noqa: BLE001 - SDK boundary, safely logged without payloads
            report_error(logging.getLogger(__name__), error)
            raise GoogleCalendarAuthenticationError(
                "Google authorization failed. Use /google_connect again."
            ) from None

    async def callback(self, state: str, code: str, browser: str) -> None:
        self.configured()
        pending = await self.states.consume("oauth", state)
        if (
            not pending
            or pending["owner"] != self.settings.telegram_owner_id
            or not secrets.compare_digest(
                pending["browser"], hashlib.sha256(browser.encode()).hexdigest()
            )
        ):
            raise OAuthStateError("Invalid or expired OAuth state.")
        await self.unlocked()
        if not code:
            raise OAuthStateError("Google authorization was cancelled. Use /google_connect again.")
        token = await self.exchange(code, state, pending["verifier"])
        await self.unlocked()
        await self.store.save(token)
        await self.audit.record(AuditAction.GOOGLE_CALENDAR_CONNECTED)

    async def disconnect(self) -> bool:
        token = await self.store.load()
        # Delete locally first: remote revocation outage must never retain the stored token.
        await self.store.delete()
        revoked = token is None
        if token:
            try:
                response = await self.http.post(
                    "https://oauth2.googleapis.com/revoke", data={"token": token.get_secret_value()}
                )
                revoked = response.status_code == 200
            except httpx.RequestError:
                logging.getLogger(__name__).warning("google_revocation_unavailable")
        await self.audit.record(AuditAction.GOOGLE_CALENDAR_DISCONNECTED)
        return revoked
