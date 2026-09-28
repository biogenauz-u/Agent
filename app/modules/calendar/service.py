from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.modules.audit.actions import AuditAction
from app.modules.calendar.audit import CalendarAudit
from app.modules.calendar.client import GoogleCalendarClient
from app.modules.calendar.exceptions import CalendarConflictError, CalendarError
from app.modules.calendar.schemas import (
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarEventView,
    FreeBusyResult,
    TimeInterval,
)
from app.modules.calendar.utils import day_range, event_view, free_intervals


class ReminderSync(Protocol):
    async def sync_calendar(
        self, event_id: str, title: str, start: datetime, offsets: list[int] | None
    ) -> bool: ...
    async def cancel_calendar(self, event_id: str) -> bool: ...


class CalendarService:
    """Validated domain operations; Telegram confirmation is a separate action boundary."""

    def __init__(
        self,
        client: GoogleCalendarClient,
        audit: CalendarAudit,
        timezone: ZoneInfo,
        reminder_sync: ReminderSync | None = None,
    ) -> None:
        self.client, self.audit, self.timezone = client, audit, timezone
        self.reminder_sync = reminder_sync

    def payload(self, event: CalendarEventCreate) -> dict[str, Any]:
        return {
            "summary": event.title,
            "description": event.description,
            "location": event.location,
            "start": {
                "dateTime": event.start.astimezone(self.timezone).isoformat(),
                "timeZone": str(self.timezone),
            },
            "end": {
                "dateTime": event.end.astimezone(self.timezone).isoformat(),
                "timeZone": str(self.timezone),
            },
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": value} for value in event.reminders],
            },
        }

    def sorted_views(self, raw: list[dict[str, Any]]) -> list[CalendarEventView]:
        def key(event: CalendarEventView) -> datetime:
            return (
                datetime.combine(event.start, time.min, self.timezone)
                if event.all_day
                else event.start.astimezone(self.timezone)
            )

        return sorted((event_view(item) for item in raw), key=key)

    async def events_on(self, day: date) -> list[CalendarEventView]:
        window = day_range(day, self.timezone)
        return self.sorted_views(
            await self.client.list_events(window.start.isoformat(), window.end.isoformat(), 50)
        )

    async def get_today_events(self) -> list[CalendarEventView]:
        return await self.events_on(datetime.now(self.timezone).date())

    async def get_tomorrow_events(self) -> list[CalendarEventView]:
        return await self.events_on(datetime.now(self.timezone).date() + timedelta(days=1))

    async def list_upcoming_events(self) -> list[CalendarEventView]:
        return self.sorted_views(
            await self.client.list_events(datetime.now(UTC).isoformat(), None, 10)
        )

    async def get_event(self, event_id: str) -> CalendarEventView:
        return event_view(await self.client.get_event(event_id))

    async def create_event(
        self, event: CalendarEventCreate, action_id: str | None = None
    ) -> CalendarEventView:
        payload = self.payload(event)
        # Google accepts base32hex IDs: UUID hex is a valid subset and fences duplicate inserts.
        payload["id"] = action_id or uuid4().hex
        result = event_view(await self.client.create_event(payload))
        await self.audit.record(AuditAction.CALENDAR_EVENT_CREATED, result.id)
        if self.reminder_sync and isinstance(result.start, datetime):
            synced = await self.reminder_sync.sync_calendar(
                result.id, result.title, result.start, event.reminders
            )
            result.reminder_warning = not synced
        return result

    async def mutable_event(self, event_id: str, etag: str) -> CalendarEventView:
        event = await self.get_event(event_id)
        if event.recurring or event.all_day:
            raise CalendarError("Recurring/all-day changes are not supported in Step 5.")
        if not etag or event.etag != etag:
            raise CalendarConflictError("Event changed. Select it again before confirming.")
        return event

    async def update_event(
        self, event_id: str, event: CalendarEventUpdate, etag: str
    ) -> CalendarEventView:
        await self.mutable_event(event_id, etag)
        names = {"title": "summary", "start": "start", "end": "end", "reminders": "reminders"}
        complete = self.payload(event)
        payload = {names[field]: complete[names[field]] for field in event.fields}
        result = event_view(await self.client.update_event(event_id, payload, etag))
        await self.audit.record(AuditAction.CALENDAR_EVENT_UPDATED, result.id)
        if self.reminder_sync and isinstance(result.start, datetime):
            offsets = event.reminders if "reminders" in event.fields else None
            result.reminder_warning = not await self.reminder_sync.sync_calendar(
                result.id, result.title, result.start, offsets
            )
        return result

    async def delete_event(self, event_id: str, etag: str) -> bool:
        await self.mutable_event(event_id, etag)
        await self.client.delete_event(event_id, etag)
        await self.audit.record(AuditAction.CALENDAR_EVENT_DELETED, event_id)
        return not self.reminder_sync or await self.reminder_sync.cancel_calendar(event_id)

    async def get_free_busy(self, window: TimeInterval) -> FreeBusyResult:
        raw = await self.client.free_busy(
            window.start.isoformat(), window.end.isoformat(), str(self.timezone)
        )
        calendar = raw.get("calendars", {}).get(self.client.calendar_id)
        if calendar is None or calendar.get("errors"):
            raise CalendarError("Calendar availability could not be checked.")
        busy = [TimeInterval.model_validate(item) for item in calendar.get("busy", [])]
        return FreeBusyResult(busy=busy, free=free_intervals(window, busy))
