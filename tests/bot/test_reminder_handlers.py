from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
from aiogram.methods import SendMessage
from aiogram.types import Update

from app.bot.constants import DENIED, LOCKED
from app.modules.calendar.state import MemoryTemporaryStore
from app.modules.reminders.actions import ReminderActions
from app.modules.reminders.schemas import ReminderView

from .conftest import Harness


def attach(harness: Harness) -> Mock:
    runtime = Mock()
    runtime.timezone = ZoneInfo("Asia/Tashkent")
    runtime.service.create_standalone = AsyncMock()
    runtime.service.cancel = AsyncMock()
    runtime.service.list_upcoming = AsyncMock(return_value=[])
    runtime.actions = ReminderActions(runtime.service, MemoryTemporaryStore(), 42)
    harness.context.reminders = runtime
    return runtime


async def callback(harness: Harness, data: str) -> None:
    harness.sequence += 1
    update = Update.model_validate(
        {
            "update_id": harness.sequence,
            "callback_query": {
                "id": str(harness.sequence),
                "from": {"id": 42, "is_bot": False, "first_name": "Test"},
                "chat_instance": "test",
                "data": data,
                "message": {
                    "message_id": 123,
                    "date": datetime.now(UTC),
                    "chat": {"id": 42, "type": "private"},
                },
            },
        },
        context={"bot": harness.bot},
    )
    await harness.dispatcher.feed_update(harness.bot, update)


@pytest.mark.parametrize("command", ["/remind", "/reminders", "/reminder_cancel"])
async def test_owner_and_lock_boundary(harness: Harness, command: str) -> None:
    attach(harness)
    await harness.send(command, user_id=99)
    assert harness.replies[-1] == DENIED
    await harness.send(command)
    assert harness.replies[-1] == LOCKED


async def test_remind_requires_confirmation_and_double_click_safe(harness: Harness) -> None:
    runtime = attach(harness)
    await harness.context.security.lock_state.unlock()
    future = datetime.now(ZoneInfo("Asia/Tashkent")) + timedelta(days=2)
    for text in ["/remind", "Call broker", future.strftime("%d.%m.%Y"), future.strftime("%H:%M")]:
        await harness.send(text)
    runtime.service.create_standalone.assert_not_called()
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    data = prompt.reply_markup.inline_keyboard[0][0].callback_data
    await callback(harness, data)
    await callback(harness, data)
    runtime.service.create_standalone.assert_awaited_once()
    assert "Reminder saqlandi." in harness.replies


async def test_reminders_formatting(harness: Harness) -> None:
    runtime = attach(harness)
    runtime.service.list_upcoming.return_value = [
        ReminderView(
            id=1,
            title="Call broker",
            message=None,
            remind_at="2026-09-25T12:00:00Z",
            event_start_at=None,
            offset_minutes=None,
            status="PENDING",
            channel="TELEGRAM",
            attempt_count=0,
            max_attempts=3,
            external_calendar_event_id=None,
        )
    ]
    await harness.context.security.lock_state.unlock()
    await harness.send("/reminders")
    assert "Call broker" in harness.replies[-1]
    assert "17:00" in harness.replies[-1]


async def test_cancel_requires_confirmation(harness: Harness) -> None:
    runtime = attach(harness)
    runtime.service.list_upcoming.return_value = [
        ReminderView(
            id=7,
            title="Call broker",
            message=None,
            remind_at="2026-09-25T12:00:00Z",
            event_start_at=None,
            offset_minutes=None,
            status="PENDING",
            channel="TELEGRAM",
            attempt_count=0,
            max_attempts=3,
            external_calendar_event_id=None,
        )
    ]
    await harness.context.security.lock_state.unlock()
    await harness.send("/reminder_cancel")
    await harness.send("1")
    runtime.service.cancel.assert_not_called()
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    await callback(harness, prompt.reply_markup.inline_keyboard[0][0].callback_data)
    runtime.service.cancel.assert_awaited_once_with(7)
