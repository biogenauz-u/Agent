import base64
import binascii
import re

from app.modules.email.exceptions import MalformedEmailError


def decode_base64url(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, binascii.Error) as error:
        raise MalformedEmailError("Email body encoding is invalid.") from error


def telegram_chunks(value: str, limit: int = 3500) -> list[str]:
    if limit < 100:
        raise ValueError("Chunk limit is too small")
    text = value.strip()
    if not text:
        return [""]
    chunks: list[str] = []
    while len(text) > limit:
        split = max(text.rfind("\n", 0, limit), text.rfind(" ", 0, limit))
        split = split if split >= limit // 2 else limit
        chunks.append(text[:split].rstrip())
        text = text[split:].lstrip()
    chunks.append(text)
    return chunks


def clean_draft(value: str, limit: int = 4000) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value).strip()[:limit]
