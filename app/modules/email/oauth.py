import asyncio
import hashlib
import secrets
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

from google_auth_oauthlib.flow import Flow
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.audit.actions import AuditAction
from app.modules.calendar.auth import TOKEN_URI
from app.modules.calendar.credentials import GoogleCredentialStore
from app.modules.calendar.state import TemporaryStore
from app.modules.email.audit import EmailAudit
from app.modules.email.client import GMAIL_SCOPES
from app.modules.email.exceptions import GmailAuthenticationError, GmailConfigurationError
from app.modules.security.lock_service import LockService


def granted_scopes(value: object) -> set[str]:
    """Normalize OAuth scope values returned as either text or a sequence."""
    if isinstance(value, str):
        return set(value.split())
    if isinstance(value, (list, tuple, set)):
        return {str(scope) for scope in value}
    return set()


class GmailOAuthService:
    def __init__(self, settings: Settings, store: GoogleCredentialStore, states: TemporaryStore, lock: LockService, audit: EmailAudit) -> None:
        self.settings, self.store, self.states, self.lock, self.audit = settings, store, states, lock, audit

    @property
    def redirect_uri(self) -> str:
        uri = urlsplit(self.settings.google_redirect_uri or "")
        return urlunsplit((uri.scheme, uri.netloc, "/oauth/gmail/callback", "", ""))

    def configured(self) -> None:
        uri = urlsplit(self.redirect_uri)
        if not self.settings.google_client_id or not self.settings.google_client_secret or not uri.hostname or (uri.scheme != "https" and not (uri.scheme == "http" and uri.hostname in {"localhost", "127.0.0.1", "::1"})):
            raise GmailConfigurationError("Google OAuth and a secure redirect URI are required.")
        self.store.require_configured()

    async def _unlocked(self) -> None:
        if await self.lock.is_locked():
            raise GmailAuthenticationError("Owner session is locked.")

    def _flow(self, state: str, verifier: str) -> Flow:
        assert self.settings.google_client_id and self.settings.google_client_secret
        return Flow.from_client_config({"web": {"client_id": self.settings.google_client_id.get_secret_value(), "client_secret": self.settings.google_client_secret.get_secret_value(), "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": TOKEN_URI}}, scopes=GMAIL_SCOPES, state=state, code_verifier=verifier, redirect_uri=self.redirect_uri)

    async def connect_url(self) -> str:
        self.configured()
        await self._unlocked()
        ticket = await self.states.issue("gmail_start", {"owner": self.settings.telegram_owner_id})
        uri = urlsplit(self.redirect_uri)
        return f"{uri.scheme}://{uri.netloc}/oauth/gmail/start?{urlencode({'ticket': ticket})}"

    async def begin(self, ticket: str, browser: str) -> str:
        self.configured()
        await self._unlocked()
        pending = await self.states.consume("gmail_start", ticket)
        if not pending or pending["owner"] != self.settings.telegram_owner_id:
            raise GmailAuthenticationError("Invalid or expired Gmail connection link.")
        verifier = secrets.token_urlsafe(64)
        state = await self.states.issue("gmail_oauth", {"owner": self.settings.telegram_owner_id, "verifier": verifier, "browser": hashlib.sha256(browser.encode()).hexdigest()})
        flow = self._flow(state, verifier)
        try:
            url, _ = flow.authorization_url(access_type="offline", prompt="consent", state=state)
            return url
        finally:
            flow.oauth2session.close()

    async def callback(self, state: str, code: str, browser: str) -> None:
        pending = await self.states.consume("gmail_oauth", state)
        if not pending or pending["owner"] != self.settings.telegram_owner_id or not secrets.compare_digest(pending["browser"], hashlib.sha256(browser.encode()).hexdigest()):
            raise GmailAuthenticationError("Invalid or expired Gmail OAuth state.")
        await self._unlocked()

        def exchange() -> SecretStr:
            flow = self._flow(state, pending["verifier"])
            try:
                token: dict[str, Any] = flow.fetch_token(code=code, timeout=15)
                granted = granted_scopes(token.get("scope"))
                if not token.get("refresh_token") or not set(GMAIL_SCOPES).issubset(granted):
                    raise GmailAuthenticationError("Gmail read/send permission was not granted.")
                return SecretStr(str(token["refresh_token"]))
            finally:
                flow.oauth2session.close()

        try:
            token = await asyncio.to_thread(exchange)
        except GmailAuthenticationError:
            raise
        except Exception:  # noqa: BLE001 - Google SDK boundary; payload is never exposed
            raise GmailAuthenticationError("Gmail authorization failed safely.") from None
        await self.store.save(token)
        await self.audit.record(AuditAction.GMAIL_CONNECTED)

    async def disconnect(self) -> None:
        await self.store.delete()
        await self.audit.record(AuditAction.GMAIL_DISCONNECTED)
