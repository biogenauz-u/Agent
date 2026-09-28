from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.database.models.task import TaskStatus

OPEN_STATUSES = (TaskStatus.TODO, TaskStatus.IN_PROGRESS)


def parse_local_time(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":"))
    return time(hour, minute)


def due_at_utc(day: date, local_time: time | None, timezone: ZoneInfo) -> datetime | None:
    if local_time is None:
        return None
    return datetime.combine(day, local_time, timezone).astimezone(UTC)


def effective_due(day: date | None, due_at: datetime | None, timezone: ZoneInfo) -> datetime | None:
    if due_at is not None:
        return due_at.astimezone(UTC)
    if day is not None:
        return datetime.combine(day + timedelta(days=1), time.min, timezone).astimezone(UTC)
    return None


def reminder_moment(
    day: date | None,
    due_at: datetime | None,
    offset_minutes: int,
    date_only_time: time,
    timezone: ZoneInfo,
) -> datetime | None:
    if due_at is not None:
        return due_at.astimezone(UTC) - timedelta(minutes=offset_minutes)
    if day is not None:
        return datetime.combine(day, date_only_time, timezone).astimezone(UTC)
    return None

