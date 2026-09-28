import asyncio
import base64
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Any, Protocol

import httpx
import requests
from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.calendar.auth import TOKEN_URI
from app.modules.calendar.credentials import CredentialStore
from app.modules.email.exceptions import (
    GmailAuthenticationError,
    GmailMessageNotFoundError,
    GmailPermissionError,
    GmailRateLimitError,
    GmailUnavailableError,
)

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GMAIL_SCOPES = [GMAIL_READONLY_SCOPE, GMAIL_SEND_SCOPE]
BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"


class AccessTokenProvider(Protocol):
    async def access_token(self) -> str: ...


class GmailTokenProvider:
    def __init__(self, settings: Settings, store: CredentialStore) -> None:
        self.settings, self.store = settings, store
        self._lock = asyncio.Lock()
        self._credentials: Credentials | None = None
        self._source: SecretStr | None = None

    def invalidate(self) -> None:
        self._credentials = None

    async def access_token(self) -> str:
        async with self._lock:
            refresh = await self.store.load()
            if refresh is None:
                raise GmailAuthenticationError("Gmail is not connected. Use /gmail_connect.")
            if (
                self._credentials
                and refresh == self._source
                and self._credentials.expiry
                and self._credentials.expiry
                > datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=1)
            ):
                return str(self._credentials.token)
            if not self.settings.google_client_id or not self.settings.google_client_secret:
                raise GmailAuthenticationError("Google OAuth is not configured.")
            credentials = Credentials(
                token=None,
                refresh_token=refresh.get_secret_value(),
                token_uri=TOKEN_URI,
                client_id=self.settings.google_client_id.get_secret_value(),
                client_secret=self.settings.google_client_secret.get_secret_value(),
                scopes=GMAIL_SCOPES,
            )
            try:
                await asyncio.to_thread(credentials.refresh, Request())
            except RefreshError:
                raise GmailAuthenticationError("Gmail authorization expired; reconnect.") from None
            except (TransportError, requests.RequestException):
                raise GmailUnavailableError("Gmail is temporarily unavailable.") from None
            if (
                credentials.refresh_token
                and credentials.refresh_token != refresh.get_secret_value()
            ):
                replacement = SecretStr(credentials.refresh_token)
                if not await self.store.rotate(refresh, replacement):
                    raise GmailAuthenticationError("Gmail connection changed; retry.")
                refresh = replacement
            self._source, self._credentials = refresh, credentials
            return str(credentials.token)


class GmailClient:
    """Thin Gmail REST adapter; it never downloads attachment bodies."""

    def __init__(self, http: httpx.AsyncClient, tokens: AccessTokenProvider) -> None:
        self.http, self.tokens = http, tokens

    async def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        token = await self.tokens.access_token()
        try:
            response = await self.http.get(
                f"{BASE_URL}/{path}", params=params, headers={"Authorization": f"Bearer {token}"}
            )
        except httpx.RequestError:
            raise GmailUnavailableError("Gmail is temporarily unavailable.") from None
        if response.status_code == 401:
            raise GmailAuthenticationError("Gmail authorization expired; reconnect.")
        if response.status_code == 403:
            raise GmailPermissionError("Gmail read permission was not granted.")
        if response.status_code == 404:
            raise GmailMessageNotFoundError("Email was not found.")
        if response.status_code == 429:
            raise GmailRateLimitError("Gmail rate limit reached; retry later.")
        if response.status_code >= 500:
            raise GmailUnavailableError("Gmail is temporarily unavailable.")
        if response.is_error:
            raise GmailUnavailableError("Gmail request failed safely.")
        return response.json()

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        token = await self.tokens.access_token()
        try:
            response = await self.http.post(
                f"{BASE_URL}/{path}",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.RequestError:
            raise GmailUnavailableError("Gmail is temporarily unavailable.") from None
        if response.status_code == 401:
            raise GmailAuthenticationError("Gmail authorization expired; reconnect.")
        if response.status_code == 403:
            raise GmailPermissionError("Gmail send permission was not granted; reconnect Gmail.")
        if response.status_code == 404:
            raise GmailMessageNotFoundError("Email thread was not found.")
        if response.status_code == 429:
            raise GmailRateLimitError("Gmail rate limit reached; retry later.")
        if response.status_code >= 500:
            raise GmailUnavailableError("Gmail is temporarily unavailable.")
        if response.is_error:
            raise GmailUnavailableError("Gmail send failed safely.")
        return response.json()

    async def list_messages(
        self, *, query: str = "in:inbox", limit: int = 10, page_token: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"q": query, "maxResults": min(limit, 100)}
        if page_token:
            params["pageToken"] = page_token
        return await self._request("messages", params)

    async def get_message(self, message_id: str) -> dict[str, Any]:
        return await self._request(f"messages/{message_id}", {"format": "full"})

    async def get_thread(self, thread_id: str) -> dict[str, Any]:
        return await self._request(f"threads/{thread_id}", {"format": "full"})

    async def get_profile(self) -> dict[str, Any]:
        return await self._request("profile")

    async def list_history(self, history_id: str) -> dict[str, Any]:
        return await self._request(
            "history",
            {"startHistoryId": history_id, "historyTypes": "messageAdded", "labelId": "INBOX"},
        )

    async def search_messages(self, query: str, limit: int = 10) -> dict[str, Any]:
        return await self.list_messages(query=query, limit=limit)

    async def send_message(
        self,
        recipient: str,
        subject: str,
        body: str,
        thread_id: str,
    ) -> str:
        message = EmailMessage()
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
        response = await self._post("messages/send", {"raw": raw, "threadId": thread_id})
        message_id = response.get("id")
        if not isinstance(message_id, str) or not message_id:
            raise GmailUnavailableError("Gmail did not confirm the sent message.")
        return message_id
