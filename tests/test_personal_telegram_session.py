import base64
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.database.models import PersonalTelegramSession
from app.database.session import DatabaseManager
from app.modules.personal_telegram.client import PersonalTelegramClient
from app.modules.personal_telegram.exceptions import PersonalTelegramConfigurationError
from app.modules.personal_telegram.session_store import PersonalTelegramSessionStore


def encryption_key() -> str:
    return base64.urlsafe_b64encode(b"p" * 32).decode()


def manager(engine) -> DatabaseManager:
    database = DatabaseManager(Settings(_env_file=None))
    database._sessions = async_sessionmaker(engine, expire_on_commit=False)
    return database


def settings(**values) -> Settings:
    return Settings(
        _env_file=None,
        TELEGRAM_OWNER_ID=42,
        TELEGRAM_API_ID=12345,
        TELEGRAM_API_HASH="api-hash-secret",
        DATA_ENCRYPTION_KEY=encryption_key(),
        **values,
    )


def test_mtproto_settings_defaults_and_validation() -> None:
    configured = settings()
    assert configured.personal_telegram_session_backend == "database"
    assert configured.personal_telegram_monitor_scope == "private"
    assert configured.personal_telegram_initial_sync_limit == 30
    with pytest.raises(ValidationError):
        settings(PERSONAL_TELEGRAM_RECENT_LIMIT=1000)


def test_missing_api_id_is_lazy_until_client_creation() -> None:
    unconfigured = Settings(_env_file=None, TELEGRAM_API_HASH="secret")
    with pytest.raises(PersonalTelegramConfigurationError, match="TELEGRAM_API_ID"):
        PersonalTelegramClient(unconfigured)


def test_missing_api_hash_is_lazy_until_client_creation() -> None:
    unconfigured = Settings(_env_file=None, TELEGRAM_API_ID=123)
    with pytest.raises(PersonalTelegramConfigurationError, match="TELEGRAM_API_HASH"):
        PersonalTelegramClient(unconfigured)


def test_client_repr_does_not_leak_api_hash_or_session() -> None:
    client = PersonalTelegramClient(settings(), "")
    assert client._client is None
    value = repr(client)
    assert "api-hash-secret" not in value
    assert "session" not in value.lower()


def test_invalid_monitor_scope_is_rejected() -> None:
    with pytest.raises(ValidationError):
        settings(PERSONAL_TELEGRAM_MONITOR_SCOPE="channels")


async def test_session_round_trip_stores_only_ciphertext(engine) -> None:
    database = manager(engine)
    store = PersonalTelegramSessionStore(database, 42, SecretStr(encryption_key()))
    plaintext = "private-string-session"
    await store.save(SecretStr(plaintext), 9001, "owner", "***45")
    loaded = await store.load()
    assert loaded is not None
    assert loaded.session.get_secret_value() == plaintext
    assert plaintext not in repr(loaded)
    async with database.session() as session:
        row = await session.scalar(select(PersonalTelegramSession))
        assert row is not None
        assert plaintext.encode() not in row.encrypted_session
        assert row.phone_hint == "***45"
        assert row.last_connected_at is not None
        assert row.last_connected_at <= datetime.now(UTC)
    await store.delete()
    assert await store.load() is None


async def test_session_deactivation_hides_revoked_session(engine) -> None:
    store = PersonalTelegramSessionStore(manager(engine), 42, SecretStr(encryption_key()))
    await store.save(SecretStr("private-session"), 9001, None, None)
    await store.deactivate()
    assert await store.load() is None


async def test_saving_session_replaces_owner_row(engine) -> None:
    database = manager(engine)
    store = PersonalTelegramSessionStore(database, 42, SecretStr(encryption_key()))
    await store.save(SecretStr("first-session"), 1, "first", "***01")
    await store.save(SecretStr("second-session"), 2, "second", "***02")
    loaded = await store.load()
    assert loaded and loaded.session.get_secret_value() == "second-session"
    async with database.session() as session:
        rows = list(await session.scalars(select(PersonalTelegramSession)))
        assert len(rows) == 1 and rows[0].telegram_account_id == 2
