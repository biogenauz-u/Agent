"""Structured allowlisted logs; never serialize updates, exceptions or settings."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from traceback import walk_tb
from uuid import uuid4

SAFE_FIELDS = ("telegram_user_id", "command", "error_id", "error_type", "frames", "action")


class SafeJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "module": record.name,
            # Framework errors can embed API URLs or message payloads. Do not render them.
            "event": record.msg if record.name.startswith("app.") else "external_log",
        }
        for name in SAFE_FIELDS:
            if hasattr(record, name):
                payload[name] = getattr(record, name)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str = "INFO") -> None:
    # OAuth callbacks carry authorization codes in query strings, including under CLI Uvicorn.
    logging.getLogger("uvicorn.access").disabled = True
    handler = logging.StreamHandler()
    handler.setFormatter(SafeJsonFormatter())
    logging.basicConfig(
        handlers=[handler], level=getattr(logging, level.upper(), logging.INFO), force=True
    )


def report_error(logger: logging.Logger, error: Exception) -> str:
    """Log exception type and stack locations, excluding text, locals and source lines."""
    error_id = uuid4().hex[:12].upper()
    frames = [
        f"{Path(frame.f_code.co_filename).name}:{line}:{frame.f_code.co_name}"
        for frame, line in walk_tb(error.__traceback__)
    ]
    logger.error(
        "unexpected_error",
        extra={
            "error_id": error_id,
            "error_type": type(error).__name__,
            "frames": frames,
        },
    )
    return error_id
