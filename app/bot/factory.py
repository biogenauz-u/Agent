from aiogram import Bot
from aiogram.utils.token import TokenValidationError

from app.core.config import Settings
from app.core.exceptions import TelegramConfigurationError


def require_owner(settings: Settings) -> int:
    if settings.telegram_owner_id is None:
        raise TelegramConfigurationError("TELEGRAM_OWNER_ID is not configured.")
    return settings.telegram_owner_id


def create_bot(settings: Settings) -> Bot:
    """Create without network calls; reveal the token only at the Aiogram boundary."""
    if not settings.telegram_bot_token:
        raise TelegramConfigurationError("TELEGRAM_BOT_TOKEN is not configured.")
    require_owner(settings)
    try:
        return Bot(token=settings.telegram_bot_token.get_secret_value())
    except TokenValidationError:
        raise TelegramConfigurationError("TELEGRAM_BOT_TOKEN is invalid.") from None
