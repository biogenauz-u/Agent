import base64
import secrets
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.encryption import CredentialEncryption
from app.database.models import GoogleCredential
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.calendar.audit import CalendarAudit
from app.modules.calendar.credentials import GoogleCredentialStore
from app.modules.calendar.exceptions import CalendarConfigurationError
from app.modules.calendar.repository import GoogleCredentialRepository
from app.modules.users.repository import UserRepository


def key() -> SecretStr:
    return SecretStr(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())


def test_encryption_binding_and_no_plaintext() -> None:
    encryption = CredentialEncryption(key())
    envelope = encryption.encrypt("private-refresh", 42)
    assert b"private-refresh" not in envelope
    assert encryption.decrypt(envelope, 42) == "private-refresh"
    assert encryption.encrypt("private-refresh", 42) != envelope
    with pytest.raises(CalendarConfigurationError):
        encryption.decrypt(envelope, 43)
    with pytest.raises(CalendarConfigurationError):
        encryption.decrypt(envelope[:-1] + bytes([envelope[-1] ^ 1]), 42)
    with pytest.raises(CalendarConfigurationError):
        CredentialEncryption(SecretStr("invalid"))


async def test_repository_save_load_delete(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    repository = GoogleCredentialRepository(session)
    await repository.save(user.id, b"encrypted-one")
    assert (await repository.load(user.id)).refresh_token_encrypted == b"encrypted-one"
    await repository.save(user.id, b"encrypted-two")
    assert (await repository.load(user.id)).refresh_token_encrypted == b"encrypted-two"
    await repository.delete(user.id)
    assert await repository.load(user.id) is None


async def test_credential_store_persists_only_ciphertext(engine) -> None:
    database = DatabaseManager(Settings(_env_file=None))
    database._sessions = async_sessionmaker(engine, expire_on_commit=False)
    store = GoogleCredentialStore(database, 42, key())
    await store.save(SecretStr("refresh-private"))
    assert (await store.load()).get_secret_value() == "refresh-private"
    async with database.session() as session:
        row = await session.scalar(select(GoogleCredential))
        assert b"refresh-private" not in row.refresh_token_encrypted
    await store.delete()
    assert await store.load() is None
    assert not await store.rotate(SecretStr("refresh-private"), SecretStr("new-refresh"))
    assert await store.load() is None


async def test_audit_failure_is_best_effort() -> None:
    database = Mock()
    database.session.side_effect = RuntimeError("secret-detail")
    await CalendarAudit(database, 42).record(AuditAction.CALENDAR_EVENT_CREATED, "abc")


async def test_token_refresh_cache_and_disconnect(monkeypatch) -> None:
    from datetime import UTC, datetime, timedelta

    from app.modules.calendar.auth import GoogleTokenProvider
    from app.modules.calendar.exceptions import GoogleCalendarAuthenticationError

    store = Mock()
    store.load = AsyncMock(return_value=SecretStr("refresh-private"))
    store.save = AsyncMock()
    provider = GoogleTokenProvider(
        Settings(_env_file=None, GOOGLE_CLIENT_ID="client", GOOGLE_CLIENT_SECRET="secret"), store
    )
    calls = []

    def refresh(credentials, request):
        calls.append(True)
        credentials.token = "access-private"
        credentials.expiry = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)

    monkeypatch.setattr("google.oauth2.credentials.Credentials.refresh", refresh)
    assert await provider.access_token() == "access-private"
    assert await provider.access_token() == "access-private"
    assert len(calls) == 1
    store.save.assert_not_called()  # access token is never persisted
    store.load.return_value = None
    with pytest.raises(GoogleCalendarAuthenticationError):
        await provider.access_token()


async def test_permanent_refresh_failure_not_repeated(monkeypatch) -> None:
    from google.auth.exceptions import RefreshError

    from app.modules.calendar.auth import GoogleTokenProvider
    from app.modules.calendar.exceptions import GoogleCalendarAuthenticationError

    store = Mock(load=AsyncMock(return_value=SecretStr("bad-refresh")))
    provider = GoogleTokenProvider(
        Settings(_env_file=None, GOOGLE_CLIENT_ID="client", GOOGLE_CLIENT_SECRET="secret"), store
    )
    refresh = Mock(side_effect=RefreshError("private-details"))
    monkeypatch.setattr("google.oauth2.credentials.Credentials.refresh", refresh)
    for _ in range(2):
        with pytest.raises(GoogleCalendarAuthenticationError):
            await provider.access_token()
    refresh.assert_called_once()
