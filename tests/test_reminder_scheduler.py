from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.database.models import Reminder, ReminderStatus
from app.database.session import DatabaseManager
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.scheduler import ReminderScheduler
from app.modules.users.repository import UserRepository

NOW = datetime(2026, 9, 25, 10, tzinfo=UTC)


class FakeScheduler:
    def __init__(self):
        self.jobs = {}
        self.started = self.paused = self.stopped = False

    def start(self, paused=False):
        self.started, self.paused = True, paused

    def resume(self):
        self.paused = False

    def pause(self):
        self.paused = True

    def shutdown(self, wait=True):
        self.stopped = True

    def remove_all_jobs(self):
        self.jobs.clear()

    def add_job(self, func, trigger, args, id, **kwargs):
        self.jobs[id] = (func, trigger, args, kwargs)

    def get_job(self, identifier):
        return Mock(id=identifier) if identifier in self.jobs else None

    def remove_job(self, identifier):
        self.jobs.pop(identifier, None)


def database(engine):
    value = DatabaseManager(Settings(_env_file=None))
    value._sessions = async_sessionmaker(engine, expire_on_commit=False)
    return value


async def add(db, key, at, status=ReminderStatus.PENDING, processing=None):
    async with db.session() as session:
        user = await UserRepository(session).get_by_telegram_user_id(42)
        if not user:
            user = await UserRepository(session).create(42)
        return await ReminderRepository(session).create(
            Reminder(
                user_id=user.id,
                title=key,
                remind_at=at,
                status=status,
                processing_started_at=processing,
                max_attempts=3,
                deduplication_key=key,
            )
        )


async def test_stable_job_id_remove_and_recovery(engine) -> None:
    db, backend = database(engine), FakeScheduler()
    future = await add(db, "future", NOW + timedelta(hours=1))
    dispatcher = Mock(dispatch=AsyncMock(), scheduler=None)
    scheduler = ReminderScheduler(
        db, dispatcher, Mock(record=AsyncMock()), 60, 10, now=lambda: NOW, scheduler=backend
    )
    await scheduler.start()
    assert list(backend.jobs) == [f"reminder:{future.id}"]
    assert backend.jobs[f"reminder:{future.id}"][2] == [future.id]
    scheduler.remove_reminder(future.id)
    assert backend.jobs == {}
    await scheduler.shutdown()
    assert backend.stopped


async def test_overdue_policy_and_stale_processing(engine) -> None:
    db, backend = database(engine), FakeScheduler()
    recent = await add(db, "recent", NOW - timedelta(minutes=30))
    old = await add(db, "old", NOW - timedelta(minutes=61))
    stale = await add(
        db,
        "stale",
        NOW - timedelta(hours=1),
        ReminderStatus.PROCESSING,
        NOW - timedelta(minutes=20),
    )
    scheduler = ReminderScheduler(
        db,
        Mock(dispatch=AsyncMock(), scheduler=None),
        Mock(record=AsyncMock()),
        60,
        10,
        now=lambda: NOW,
        scheduler=backend,
    )
    await scheduler.start()
    assert f"reminder:{recent.id}" in backend.jobs
    assert f"reminder:{stale.id}" in backend.jobs
    assert f"reminder:{old.id}" not in backend.jobs
    async with db.session() as session:
        assert (await session.get(Reminder, old.id)).status == ReminderStatus.MISSED
        assert (await session.get(Reminder, stale.id)).status == ReminderStatus.PENDING
    await scheduler.shutdown()


async def test_stale_processing_at_max_attempts_fails(engine) -> None:
    db, backend = database(engine), FakeScheduler()
    reminder = await add(
        db,
        "stale-max",
        NOW - timedelta(hours=1),
        ReminderStatus.PROCESSING,
        NOW - timedelta(minutes=20),
    )
    async with db.session() as session:
        stored = await session.get(Reminder, reminder.id)
        stored.attempt_count = stored.max_attempts
    scheduler = ReminderScheduler(
        db,
        Mock(dispatch=AsyncMock(), scheduler=None),
        Mock(record=AsyncMock()),
        60,
        10,
        now=lambda: NOW,
        scheduler=backend,
    )
    await scheduler.start()
    async with db.session() as session:
        assert (await session.get(Reminder, reminder.id)).status == ReminderStatus.FAILED
    assert f"reminder:{reminder.id}" not in backend.jobs
    await scheduler.shutdown()


async def test_restart_rebuilds_from_database(engine) -> None:
    db = database(engine)
    reminder = await add(db, "restart", NOW + timedelta(hours=1))
    first = ReminderScheduler(
        db,
        Mock(dispatch=AsyncMock(), scheduler=None),
        Mock(record=AsyncMock()),
        60,
        10,
        now=lambda: NOW,
        scheduler=FakeScheduler(),
    )
    await first.start()
    await first.shutdown()
    second_backend = FakeScheduler()
    second = ReminderScheduler(
        db,
        Mock(dispatch=AsyncMock(), scheduler=None),
        Mock(record=AsyncMock()),
        60,
        10,
        now=lambda: NOW,
        scheduler=second_backend,
    )
    await second.start()
    assert f"reminder:{reminder.id}" in second_backend.jobs
    await second.shutdown()
