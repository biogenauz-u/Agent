from datetime import timedelta

from app.database.models import ReminderStatus
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.reminders.audit import ReminderAudit
from app.modules.reminders.delivery import TelegramReminderDelivery
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.utils import utc_now


class ReminderDispatcher:
    """Claim, deliver, persist outcome, then arrange a bounded retry."""

    def __init__(
        self,
        database: DatabaseManager,
        delivery: TelegramReminderDelivery,
        audit: ReminderAudit,
        retry_delays: tuple[int, ...],
        *,
        now=utc_now,
    ) -> None:
        self.database, self.delivery, self.audit = database, delivery, audit
        self.retry_delays, self.now = retry_delays, now
        self.scheduler = None

    async def dispatch(self, reminder_id: int) -> None:
        now = self.now()
        async with self.database.session() as session:
            reminder = await ReminderRepository(session).claim(reminder_id, now)
        if reminder is None:
            return
        result = await self.delivery.deliver(reminder)
        completed = self.now()
        if result.success:
            async with self.database.session() as session:
                changed = await ReminderRepository(session).mark_delivered(reminder_id, completed)
            if changed:
                await self.audit.record(AuditAction.REMINDER_DELIVERED, reminder_id)
            return
        retry_at = None
        if reminder.attempt_count < reminder.max_attempts:
            delay_index = min(reminder.attempt_count - 1, len(self.retry_delays) - 1)
            retry_at = completed + timedelta(seconds=self.retry_delays[delay_index])
        async with self.database.session() as session:
            status = await ReminderRepository(session).mark_retry_or_failed(
                reminder_id, completed, retry_at, result.failure_reason or "delivery_failed"
            )
        if status == ReminderStatus.PENDING and retry_at is not None:
            await self.audit.record(AuditAction.REMINDER_RETRY, reminder_id, retry_at)
            if self.scheduler:
                self.scheduler.schedule_id(reminder_id, retry_at)
        elif status == ReminderStatus.FAILED:
            await self.audit.record(AuditAction.REMINDER_FAILED, reminder_id)
