from datetime import UTC, date, datetime, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.database.models.daily import (
    DailyDelivery,
    DailyDeliveryStatus,
    DailyDeliveryType,
    DailySettings,
)
from app.database.session import DatabaseManager
from app.modules.daily.briefing import MorningBriefingFormatter
from app.modules.daily.evening import EveningSummaryFormatter
from app.modules.daily.repository import DailyRepository
from app.modules.daily.scheduler import DailyScheduler
from app.modules.daily.schemas import EveningSummaryData, FinanceLine, MorningBriefingData, Section
from app.modules.daily.service import DailyAutomationService

OWNER = 42
NOW = datetime(2026, 9, 25, 3, 30, tzinfo=UTC)


def manager(engine) -> DatabaseManager:
    database = DatabaseManager(Settings(_env_file=None))
    database._sessions = async_sessionmaker(engine, expire_on_commit=False)
    return database


def test_daily_config_defaults_and_validation() -> None:
    settings = Settings(_env_file=None)
    assert settings.daily_morning_time == time(8)
    assert settings.daily_evening_time == time(20)
    assert settings.daily_automation_grace_minutes == 120
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DAILY_MORNING_DEFAULT_TIME="25:00")


async def test_daily_settings_defaults_update_and_unique(engine) -> None:
    repository = DailyRepository(manager(engine), OWNER)
    first = await repository.get_or_create(time(8), time(20))
    second = await repository.get_or_create(time(9), time(21))
    assert first == second
    assert first.morning_enabled and first.morning_time == time(8)
    assert first.evening_enabled and first.evening_time == time(20)
    updated = await repository.update_morning(False, time(7, 15))
    assert not updated.morning_enabled and updated.morning_time == time(7, 15)
    async with async_sessionmaker(engine)() as session:
        assert len((await session.scalars(select(DailySettings))).all()) == 1


async def test_delivery_claim_is_unique_per_owner_type_date(engine) -> None:
    repository = DailyRepository(manager(engine), OWNER)
    day = date(2026, 9, 25)
    first = await repository.claim(DailyDeliveryType.MORNING, day, NOW)
    duplicate = await repository.claim(DailyDeliveryType.MORNING, day, NOW)
    evening = await repository.claim(DailyDeliveryType.EVENING, day, NOW)
    assert first and evening and duplicate is None
    await repository.mark(first, DailyDeliveryStatus.DELIVERED)
    assert await repository.already_delivered(DailyDeliveryType.MORNING, day)
    async with async_sessionmaker(engine)() as session:
        row = await session.get(DailyDelivery, first)
        assert row and row.delivered_at and row.delivered_at.tzinfo is not None


def morning_data(**changes) -> MorningBriefingData:
    values = {
        "day": date(2026, 9, 25),
        "calendar": Section(details=["10:00 — Office"]),
        "tasks": Section(details=["Bugun: 5", "Kechikkan: 1", "Muhim: 2"]),
        "email": Section(details=["Yangi: 3", "O'qilmagan: 7"]),
        "reminders": Section(details=["Bugun: 4"]),
        "finance": Section(),
        "notebook": Section(details=["Kecha: 2 ta yangi yozuv"]),
        "personal_telegram": Section(details=["Yangi private xabarlar: 5"]),
        "finance_lines": [FinanceLine(currency="UZS", expense=Decimal(450000))],
    }
    values.update(changes)
    return MorningBriefingData(**values)


def test_morning_formatter_sections_currency_and_length() -> None:
    text = MorningBriefingFormatter().format(morning_data())
    for expected in ("25-sentabr", "Office", "Kechikkan: 1", "450,000", "UZS"):
        assert expected in text
    assert len(text) <= 4000


def test_morning_formatter_fail_soft_section() -> None:
    text = MorningBriefingFormatter().format(
        morning_data(email=Section(status="unavailable"))
    )
    assert "📧 Email\nVaqtinchalik mavjud emas" in text
    assert "✅ Tasks" in text


def test_evening_formatter_has_unfinished_prompt_and_multicurrency() -> None:
    data = EveningSummaryData(
        day=date(2026, 9, 25),
        tasks=Section(details=["Bajarildi: 4", "Qoldi: 2"]),
        calendar=Section(details=["3 ta event"]),
        finance=Section(),
        email=Section(details=["12 ta yangi"]),
        notebook=Section(details=["4 ta yozuv"]),
        personal_telegram=Section(details=["8 ta yangi xabar"]),
        unfinished_task_ids=[1, 2],
        finance_lines=[
            FinanceLine(currency="UZS", expense=Decimal(670000)),
            FinanceLine(currency="USD", expense=Decimal(25)),
        ],
    )
    text = EveningSummaryFormatter().format(data)
    assert "Bajarildi: 4" in text and "Ertangi kunga" in text
    assert "670,000" in text and "25" in text and "USD" in text


class FakeScheduler:
    def __init__(self) -> None:
        self.jobs = {}
        self.started = self.resumed = self.shutdown_called = False

    def start(self, paused=False): self.started = True
    def resume(self): self.resumed = True
    def shutdown(self, wait=True): self.shutdown_called = True
    def get_jobs(self): return list(self.jobs.values())
    def remove_job(self, job_id): self.jobs.pop(job_id, None)
    def add_job(self, func, trigger, *, args, id, **kwargs):
        self.jobs[id] = SimpleNamespace(id=id, func=func, trigger=trigger, args=args)


async def test_scheduler_stable_ids_timezone_and_recovery() -> None:
    settings = SimpleNamespace(
        morning_enabled=True, morning_time=time(8),
        evening_enabled=True, evening_time=time(20),
    )
    repository = SimpleNamespace(get_or_create=AsyncMock(return_value=settings))
    service = SimpleNamespace(owner_id=OWNER, deliver=AsyncMock())
    fake = FakeScheduler()
    scheduler = DailyScheduler(
        service, repository, Settings(_env_file=None).timezone,
        time(8), time(20), 120, now=lambda: NOW, scheduler=fake,
    )
    await scheduler.start()
    assert set(fake.jobs) == {"daily:morning:42", "daily:evening:42"}
    assert str(fake.jobs["daily:morning:42"].trigger.timezone) == "Asia/Tashkent"
    service.deliver.assert_awaited_once_with(DailyDeliveryType.MORNING, NOW.astimezone(Settings(_env_file=None).timezone))
    await scheduler.shutdown()
    assert fake.jobs == {} and not fake.shutdown_called


@pytest.mark.parametrize(
    ("hour", "expected"), [(2, 0), (3, 1), (5, 1), (6, 0)]
)
async def test_morning_grace_window(hour: int, expected: int) -> None:
    zone = Settings(_env_file=None).timezone
    current = datetime(2026, 9, 25, hour, tzinfo=UTC)
    settings = SimpleNamespace(
        morning_enabled=True, morning_time=time(8), evening_enabled=False, evening_time=time(20)
    )
    service = SimpleNamespace(owner_id=OWNER, deliver=AsyncMock())
    scheduler = DailyScheduler(
        service, SimpleNamespace(), zone, time(8), time(20), 120,
        now=lambda: current, scheduler=FakeScheduler(),
    )
    await scheduler.recover(settings)
    assert service.deliver.await_count == expected


async def test_collection_is_fail_soft_and_uses_services() -> None:
    task_summary = SimpleNamespace(total=2, done=1, remaining=1, overdue=1, urgent=1)
    tasks = SimpleNamespace(
        service=SimpleNamespace(
            get_daily_summary=AsyncMock(return_value=task_summary),
            list_unfinished_for_date=AsyncMock(return_value=[]),
        )
    )
    app = SimpleNamespace(
        settings=Settings(_env_file=None), database=None,
        calendar=SimpleNamespace(service=SimpleNamespace(events_on=AsyncMock(side_effect=RuntimeError))),
        tasks=tasks, email=None, reminders=None, finance=None,
        notebook=None, personal_telegram=None,
    )
    service = DailyAutomationService(app, SimpleNamespace(), AsyncMock(), OWNER)
    data = await service.morning_data(NOW)
    assert data.calendar.status == "unavailable"
    assert data.tasks.details == ["Bugun: 2", "Kechikkan: 1", "Muhim: 1"]
    assert data.email.status == "not_configured"


async def test_carry_forward_calls_task_service_once_and_never_automatically() -> None:
    carry = AsyncMock(return_value=[SimpleNamespace(id=1), SimpleNamespace(id=2)])
    app = SimpleNamespace(
        settings=Settings(_env_file=None), database=None,
        tasks=SimpleNamespace(service=SimpleNamespace(carry_forward_tasks=carry)),
    )
    service = DailyAutomationService(app, SimpleNamespace(), AsyncMock(), OWNER)
    assert carry.await_count == 0
    assert await service.carry_forward([1, 2], NOW) == 2
    carry.assert_awaited_once_with([1, 2], date(2026, 9, 26))
