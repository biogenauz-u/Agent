from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database.models.daily import DailyDeliveryType
from app.modules.daily.repository import DailyRepository
from app.modules.daily.service import DailyAutomationService
from app.modules.daily.utils import local_schedule


class DailyScheduler:
    def __init__(
        self,
        service: DailyAutomationService,
        repository: DailyRepository,
        timezone,
        default_morning,
        default_evening,
        grace_minutes: int,
        *,
        now=lambda: datetime.now(UTC),
        scheduler: AsyncIOScheduler | None = None,
    ) -> None:
        self.service, self.repository, self.timezone = service, repository, timezone
        self.default_morning, self.default_evening = default_morning, default_evening
        self.grace = timedelta(minutes=grace_minutes)
        self.now = now
        self._owns_scheduler = scheduler is None
        self.scheduler = scheduler or AsyncIOScheduler(timezone=timezone)
        self.running = False

    @staticmethod
    def job_id(kind: DailyDeliveryType, owner_id: int) -> str:
        return f"daily:{kind.value.casefold()}:{owner_id}"

    async def start(self) -> None:
        if self.running:
            return
        settings = await self.repository.get_or_create(self.default_morning, self.default_evening)
        if self._owns_scheduler:
            self.scheduler.start(paused=True)
        try:
            self.restore(settings)
            await self.recover(settings)
            if self._owns_scheduler:
                self.scheduler.resume()
            self.running = True
        except BaseException:
            if self._owns_scheduler:
                self.scheduler.shutdown(wait=False)
            raise

    def restore(self, settings) -> None:
        for job in self.scheduler.get_jobs():
            if job.id.startswith("daily:"):
                self.scheduler.remove_job(job.id)
        for kind, enabled, clock in (
            (DailyDeliveryType.MORNING, settings.morning_enabled, settings.morning_time),
            (DailyDeliveryType.EVENING, settings.evening_enabled, settings.evening_time),
        ):
            if enabled:
                self.scheduler.add_job(
                    self.service.deliver,
                    CronTrigger(hour=clock.hour, minute=clock.minute, timezone=self.timezone),
                    args=[kind],
                    id=self.job_id(kind, self.service.owner_id),
                    replace_existing=True,
                    coalesce=True,
                    max_instances=1,
                    misfire_grace_time=int(self.grace.total_seconds()),
                )

    async def recover(self, settings) -> None:
        current = self.now().astimezone(self.timezone)
        for kind, enabled, clock in (
            (DailyDeliveryType.MORNING, settings.morning_enabled, settings.morning_time),
            (DailyDeliveryType.EVENING, settings.evening_enabled, settings.evening_time),
        ):
            scheduled = local_schedule(current.date(), clock, self.timezone)
            if enabled and scheduled <= current <= scheduled + self.grace:
                await self.service.deliver(kind, current)

    async def reload(self) -> None:
        settings = await self.repository.get_or_create(self.default_morning, self.default_evening)
        self.restore(settings)

    async def shutdown(self) -> None:
        if not self.running:
            return
        self.running = False
        for job in self.scheduler.get_jobs():
            if job.id.startswith("daily:"):
                self.scheduler.remove_job(job.id)
        if self._owns_scheduler:
            self.scheduler.shutdown(wait=True)
