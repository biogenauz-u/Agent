import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.reminders.audit import ReminderAudit
from app.modules.reminders.dispatcher import ReminderDispatcher
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.utils import job_id, utc_now


class ReminderScheduler:
    """In-memory wake-up index rebuilt from PostgreSQL on every startup."""

    def __init__(
        self,
        database: DatabaseManager,
        dispatcher: ReminderDispatcher,
        audit: ReminderAudit,
        overdue_grace_minutes: int,
        processing_timeout_minutes: int,
        *,
        now=utc_now,
        scheduler: AsyncIOScheduler | None = None,
    ) -> None:
        self.database, self.dispatcher, self.audit = database, dispatcher, audit
        self.overdue_grace = timedelta(minutes=overdue_grace_minutes)
        self.processing_timeout = timedelta(minutes=processing_timeout_minutes)
        self.now = now
        self.scheduler = scheduler or AsyncIOScheduler(timezone="UTC")
        self.running = False
        dispatcher.scheduler = self

    async def start(self) -> None:
        if self.running:
            return
        self.scheduler.start(paused=True)
        try:
            await self.recover_pending()
            self.scheduler.resume()
            self.running = True
        except BaseException:
            self.scheduler.shutdown(wait=False)
            raise

    async def shutdown(self) -> None:
        if not self.running:
            return
        self.running = False
        self.scheduler.pause()
        self.scheduler.remove_all_jobs()
        self.scheduler.shutdown(wait=True)

    def schedule_id(self, reminder_id: int, run_at: datetime) -> None:
        self.scheduler.add_job(
            self.dispatcher.dispatch,
            DateTrigger(run_date=run_at),
            args=[reminder_id],
            id=job_id(reminder_id),
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=None,
        )

    def remove_reminder(self, reminder_id: int) -> None:
        job = self.scheduler.get_job(job_id(reminder_id))
        if job is not None:
            self.scheduler.remove_job(job.id)

    async def recover_pending(self) -> None:
        now = self.now()
        async with self.database.session() as session:
            repository = ReminderRepository(session)
            stale, stale_failed = await repository.recover_stale(now - self.processing_timeout, now)
            pending = await repository.list_pending()
        if stale:
            logging.getLogger(__name__).warning(
                "stale_reminders_recovered", extra={"action": "recovery"}
            )
        for reminder_id in stale_failed:
            await self.audit.record(AuditAction.REMINDER_FAILED, reminder_id)
        for reminder in pending:
            run_at = reminder.retry_at or reminder.remind_at
            overdue = now - run_at
            if overdue > self.overdue_grace:
                async with self.database.session() as session:
                    missed = await ReminderRepository(session).mark_missed(reminder.id, now)
                if missed:
                    await self.audit.record(AuditAction.REMINDER_FAILED, reminder.id)
                continue
            self.schedule_id(reminder.id, max(run_at, now))
