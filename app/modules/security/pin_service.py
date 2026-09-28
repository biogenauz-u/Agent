import asyncio

from argon2 import PasswordHasher, Type, extract_parameters
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings
from app.core.exceptions import TelegramConfigurationError

MAX_PIN_LENGTH = 256


class PinService:
    """Hold only an Argon2id hash; verification runs outside the event loop."""

    def __init__(self, encoded_hash: str) -> None:
        try:
            parameters = extract_parameters(encoded_hash)
            if parameters.type != Type.ID:
                raise ValueError("wrong algorithm")
        except (InvalidHashError, ValueError):
            raise TelegramConfigurationError(
                "BOT_PIN_HASH must be a valid Argon2id hash."
            ) from None
        self._encoded_hash = encoded_hash
        self._hasher = PasswordHasher(type=Type.ID)

    @classmethod
    def from_settings(cls, settings: Settings) -> "PinService":
        if settings.bot_pin_hash:
            return cls(settings.bot_pin_hash.get_secret_value())
        if settings.app_env != "development" or not settings.bot_pin:
            raise TelegramConfigurationError(
                "Configure BOT_PIN_HASH, or BOT_PIN for development only."
            )
        pin = settings.bot_pin.get_secret_value()
        if not 6 <= len(pin) <= MAX_PIN_LENGTH:
            raise TelegramConfigurationError(
                "Development BOT_PIN must contain 6 to 256 characters."
            )
        return cls(PasswordHasher(type=Type.ID).hash(pin))

    async def verify_pin(self, pin: str) -> bool:
        if not pin or len(pin) > MAX_PIN_LENGTH:
            return False
        try:
            return await asyncio.to_thread(self._hasher.verify, self._encoded_hash, pin)
        except VerifyMismatchError:
            return False
        except (VerificationError, InvalidHashError):
            raise TelegramConfigurationError("Configured PIN hash cannot be verified.") from None
