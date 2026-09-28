import asyncio
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from aiogram import Bot

from app.database.models.daily import DailyDeliveryStatus, DailyDeliveryType
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.daily.briefing import MorningBriefingFormatter
from app.modules.daily.evening import EveningSummaryFormatter
from app.modules.daily.repository import DailyRepository
from app.modules.daily.schemas import (
    EveningSummaryData,
    FinanceLine,
    MorningBriefingData,
    Section,
)
from app.modules.daily.utils import local_schedule
from app.modules.users.repository import UserRepository

logger = logging.getLogger(__name__)


class DailyAutomationService:
    """Fail-soft aggregation over existing application services."""

    def __init__(self, application, repository: DailyRepository, bot: Bot, owner_id: int) -> None:
        self.app, self.repository, self.bot, self.owner_id = application, repository, bot, owner_id
        self.timezone = application.settings.timezone
        self.morning_formatter = MorningBriefingFormatter()
        self.evening_formatter = EveningSummaryFormatter()

    async def _section(self, name: str, operation) -> tuple[object | None, Section]:
        runtime = getattr(self.app, name, None)
        if runtime is None:
            return None, Section(status="not_configured")
        try:
            return await operation(runtime), Section()
        except Exception as error:  # noqa: BLE001 - one integration cannot suppress briefing
            logger.warning("daily_section_unavailable", extra={"section": name, "error_type": type(error).__name__})
            return None, Section(status="unavailable")

    async def morning_data(self, now: datetime | None = None) -> MorningBriefingData:
        local = (now or datetime.now(UTC)).astimezone(self.timezone)
        day, yesterday = local.date(), local.date() - timedelta(days=1)
        events, calendar = await self._section("calendar", lambda r: r.service.events_on(day))
        summary, tasks = await self._section("tasks", lambda r: r.service.get_daily_summary(day))
        emails, email = await self._section(
            "email", lambda r: r.service.daily_counts(day, self.timezone)
        )
        reminders, reminder_section = await self._section(
            "reminders", lambda r: r.service.pending_count_for_date(day, self.timezone)
        )
        transactions, finance = await self._section(
            "finance", lambda r: r.service.totals_for_date(yesterday)
        )
        notes, notebook = await self._section(
            "notebook", lambda r: r.service.count_for_date(yesterday)
        )
        messages, personal = await self._section(
            "personal_telegram",
            lambda r: r.service.incoming_count_for_date(day, self.timezone),
        )

        if events is not None:
            calendar.count = len(events)
            calendar.details = [self._event_line(item) for item in events[:10]]
            if len(events) > 10:
                calendar.details.append(f"+{len(events) - 10} ta boshqa event")
        if summary is not None:
            tasks.count = summary.total
            tasks.details = [f"Bugun: {summary.total}", f"Kechikkan: {summary.overdue}", f"Muhim: {summary.urgent}"]
        if emails is not None:
            new, unread = emails
            email.count = new
            email.details = [f"Yangi: {new}", f"O'qilmagan: {unread}"]
        if reminders is not None:
            reminder_section.count = reminders
            reminder_section.details = [f"Bugun: {reminders}"]
        finance_lines = self._finance(transactions or {}) if transactions is not None else []
        if notes is not None:
            notebook.count = notes
            notebook.details = [f"Kecha: {notes} ta yangi yozuv"]
        if messages is not None:
            personal.count = messages
            personal.details = [f"Yangi private xabarlar: {messages}"]
        return MorningBriefingData(
            day=day, calendar=calendar, tasks=tasks, email=email,
            reminders=reminder_section, finance=finance, notebook=notebook,
            personal_telegram=personal, finance_lines=finance_lines,
        )

    async def evening_data(self, now: datetime | None = None) -> EveningSummaryData:
        local = (now or datetime.now(UTC)).astimezone(self.timezone)
        day = local.date()
        summary, tasks = await self._section("tasks", lambda r: r.service.get_daily_summary(day))
        unfinished, _ = await self._section("tasks", lambda r: r.service.list_unfinished_for_date(day))
        events, calendar = await self._section("calendar", lambda r: r.service.events_on(day))
        transactions, finance = await self._section(
            "finance", lambda r: r.service.totals_for_date(day)
        )
        emails, email = await self._section(
            "email", lambda r: r.service.daily_counts(day, self.timezone)
        )
        notes, notebook = await self._section(
            "notebook", lambda r: r.service.count_for_date(day)
        )
        messages, personal = await self._section(
            "personal_telegram",
            lambda r: r.service.incoming_count_for_date(day, self.timezone),
        )
        if summary is not None:
            tasks.details = [f"Bajarildi: {summary.done}", f"Qoldi: {summary.remaining}", f"Kechikkan: {summary.overdue}"]
        if events is not None:
            calendar.count = len(events)
            calendar.details = [f"{len(events)} ta event"]
        if emails is not None:
            email.details = [f"{emails[0]} ta yangi"]
        if notes is not None:
            notebook.details = [f"{notes} ta yozuv"]
        if messages is not None:
            personal.details = [f"{messages} ta yangi xabar"]
        return EveningSummaryData(
            day=day, tasks=tasks, calendar=calendar, finance=finance, email=email,
            notebook=notebook, personal_telegram=personal,
            unfinished_task_ids=[item.id for item in (unfinished or [])],
            finance_lines=self._finance(transactions or {}) if transactions is not None else [],
        )

    async def morning_text(self, now: datetime | None = None) -> str:
        return self.morning_formatter.format(await self.morning_data(now))

    async def evening_text(self, now: datetime | None = None) -> tuple[str, list[int]]:
        data = await self.evening_data(now)
        return self.evening_formatter.format(data), data.unfinished_task_ids

    async def deliver(self, kind: DailyDeliveryType, now: datetime | None = None) -> bool:
        current = (now or datetime.now(UTC)).astimezone(self.timezone)
        settings = await self.repository.get_or_create(
            self.app.settings.daily_morning_time, self.app.settings.daily_evening_time
        )
        clock = settings.morning_time if kind == DailyDeliveryType.MORNING else settings.evening_time
        scheduled = local_schedule(current.date(), clock, self.timezone)
        delivery_id = await self.repository.claim(kind, current.date(), scheduled)
        if delivery_id is None:
            return False
        try:
            text = await self.morning_text(current) if kind == DailyDeliveryType.MORNING else (await self.evening_text(current))[0]
            attempts = self.app.settings.daily_delivery_max_attempts
            for attempt in range(attempts):
                try:
                    await self.bot.send_message(self.owner_id, text)
                    break
                except Exception:
                    if attempt + 1 >= attempts:
                        raise
                    await asyncio.sleep((60, 300, 900)[min(attempt, 2)])
            await self.repository.mark(delivery_id, DailyDeliveryStatus.DELIVERED)
            await self.audit(
                AuditAction.MORNING_BRIEFING_SENT if kind == DailyDeliveryType.MORNING else AuditAction.EVENING_SUMMARY_SENT,
                {"date": current.date().isoformat(), "delivery_type": kind.value},
            )
            return True
        except Exception:
            await self.repository.mark(delivery_id, DailyDeliveryStatus.FAILED)
            await self.audit(AuditAction.DAILY_DELIVERY_FAILED, {"date": current.date().isoformat(), "delivery_type": kind.value})
            raise

    async def carry_forward(self, task_ids: list[int], now: datetime | None = None) -> int:
        tomorrow = (now or datetime.now(UTC)).astimezone(self.timezone).date() + timedelta(days=1)
        rows = await self.app.tasks.service.carry_forward_tasks(task_ids, tomorrow)
        await self.audit(AuditAction.TASK_CARRY_FORWARD_CONFIRMED, {"task_count": len(rows), "date": tomorrow.isoformat()})
        return len(rows)

    async def audit(self, action: AuditAction, details: dict[str, object]) -> None:
        if self.app.database is None:
            return
        try:
            async with self.app.database.session() as session:
                owner = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
                await AuditService(AuditRepository(session)).log_event(
                    action,
                    user_id=owner.id if owner else None,
                    entity_type="daily_automation",
                    details=details,
                )
        except Exception as error:  # noqa: BLE001 - delivery remains authoritative
            logger.warning(
                "daily_audit_failed", extra={"error_type": type(error).__name__}
            )

    @staticmethod
    def _event_line(event) -> str:
        if isinstance(event.start, datetime):
            return f"{event.start.strftime('%H:%M')} — {event.title}"
        return f"Kun bo'yi — {event.title}"

    @staticmethod
    def _finance(values: dict[str, dict[str, Decimal]]) -> list[FinanceLine]:
        return [FinanceLine(currency=currency, **totals) for currency, totals in sorted(values.items())]
