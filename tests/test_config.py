"""Configuration tests never load the owner's .env or credentials."""

import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    names = {str(field.alias).upper() for field in Settings.model_fields.values()}
    for name in list(os.environ):
        if name.upper() in names:
            monkeypatch.delenv(name)


def test_optional_ids_and_default_timezone() -> None:
    settings = Settings(_env_file=None)
    assert settings.telegram_owner_id is None
    assert settings.telegram_api_id is None
    assert not settings.is_owner_configured
    assert settings.app_timezone == "Asia/Tashkent"
    assert datetime(2026, 1, 1, tzinfo=settings.timezone).utcoffset() == timedelta(hours=5)


def test_empty_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for field in Settings.model_fields.values():
        monkeypatch.setenv(str(field.alias), "")
    settings = Settings(_env_file=None)
    assert settings.telegram_owner_id is None
    assert settings.telegram_api_id is None
    assert settings.bot_pin is None
    assert settings.database_url is None


def test_example_file_loads() -> None:
    example = Path(__file__).resolve().parents[1] / ".env.example"
    settings = Settings(_env_file=example)
    assert settings.telegram_owner_id is None
    assert settings.telegram_api_id is None
    assert settings.secret_key is None


@pytest.mark.parametrize("name", ["TELEGRAM_OWNER_ID", "TELEGRAM_API_ID"])
@pytest.mark.parametrize("value", ["abc", "0", "-1"])
def test_invalid_ids(name: str, value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_TIMEZONE", "Invalid/Timezone")
    with pytest.raises(ValidationError, match="IANA timezone"):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "name",
    [
        "telegram_bot_token",
        "telegram_api_hash",
        "bot_pin",
        "secret_key",
        "database_url",
        "redis_url",
        "ai_api_key",
        "stt_api_key",
    ],
)
def test_secrets_masked(name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    value = "test-only-sensitive-value"
    monkeypatch.setenv(name.upper(), value)
    settings = Settings(_env_file=None)
    secret = getattr(settings, name)
    assert isinstance(secret, SecretStr)
    assert secret.get_secret_value() == value
    assert value not in str(settings)
    assert value not in repr(settings)
    assert value not in settings.model_dump_json()
