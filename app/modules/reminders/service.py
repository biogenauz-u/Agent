import logging
from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.database.models import Reminder, ReminderStatus
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.reminders.audit import ReminderAudit
from app.modules.reminders.exceptions import ReminderNotFoundError, ReminderValidationError
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.schemas import CalendarReminderCreate, ReminderCreate, ReminderView
from app.modules.reminders.utils import deduplication_key, utc_now
from app.modules.users.repository import UserRepository


class SchedulerPort(Protocol):
    def schedule_id(self, reminder_id: int, run_at: datetime) -> None: ...
    def remove_reminder(self, reminder_id: int) -> None: ...


class ReminderService:
    def __init__(
        self,
        database: DatabaseManager,
        owner_id: int,
        max_attempts: int,
        default_offset: int = 10,
        *,
        now=utc_now,
    ) -> None:
        self.database, self.owner_id = database, owner_id
        self.max_attempts, self.default_offset = max_attempts, default_offset
        self.now = now
        self.scheduler: SchedulerPort | None = None
        self.audit = ReminderAudit(database, owner_id)

    async def _owner(self, session) -> int:
        users = UserRepository(session)
        user = await users.get_by_telegram_user_id(self.owner_id)
        if user is None:
            user = await users.create(self.owner_id)
        return user.id

    def _view(self, reminder: Reminder) -> ReminderView:
        return ReminderView.model_validate(reminder, from_attributes=True)

    async def create_standalone(self, request: ReminderCreate) -> ReminderView:
        now = self.now()
        if request.remind_at.astimezone(UTC) <= now:
            raise ReminderValidationError("Reminder time must be in the future.")
        key = deduplication_key(
            "standalone",
            self.owner_id,
            uuid4().hex,
        )
        reminder = Reminder(
            user_id=0,
            title=request.title,
            message=request.message,
            remind_at=request.remind_at.astimezone(UTC),
            max_attempts=self.max_attempts,
            deduplication_key=key,
        )
        try:
            async with self.database.session() as session:
                reminder.user_id = await self._owner(session)
                existing = await ReminderRepository(session).find_by_deduplication_key(key)
                if existing:
                    return self._view(existing)
                await ReminderRepository(session).create(reminder)
        except IntegrityError:
            async with self.database.session() as session:
                existing = await ReminderRepository(session).find_by_deduplication_key(key)
                if existing is None:
                    raise
                return self._view(existing)
        if self.scheduler:
            self.scheduler.schedule_id(reminder.id, reminder.remind_at)
        await self.audit.record(AuditAction.REMINDER_CREATED, reminder.id, reminder.remind_at)
        return self._view(reminder)

    async def create_for_calendar(self, request: CalendarReminderCreate) -> list[ReminderView]:
        now = self.now()
        occurrences: list[tuple[Reminder, bool]] = []
        offsets = request.offsets or [self.default_offset]
        async with self.database.session() as session:
            owner = await self._owner(session)
            repository = ReminderRepository(session)
            for offset in offsets:
                remind_at = request.event_start_at.astimezone(UTC) - timedelta(minutes=offset)
                if remind_at <= now:
                    continue
                key = deduplication_key(
                    "calendar",
                    self.owner_id,
                    request.external_calendar_event_id,
                    request.event_start_at.astimezone(UTC).isoformat(),
                    offset,
                    "telegram",
                )
                reminder = Reminder(
                    user_id=owner,
                    external_calendar_event_id=request.external_calendar_event_id,
                    title=request.title,
                    remind_at=remind_at,
                    event_start_at=request.event_start_at.astimezone(UTC),
                    offset_minutes=offset,
                    max_attempts=self.max_attempts,
                    deduplication_key=key,
                )
                existing = await repository.find_by_deduplication_key(key)
                if existing:
                    occurrences.append((existing, False))
                    continue
                try:
                    async with session.begin_nested():
                        await repository.create(reminder)
                    occurrences.append((reminder, True))
                except IntegrityError:
                    existing = await repository.find_by_deduplication_key(key)
                    if existing is None:
                        raise
                    occurrences.append((existing, False))
        for reminder, was_created in occurrences:
            if self.scheduler and reminder.status == ReminderStatus.PENDING:
                self.scheduler.schedule_id(reminder.id, reminder.retry_at or reminder.remind_at)
            if was_created:
                await self.audit.record(
                    AuditAction.REMINDER_CREATED, reminder.id, reminder.remind_at
                )
        return [self._view(item) for item, _ in occurrences]

    async def list_upcoming(self, limit: int = 10) -> list[ReminderView]:
        async with self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            if user is None:
                return []
            rows = await ReminderRepository(session).list_upcoming(user.id, self.now(), limit)
            return [self._view(item) for item in rows]

    async def pending_count_for_date(self, day: date, timezone) -> int:
        rows = await self.list_upcoming(10_000)
        return sum(item.remind_at.astimezone(timezone).date() == day for item in rows)

    async def cancel(self, reminder_id: int) -> None:
        now = self.now()
        async with self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            if user is None or not await ReminderRepository(session).cancel(
                reminder_id, user.id, now
            ):
                raise ReminderNotFoundError("Pending reminder not found.")
        if self.scheduler:
            self.scheduler.remove_reminder(reminder_id)
        await self.audit.record(AuditAction.REMINDER_CANCELLED, reminder_id)

    async def reschedule(self, reminder_id: int, remind_at: datetime) -> ReminderView:
        remind_at = remind_at.astimezone(UTC)
        if remind_at <= self.now():
            raise ReminderValidationError("Reminder time must be in the future.")
        async with self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            reminder = (
                await ReminderRepository(session).reschedule(
                    reminder_id,
                    user.id,
                    remind_at,
                    deduplication_key("rescheduled", self.owner_id, reminder_id, uuid4().hex),
                )
                if user
                else None
            )
            if reminder is None:
                raise ReminderNotFoundError("Pending reminder not found.")
        if self.scheduler:
            self.scheduler.schedule_id(reminder.id, reminder.remind_at)
        await self.audit.record(AuditAction.REMINDER_RESCHEDULED, reminder.id, reminder.remind_at)
        return self._view(reminder)

    async def cancel_calendar(self, event_id: str) -> bool:
        now = self.now()
        async with self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            ids = (
                await ReminderRepository(session).cancel_calendar_pending(user.id, event_id, now)
                if user
                else []
            )
        for reminder_id in ids:
            if self.scheduler:
                self.scheduler.remove_reminder(reminder_id)
            await self.audit.record(AuditAction.REMINDER_CANCELLED, reminder_id)
        return True

    async def sync_calendar(
        self, event_id: str, title: str, start: datetime, offsets: list[int] | None
    ) -> bool:
        try:
            if offsets is None:
                async with self.database.session() as session:
                    user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
                    existing = (
                        await ReminderRepository(session).list_for_calendar_event(user.id, event_id)
                        if user
                        else []
                    )
                    offsets = sorted(
                        {
                            row.offset_minutes
                            for row in existing
                            if row.status == ReminderStatus.PENDING
                            and row.offset_minutes is not None
                        }
                    )
                offsets = offsets or [self.default_offset]
            await self.cancel_calendar(event_id)
            if not offsets:
                return True
            reminders = await self.create_for_calendar(
                CalendarReminderCreate(
                    external_calendar_event_id=event_id,
                    title=title,
                    event_start_at=start,
                    offsets=offsets or [self.default_offset],
                )
            )
            for reminder in reminders:
                await self.audit.record(
                    AuditAction.REMINDER_RESCHEDULED, reminder.id, reminder.remind_at
                )
            return True
        except Exception as error:  # noqa: BLE001 - Google action already succeeded
            logging.getLogger(__name__).warning(
                "calendar_reminder_sync_failed", extra={"error_type": type(error).__name__}
            )
            return False
