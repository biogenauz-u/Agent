from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from app.modules.tasks.exceptions import TaskValidationError
from app.modules.tasks.reminders import TaskReminderAdapter


async def test_date_only_reminder_uses_configured_local_time() -> None:
    service = AsyncMock()
    service.create_standalone.return_value.id = 11
    adapter = TaskReminderAdapter(service, ZoneInfo("Asia/Tashkent"), time(9))
    await adapter.create(1, "task", date(2026, 9, 25), None, 60, datetime(2026, 9, 24, tzinfo=UTC))
    request = service.create_standalone.await_args.args[0]
    assert request.remind_at == datetime(2026, 9, 25, 4, tzinfo=UTC)


async def test_timed_reminder_offset_and_past_rejection() -> None:
    service = AsyncMock()
    service.create_standalone.return_value.id = 11
    adapter = TaskReminderAdapter(service, ZoneInfo("Asia/Tashkent"), time(9))
    due = datetime(2026, 9, 25, 10, tzinfo=UTC)
    await adapter.create(1, "task", due.date(), due, 60, datetime(2026, 9, 24, tzinfo=UTC))
    assert service.create_standalone.await_args.args[0].remind_at == due - timedelta(hours=1)
    with pytest.raises(TaskValidationError):
        await adapter.create(1, "task", due.date(), due, 60, due)
