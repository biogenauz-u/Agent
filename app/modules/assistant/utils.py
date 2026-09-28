import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import ClassVar
from zoneinfo import ZoneInfo

from app.modules.assistant.exceptions import AssistantValidationError


class DateTimeResolver:
    WORDS: ClassVar[dict[str, int]] = {
        "bugun": 0,
        "today": 0,
        "сегодня": 0,
        "ertaga": 1,
        "tomorrow": 1,
        "завтра": 1,
        "indin": 2,
        "day after tomorrow": 2,
        "послезавтра": 2,
    }

    def __init__(self, timezone: ZoneInfo) -> None:
        self.timezone = timezone

    def resolve_date(self, text: str, now: datetime) -> date | None:
        lowered = text.casefold()
        for word in sorted(self.WORDS, key=len, reverse=True):
            if word in lowered:
                return now.astimezone(self.timezone).date() + timedelta(
                    days=self.WORDS[word]
                )
        return None

    def resolve(self, text: str, now: datetime) -> datetime | None:
        day = self.resolve_date(text, now)
        if day is None:
            return None
        match = re.search(
            r"(?:soat\s*)?(\d{1,2})(?::(\d{2}))?\s*(pm|am|da|в)?\b",
            text.casefold(),
        )
        if not match:
            return None
        hour, minute = int(match.group(1)), int(match.group(2) or 0)
        marker = match.group(3)
        if marker == "pm" and hour < 12:
            hour += 12
        if marker == "am" and hour == 12:
            hour = 0
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise AssistantValidationError("Invalid time")
        return datetime.combine(day, time(hour, minute), self.timezone)


def normalize_amount(text: str) -> Decimal | None:
    normalized = text.casefold().replace(",", ".")
    match = re.search(
        r"(?<!\w)(\d+(?:\.\d+)?)\s*"
        r"(ming|mln|million|thousand|тысяч\w*|миллион\w*)?",
        normalized,
    )
    if not match:
        return None
    value = Decimal(match.group(1))
    scale = match.group(2) or ""
    if scale in {"ming", "thousand"} or scale.startswith("тысяч"):
        value *= 1000
    elif scale in {"mln", "million"} or scale.startswith("миллион"):
        value *= 1_000_000
    return value
