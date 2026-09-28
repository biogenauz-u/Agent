import logging

import pytest
from argon2 import PasswordHasher, Type

from app.bot.factory import create_bot, require_owner
from app.core.config import Settings
from app.core.exceptions import TelegramConfigurationError
from app.core.logging import SafeJsonFormatter, report_error
from app.modules.security.pin_service import PinService


def configured(**values: object) -> Settings:
    return Settings(_env_file=None, TELEGRAM_OWNER_ID=42, **values)


def test_missing_token() -> None:
    with pytest.raises(TelegramConfigurationError, match="TELEGRAM_BOT_TOKEN"):
        create_bot(configured(TELEGRAM_BOT_TOKEN=None))


def test_missing_owner() -> None:
    with pytest.raises(TelegramConfigurationError, match="TELEGRAM_OWNER_ID"):
        require_owner(Settings(_env_file=None, TELEGRAM_OWNER_ID=None))


def test_invalid_token_redacted() -> None:
    candidate = "test-secret-invalid-token"
    with pytest.raises(TelegramConfigurationError) as caught:
        create_bot(configured(TELEGRAM_BOT_TOKEN=candidate))
    assert candidate not in str(caught.value)


async def test_token_repr() -> None:
    candidate = "123456789:TEST_ONLY_FAKE_TOKEN_NOT_FOR_TELEGRAM_abc"
    settings = configured(TELEGRAM_BOT_TOKEN=candidate)
    bot = create_bot(settings)
    try:
        assert candidate not in repr(settings)
        assert candidate not in repr(bot)
    finally:
        await bot.session.close()


def test_framework_logs_and_exception_text_redacted(caplog: pytest.LogCaptureFixture) -> None:
    formatter = SafeJsonFormatter()
    record = logging.LogRecord(
        "aiogram.dispatcher", logging.ERROR, "", 1, "test-secret-in-url", (), None
    )
    assert "test-secret-in-url" not in formatter.format(record)
    try:
        raise RuntimeError("test-secret-pin")
    except RuntimeError as error:
        report_error(logging.getLogger("app.bot.test"), error)
    assert "test-secret-pin" not in caplog.text
    assert "error_id" in formatter.format(caplog.records[-1])


async def test_hash_priority_and_verification(pin_hash: str) -> None:
    service = PinService.from_settings(
        configured(
            BOT_PIN_HASH=pin_hash,
            BOT_PIN="different-test-only",
            APP_ENV="production",
        )
    )
    assert await service.verify_pin("test-pin-only")
    assert not await service.verify_pin("wrong-test-only")
    assert pin_hash not in repr(service)


def test_plain_pin_rejected_in_production() -> None:
    with pytest.raises(TelegramConfigurationError):
        PinService.from_settings(
            configured(
                APP_ENV="production",
                BOT_PIN="test-pin-only",
                BOT_PIN_HASH=None,
            )
        )


async def test_development_pin() -> None:
    service = PinService.from_settings(
        configured(
            APP_ENV="development",
            BOT_PIN="test-pin-only",
            BOT_PIN_HASH=None,
        )
    )
    assert await service.verify_pin("test-pin-only")


@pytest.mark.parametrize(
    "value",
    ["bad-test-hash", PasswordHasher(type=Type.I).hash("test-only")],
    ids=["malformed", "wrong_algorithm"],
)
def test_invalid_hash(value: str) -> None:
    with pytest.raises(TelegramConfigurationError):
        PinService(value)


def test_missing_pin() -> None:
    with pytest.raises(TelegramConfigurationError):
        PinService.from_settings(configured(BOT_PIN=None, BOT_PIN_HASH=None))


def test_hash_setting_is_masked(pin_hash: str) -> None:
    settings = configured(BOT_PIN_HASH=pin_hash)
    assert pin_hash not in repr(settings)
    assert pin_hash not in settings.model_dump_json()
    assert settings.bot_pin_hash.get_secret_value() == pin_hash
