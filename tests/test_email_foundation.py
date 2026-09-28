import asyncio
import base64
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.core.encryption import CredentialEncryption
from app.modules.calendar.exceptions import CalendarConfigurationError
from app.modules.email.monitor import GmailMonitor
from app.modules.email.oauth import granted_scopes


def key() -> SecretStr:
    return SecretStr(base64.urlsafe_b64encode(b"x" * 32).decode())


def test_gmail_settings_defaults_and_bounds() -> None:
    settings = Settings(_env_file=None)
    assert settings.gmail_poll_interval_seconds == 60
    assert settings.gmail_initial_sync_limit == 30
    assert settings.gmail_notify_mode == "all"
    with pytest.raises(ValidationError):
        Settings(_env_file=None, GMAIL_POLL_INTERVAL_SECONDS=1)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("scope.one scope.two", {"scope.one", "scope.two"}),
        (["scope.one", "scope.two"], {"scope.one", "scope.two"}),
        (None, set()),
    ],
)
def test_gmail_oauth_scope_formats(value: object, expected: set[str]) -> None:
    assert granted_scopes(value) == expected


def test_email_body_uses_distinct_encrypted_envelope() -> None:
    cipher = CredentialEncryption(key())
    encrypted = cipher.encrypt("sensitive body", 123, "gmail_body")
    assert b"sensitive body" not in encrypted
    assert cipher.decrypt(encrypted, 123, "gmail_body") == "sensitive body"
    with pytest.raises(CalendarConfigurationError):
        cipher.decrypt(encrypted, 123, "google_calendar")


async def test_initial_poll_baselines_without_notification() -> None:
    service = AsyncMock()
    service.checkpoint.return_value = None
    monitor = GmailMonitor(service, 30, 20)
    assert await monitor.poll_once() == 0
    service.initial_sync.assert_awaited_once_with(20)
    service.sync_new.assert_not_called()


async def test_monitor_stops_cleanly() -> None:
    service = AsyncMock()
    service.checkpoint.return_value = "1"
    service.sync_new.return_value = 0
    monitor = GmailMonitor(service, 30, 20)
    monitor.start()
    await asyncio.sleep(0)
    await monitor.stop()
    assert monitor._task is None
