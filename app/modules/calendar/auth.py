"""Official Google refresh logic off the event loop; access tokens only in memory."""

import asyncio
from datetime import UTC, datetime, timedelta

import requests
from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.calendar.credentials import CredentialStore
from app.modules.calendar.exceptions import (
    CalendarConfigurationError,
    GoogleCalendarAuthenticationError,
    GoogleCalendarUnavailableError,
)

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.freebusy",
]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def require_google(settings: Settings) -> None:
    if not settings.google_client_id or not settings.google_client_secret:
        raise CalendarConfigurationError("Google OAuth client settings are missing.")


class GoogleTokenProvider:
    def __init__(self, settings: Settings, store: CredentialStore) -> None:
        self.settings, self.store = settings, store
        self._lock = asyncio.Lock()
        self._credentials: Credentials | None = None
        self._source: SecretStr | None = None
        self._invalid: SecretStr | None = None

    def invalidate(self) -> None:
        self._credentials = None
        self._invalid = self._source

    async def access_token(self) -> str:
        require_google(self.settings)
        async with self._lock:
            # Re-read so disconnect/reconnect in another process invalidates the cache.
            refresh = await self.store.load()
            if refresh is None or refresh == self._invalid:
                raise GoogleCalendarAuthenticationError(
                    "Google Calendar: reconnect with /google_connect."
                )
            if (
                refresh == self._source
                and self._credentials is not None
                and self._credentials.expiry is not None
                and self._credentials.expiry
                > datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=1)
            ):
                return str(self._credentials.token)
            assert self.settings.google_client_id and self.settings.google_client_secret
            credentials = Credentials(
                token=None,
                refresh_token=refresh.get_secret_value(),
                token_uri=TOKEN_URI,
                client_id=self.settings.google_client_id.get_secret_value(),
                client_secret=self.settings.google_client_secret.get_secret_value(),
                scopes=SCOPES,
            )

            def refresh_sync() -> None:
                with requests.Session() as session:
                    request = Request(session=session)
                    credentials.refresh(lambda **kwargs: request(**{**kwargs, "timeout": 15}))

            try:
                await asyncio.to_thread(refresh_sync)
            except RefreshError as error:
                if not error.retryable:
                    self._invalid = refresh
                raise GoogleCalendarAuthenticationError(
                    "Google Calendar authorization failed; reconnect."
                ) from None
            except (TransportError, requests.RequestException):
                raise GoogleCalendarUnavailableError(
                    "Google temporarily unavailable. Try later."
                ) from None
            if (
                credentials.refresh_token
                and credentials.refresh_token != refresh.get_secret_value()
            ):
                replacement = SecretStr(credentials.refresh_token)
                if not await self.store.rotate(refresh, replacement):
                    raise GoogleCalendarAuthenticationError("Google connection changed. Try again.")
                refresh = replacement
            self._source, self._credentials, self._invalid = refresh, credentials, None
            return str(credentials.token)
