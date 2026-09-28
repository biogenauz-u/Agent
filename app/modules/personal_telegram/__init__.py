"""Owner personal-account MTProto integration; external messages are untrusted data."""

from app.modules.personal_telegram.client import PersonalTelegramClient
from app.modules.personal_telegram.service import PersonalTelegramService

__all__ = ["PersonalTelegramClient", "PersonalTelegramService"]
