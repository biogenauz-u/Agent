from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.modules.calendar.schemas import CalendarEventView, TimeInterval


def day_range(day: date, timezone: ZoneInfo) -> TimeInterval:
    return TimeInterval(
        start=datetime.combine(day, time.min, timezone),
        end=datetime.combine(day + timedelta(days=1), time.min, timezone),
    )


def parse_local(day: str, clock: str, timezone: ZoneInfo) -> datetime:
    aware = datetime.strptime(f"{day} {clock}", "%d.%m.%Y %H:%M").replace(tzinfo=timezone)
    # Reject ambiguous/nonexistent wall time rather than silently choosing a DST fold.
    if aware.utcoffset() != aware.replace(fold=1).utcoffset():
        raise ValueError("Ambiguous or nonexistent local time")
    return aware


def event_view(raw: dict[str, Any]) -> CalendarEventView:
    all_day = "date" in raw["start"]
    parse = date.fromisoformat if all_day else datetime.fromisoformat
    field = "date" if all_day else "dateTime"
    return CalendarEventView(
        id=raw["id"],
        etag=raw.get("etag", ""),
        title=raw.get("summary", "(Untitled)"),
        start=parse(raw["start"][field]),
        end=parse(raw["end"][field]),
        all_day=all_day,
        recurring=bool(raw.get("recurringEventId") or raw.get("recurrence")),
        description=raw.get("description", ""),
        location=raw.get("location", ""),
        reminders=[
            r["minutes"]
            for r in raw.get("reminders", {}).get("overrides", [])
            if r.get("method") == "popup"
        ],
    )


def free_intervals(window: TimeInterval, busy: list[TimeInterval]) -> list[TimeInterval]:
    """Clip and merge overlapping/adjacent busy intervals; return their complement."""
    cursor = window.start
    result: list[TimeInterval] = []
    for interval in sorted(busy, key=lambda item: item.start):
        start, end = max(interval.start, window.start), min(interval.end, window.end)
        if end <= start:
            continue
        if start > cursor:
            result.append(TimeInterval(start=cursor, end=start))
        cursor = max(cursor, end)
    if cursor < window.end:
        result.append(TimeInterval(start=cursor, end=window.end))
    return result


def event_label(event: CalendarEventView, timezone: ZoneInfo) -> str:
    when = (
        f"{event.start:%d.%m.%Y} All day"
        if event.all_day
        else event.start.astimezone(timezone).strftime("%d.%m.%Y %H:%M")
    )
    return f"{when} - {event.title[:200]}"
