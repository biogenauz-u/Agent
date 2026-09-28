from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

UZBEK_MONTHS = (
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
)


def parse_clock(value: str) -> time:
    return time.fromisoformat(value)


def local_schedule(day: date, clock: time, timezone: ZoneInfo) -> datetime:
    return datetime.combine(day, clock, timezone)


def uzbek_date(day: date) -> str:
    return f"{day.day}-{UZBEK_MONTHS[day.month - 1]}"


def money(value: Decimal) -> str:
    decimals = 0 if value == value.to_integral() else 2
    return f"{value:,.{decimals}f}"
