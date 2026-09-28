from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Reminder, ReminderStatus


class ReminderRepository:
    """Transaction-local reminder persistence; callers own commit boundaries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, reminder: Reminder) -> Reminder:
        self.session.add(reminder)
        await self.session.flush()
        return reminder

    async def get_by_id(self, reminder_id: int) -> Reminder | None:
        return await self.session.get(Reminder, reminder_id)

    async def find_by_deduplication_key(self, key: str) -> Reminder | None:
        return await self.session.scalar(select(Reminder).where(Reminder.deduplication_key == key))

    async def list_pending(self, user_id: int | None = None, limit: int = 1000) -> list[Reminder]:
        statement = select(Reminder).where(Reminder.status == ReminderStatus.PENDING)
        if user_id is not None:
            statement = statement.where(Reminder.user_id == user_id)
        next_run = func.coalesce(Reminder.retry_at, Reminder.remind_at)
        return list((await self.session.scalars(statement.order_by(next_run).limit(limit))).all())

    async def list_due(self, now: datetime, limit: int = 100) -> list[Reminder]:
        next_run = func.coalesce(Reminder.retry_at, Reminder.remind_at)
        result = await self.session.scalars(
            select(Reminder)
            .where(Reminder.status == ReminderStatus.PENDING, next_run <= now)
            .order_by(next_run)
            .limit(limit)
        )
        return list(result.all())

    async def list_upcoming(self, user_id: int, now: datetime, limit: int = 10) -> list[Reminder]:
        next_run = func.coalesce(Reminder.retry_at, Reminder.remind_at)
        result = await self.session.scalars(
            select(Reminder)
            .where(
                Reminder.user_id == user_id,
                Reminder.status == ReminderStatus.PENDING,
                next_run > now,
            )
            .order_by(next_run)
            .limit(limit)
        )
        return list(result.all())

    async def list_for_calendar_event(self, user_id: int, event_id: str) -> list[Reminder]:
        return list(
            (
                await self.session.scalars(
                    select(Reminder)
                    .where(
                        Reminder.user_id == user_id,
                        Reminder.external_calendar_event_id == event_id,
                    )
                    .order_by(Reminder.remind_at)
                )
            ).all()
        )

    async def claim(self, reminder_id: int, now: datetime) -> Reminder | None:
        """Atomic PENDING to PROCESSING transition; only one worker receives a row."""
        next_run = func.coalesce(Reminder.retry_at, Reminder.remind_at)
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.status == ReminderStatus.PENDING,
                next_run <= now,
            )
            .values(
                status=ReminderStatus.PROCESSING,
                processing_started_at=now,
                last_attempt_at=now,
                attempt_count=Reminder.attempt_count + 1,
            )
            .returning(Reminder)
        )
        return result.scalar_one_or_none()

    async def mark_delivered(self, reminder_id: int, now: datetime) -> bool:
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.status == ReminderStatus.PROCESSING,
            )
            .values(
                status=ReminderStatus.DELIVERED,
                delivered_at=now,
                processing_started_at=None,
                retry_at=None,
                failure_reason=None,
            )
        )
        return bool(result.rowcount)

    async def mark_retry_or_failed(
        self, reminder_id: int, now: datetime, retry_at: datetime | None, reason: str
    ) -> ReminderStatus | None:
        status = ReminderStatus.PENDING if retry_at else ReminderStatus.FAILED
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.status == ReminderStatus.PROCESSING,
            )
            .values(
                status=status,
                retry_at=retry_at,
                failed_at=None if retry_at else now,
                processing_started_at=None,
                failure_reason=reason,
            )
            .returning(Reminder.status)
        )
        return result.scalar_one_or_none()

    async def mark_missed(self, reminder_id: int, now: datetime) -> bool:
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.status == ReminderStatus.PENDING,
            )
            .values(
                status=ReminderStatus.MISSED,
                failed_at=now,
                failure_reason="overdue_grace_exceeded",
                retry_at=None,
            )
        )
        return bool(result.rowcount)

    async def cancel(self, reminder_id: int, user_id: int, now: datetime) -> bool:
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id,
                Reminder.status == ReminderStatus.PENDING,
            )
            .values(status=ReminderStatus.CANCELLED, cancelled_at=now, retry_at=None)
        )
        return bool(result.rowcount)

    async def reschedule(
        self, reminder_id: int, user_id: int, remind_at: datetime, key: str
    ) -> Reminder | None:
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id,
                Reminder.status == ReminderStatus.PENDING,
            )
            .values(
                remind_at=remind_at,
                retry_at=None,
                failure_reason=None,
                deduplication_key=key,
            )
            .returning(Reminder)
        )
        return result.scalar_one_or_none()

    async def cancel_calendar_pending(
        self, user_id: int, event_id: str, now: datetime
    ) -> list[int]:
        result = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.user_id == user_id,
                Reminder.external_calendar_event_id == event_id,
                Reminder.status == ReminderStatus.PENDING,
            )
            .values(status=ReminderStatus.CANCELLED, cancelled_at=now, retry_at=None)
            .returning(Reminder.id)
        )
        return list(result.scalars().all())

    async def recover_stale(self, before: datetime, now: datetime) -> tuple[list[int], list[int]]:
        failed = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.status == ReminderStatus.PROCESSING,
                Reminder.processing_started_at < before,
                Reminder.attempt_count >= Reminder.max_attempts,
            )
            .values(
                status=ReminderStatus.FAILED,
                processing_started_at=None,
                failed_at=now,
                failure_reason="stale_processing_max_attempts",
            )
            .returning(Reminder.id)
        )
        recovered = await self.session.execute(
            update(Reminder)
            .where(
                Reminder.status == ReminderStatus.PROCESSING,
                Reminder.processing_started_at < before,
                Reminder.attempt_count < Reminder.max_attempts,
            )
            .values(
                status=ReminderStatus.PENDING,
                processing_started_at=None,
                retry_at=now,
                failure_reason="stale_processing_recovered",
            )
            .returning(Reminder.id)
        )
        return list(recovered.scalars().all()), list(failed.scalars().all())
