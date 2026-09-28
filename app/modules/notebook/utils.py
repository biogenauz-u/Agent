import re
import unicodedata
from pathlib import PurePath
from urllib.parse import urlsplit

from app.database.models.notebook import AttachmentType
from app.modules.notebook.exceptions import NotebookValidationError


def normalize_label(value: str, *, maximum: int = 80) -> tuple[str, str]:
    display = " ".join(value.strip().lstrip("#").split())
    if not display or len(display) > maximum:
        raise NotebookValidationError(f"Name must contain 1 to {maximum} characters.")
    folded = unicodedata.normalize("NFKD", display.casefold())
    slug = re.sub(r"[^a-z0-9]+", "-", "".join(c for c in folded if not unicodedata.combining(c)))
    slug = slug.strip("-")
    if not slug:
        raise NotebookValidationError("Name must contain letters or numbers.")
    return display, slug


def safe_original_name(value: str | None) -> str:
    if not value:
        return "attachment"
    if "\x00" in value:
        raise NotebookValidationError("Invalid attachment filename.")
    name = PurePath(value.replace("\\", "/")).name.strip()
    if not name or name in {".", ".."}:
        return "attachment"
    return name[:255]


def validate_url(value: str, allowed: tuple[str, ...]) -> str:
    url = value.strip()
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in allowed or not parsed.netloc or parsed.username or parsed.password:
        raise NotebookValidationError("Only public http/https links are accepted.")
    if len(url) > 4096:
        raise NotebookValidationError("Link is too long.")
    return url


def attachment_type(mime_type: str, *, voice: bool = False) -> AttachmentType:
    mime = mime_type.casefold()
    if voice:
        return AttachmentType.VOICE
    if mime.startswith("image/"):
        return AttachmentType.IMAGE
    if mime.startswith("video/"):
        return AttachmentType.VIDEO
    if mime == "application/pdf":
        return AttachmentType.PDF
    if "word" in mime or "officedocument.wordprocessing" in mime:
        return AttachmentType.WORD
    if "excel" in mime or "spreadsheetml" in mime:
        return AttachmentType.EXCEL
    if mime.startswith(("text/", "application/")):
        return AttachmentType.DOCUMENT
    return AttachmentType.OTHER

