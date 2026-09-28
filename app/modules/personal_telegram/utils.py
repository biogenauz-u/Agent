import re
from datetime import UTC, datetime
from typing import Any

from app.database.models.personal_telegram import TelegramMessageDirection
from app.modules.personal_telegram.schemas import IncomingTelegramMessage


def safe_preview(value: str, limit: int = 240) -> str:
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
    cleaned = " ".join(cleaned.split())
    return cleaned[:limit]


def mask_phone(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    return f"***{digits[-2:]}" if len(digits) >= 2 else "***"


def media_type(message: Any) -> str | None:
    media = getattr(message, "media", None)
    if media is None:
        return None
    document = getattr(message, "document", None)
    if getattr(message, "photo", None) is not None:
        return "photo"
    if getattr(message, "video", None) is not None:
        return "video"
    if getattr(message, "voice", None) is not None:
        return "voice"
    if getattr(message, "audio", None) is not None:
        return "audio"
    if getattr(message, "sticker", None) is not None:
        return "sticker"
    if document is not None:
        return "document"
    return "media"


async def normalize_message(message: Any, *, is_private: bool = True) -> IncomingTelegramMessage:
    sender = await message.get_sender() if hasattr(message, "get_sender") else None
    first = getattr(sender, "first_name", None) or ""
    last = getattr(sender, "last_name", None) or ""
    name = " ".join(part for part in (first, last) if part).strip()
    text = str(getattr(message, "message", None) or getattr(message, "raw_text", None) or "")
    date = getattr(message, "date", None) or datetime.now(UTC)
    if date.tzinfo is None:
        date = date.replace(tzinfo=UTC)
    chat_id = int(message.chat_id)
    kind = media_type(message)
    return IncomingTelegramMessage(
        peer_id=chat_id,
        peer_type="private" if is_private else "group",
        sender_id=int(message.sender_id) if getattr(message, "sender_id", None) else None,
        sender_username=getattr(sender, "username", None),
        sender_display_name=name or getattr(sender, "username", None) or "Unknown",
        telegram_message_id=int(message.id),
        telegram_chat_id=chat_id,
        direction=(
            TelegramMessageDirection.OUTGOING
            if bool(getattr(message, "out", False))
            else TelegramMessageDirection.INCOMING
        ),
        text=text,
        received_at=date,
        reply_to_message_id=getattr(message, "reply_to_msg_id", None),
        has_media=kind is not None,
        media_type=kind,
        is_private=is_private,
        sender_is_bot=bool(getattr(sender, "bot", False)),
    )
