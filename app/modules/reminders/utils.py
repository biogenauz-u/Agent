import hashlib
from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def deduplication_key(*parts: object) -> str:
    canonical = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(canonical.encode()).hexdigest()


def job_id(reminder_id: int) -> str:
    return f"reminder:{reminder_id}"


def sanitize_failure(error: Exception) -> str:
    """Keep only exception type; SDK text can contain API URLs or message content."""
    return type(error).__name__[:120]
