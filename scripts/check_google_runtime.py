"""Read-only Google integration diagnostic; never prints credentials or tokens."""

import asyncio
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select

from app.core.config import Settings
from app.core.encryption import CredentialEncryption
from app.database.health import check_database_health
from app.database.models import GoogleCredential, User
from app.database.session import DatabaseManager
from app.modules.calendar.auth import SCOPES as CALENDAR_SCOPES
from app.modules.email.client import GMAIL_SCOPES


def callback_uris(settings: Settings) -> tuple[str, str] | None:
    if not settings.google_redirect_uri:
        return None
    uri = urlsplit(settings.google_redirect_uri)
    calendar = urlunsplit((uri.scheme, uri.netloc, "/oauth/google/callback", "", ""))
    gmail = urlunsplit((uri.scheme, uri.netloc, "/oauth/gmail/callback", "", ""))
    return calendar, gmail


def google_configuration(settings: Settings) -> str:
    if not settings.google_client_id or not settings.google_client_secret:
        return "NOT_CONFIGURED"
    callbacks = callback_uris(settings)
    if callbacks is None:
        return "NOT_CONFIGURED"
    calendar, _ = callbacks
    uri = urlsplit(calendar)
    local_http = uri.scheme == "http" and uri.hostname in {"localhost", "127.0.0.1", "::1"}
    if not uri.hostname or (uri.scheme != "https" and not local_http):
        return "INVALID_REDIRECT_URI"
    return "CONFIGURED"


async def credential_status(settings: Settings) -> tuple[str, str, str]:
    if settings.database_url is None:
        return "NOT_CONFIGURED", "BLOCKED", "BLOCKED"
    manager = DatabaseManager(settings)
    try:
        manager.initialize()
        if not await check_database_health(manager.engine):
            return "UNAVAILABLE", "BLOCKED", "BLOCKED"
        if settings.telegram_owner_id is None:
            return "CONNECTED", "BLOCKED", "BLOCKED"
        cipher = CredentialEncryption(settings.data_encryption_key)
        async with manager.session() as session:
            user_id = await session.scalar(
                select(User.id).where(User.telegram_user_id == settings.telegram_owner_id)
            )
            if user_id is None:
                return "CONNECTED", "NOT_CONNECTED", "NOT_CONNECTED"
            rows = (
                await session.scalars(
                    select(GoogleCredential).where(GoogleCredential.user_id == user_id)
                )
            ).all()
        providers: dict[str, str] = {}
        for row in rows:
            try:
                cipher.decrypt(row.refresh_token_encrypted, settings.telegram_owner_id, row.provider)
                providers[row.provider] = "ENCRYPTED_VALID"
            except Exception:  # noqa: BLE001 - report validity only, never credential material
                providers[row.provider] = "ENCRYPTED_INVALID"
        return (
            "CONNECTED",
            providers.get("google_calendar", "NOT_CONNECTED"),
            providers.get("google_gmail", "NOT_CONNECTED"),
        )
    except Exception as error:  # noqa: BLE001 - sanitized diagnostic boundary
        return f"ERROR ({type(error).__name__})", "BLOCKED", "BLOCKED"
    finally:
        await manager.dispose()


async def main() -> int:
    settings = Settings()
    print("Personal AI Google Runtime Check")
    print(f"Google OAuth: {google_configuration(settings)}")
    print(f"Client ID configured: {settings.google_client_id is not None}")
    print(f"Client secret configured: {settings.google_client_secret is not None}")
    print(f"Encryption key configured: {settings.data_encryption_key is not None}")
    callbacks = callback_uris(settings)
    if callbacks:
        print(f"Calendar callback: {callbacks[0]}")
        print(f"Gmail callback: {callbacks[1]}")
    else:
        print("Calendar callback: NOT_CONFIGURED")
        print("Gmail callback: NOT_CONFIGURED")
    print(f"Calendar scopes: {', '.join(CALENDAR_SCOPES)}")
    print(f"Gmail scopes: {', '.join(GMAIL_SCOPES)}")
    print(f"Gmail send scope requested: {'gmail.send' in ' '.join(GMAIL_SCOPES)}")
    database, calendar, gmail = await credential_status(settings)
    print(f"Database: {database}")
    print(f"Calendar credential: {calendar}")
    print(f"Gmail credential: {gmail}")
    configured = google_configuration(settings) == "CONFIGURED"
    return 0 if configured and database == "CONNECTED" else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
