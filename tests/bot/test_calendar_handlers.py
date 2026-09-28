from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram.methods import SendMessage
from aiogram.types import Update

from app.bot.constants import DENIED, LOCKED
from app.modules.calendar.actions import CalendarActions
from app.modules.calendar.state import MemoryTemporaryStore

from .conftest import Harness


def attach(harness: Harness) -> Mock:
    calendar = Mock()
    calendar.settings.timezone = __import__("zoneinfo").ZoneInfo("Asia/Tashkent")
    calendar.settings.calendar_default_event_duration_minutes = 60
    calendar.settings.google_calendar_id = "primary"
    calendar.store.load = AsyncMock(return_value=None)
    calendar.service.create_event = AsyncMock()
    calendar.service.get_today_events = AsyncMock(return_value=[])
    calendar.service.get_tomorrow_events = AsyncMock(return_value=[])
    calendar.service.list_upcoming_events = AsyncMock(return_value=[])
    calendar.oauth.unlocked = AsyncMock()
    calendar.actions = CalendarActions(calendar.service, calendar.oauth, MemoryTemporaryStore(), 42)
    harness.context.calendar = calendar
    return calendar


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


@pytest.mark.parametrize(
    "command",
    [
        "/calendar",
        "/today",
        "/tomorrow",
        "/upcoming",
        "/event_add",
        "/event_update",
        "/event_delete",
        "/free",
        "/google_connect",
        "/google_disconnect",
    ],
)
async def test_calendar_owner_lock_boundary(harness: Harness, command: str) -> None:
    calendar = attach(harness)
    await harness.send(command, user_id=99)
    assert harness.replies[-1] == DENIED
    await harness.send(command)
    assert harness.replies[-1] == LOCKED
    calendar.service.create_event.assert_not_called()


async def test_create_fsm_and_double_click(harness: Harness) -> None:
    calendar = attach(harness)
    await harness.context.security.lock_state.unlock()
    for text in ["/event_add", "Meeting", "25.09.2026", "15:00", "-", "-"]:
        await harness.send(text)
    assert "saqlansinmi" in harness.replies[-1]
    calendar.service.create_event.assert_not_called()
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    data = prompt.reply_markup.inline_keyboard[0][0].callback_data
    await callback(harness, data)
    await callback(harness, data)
    calendar.service.create_event.assert_awaited_once()
    assert "Event yaratildi." in harness.replies


async def test_cancel_prevents_create(harness: Harness) -> None:
    calendar = attach(harness)
    await harness.context.security.lock_state.unlock()
    for text in ["/event_add", "Meeting", "25.09.2026", "15:00", "60", "10"]:
        await harness.send(text)
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    data = prompt.reply_markup.inline_keyboard[0][0].callback_data
    await harness.send("/cancel")
    await callback(harness, data)
    calendar.service.create_event.assert_not_called()


@pytest.mark.parametrize("command", ["/today", "/tomorrow", "/upcoming"])
async def test_empty_schedule(harness: Harness, command: str) -> None:
    attach(harness)
    await harness.context.security.lock_state.unlock()
    await harness.send(command)
    assert "reja yo'q" in harness.replies[-1]


async def test_delete_selection_and_confirmation(harness: Harness) -> None:
    from app.modules.calendar.schemas import CalendarEventView

    calendar = attach(harness)
    await harness.context.security.lock_state.unlock()
    event = CalendarEventView(
        id="abc123",
        etag="v1",
        title="Meeting",
        start=datetime(2026, 9, 25, 10, tzinfo=UTC),
        end=datetime(2026, 9, 25, 11, tzinfo=UTC),
    )
    calendar.service.list_upcoming_events.return_value = [event]
    calendar.service.get_event = AsyncMock(return_value=event)
    calendar.service.mutable_event = AsyncMock(return_value=event)
    calendar.service.delete_event = AsyncMock()
    await harness.send("/event_delete")
    await harness.send("1")
    calendar.service.delete_event.assert_not_called()
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    await callback(harness, prompt.reply_markup.inline_keyboard[0][0].callback_data)
    calendar.service.delete_event.assert_awaited_once_with("abc123", "v1")


async def test_update_title_confirmation(harness: Harness) -> None:
    from app.modules.calendar.schemas import CalendarEventView

    calendar = attach(harness)
    await harness.context.security.lock_state.unlock()
    event = CalendarEventView(
        id="abc123",
        etag="v1",
        title="Meeting",
        start=datetime(2026, 9, 25, 10, tzinfo=UTC),
        end=datetime(2026, 9, 25, 11, tzinfo=UTC),
    )
    calendar.service.list_upcoming_events.return_value = [event]
    calendar.service.get_event = AsyncMock(return_value=event)
    calendar.service.mutable_event = AsyncMock(return_value=event)
    calendar.service.update_event = AsyncMock()
    for text in ["/event_update", "1", "title", "Updated meeting"]:
        await harness.send(text)
    calendar.service.update_event.assert_not_called()
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    await callback(harness, prompt.reply_markup.inline_keyboard[0][0].callback_data)
    calendar.service.update_event.assert_awaited_once()
    assert calendar.service.update_event.call_args.args[1].fields == {"title"}


async def test_disconnect_confirmation(harness: Harness) -> None:
    calendar = attach(harness)
    calendar.oauth.disconnect = AsyncMock(return_value=True)
    await harness.context.security.lock_state.unlock()
    await harness.send("/google_disconnect")
    calendar.oauth.disconnect.assert_not_called()
    prompt = [call for call in harness.api.calls if isinstance(call, SendMessage)][-1]
    await callback(harness, prompt.reply_markup.inline_keyboard[0][0].callback_data)
    calendar.oauth.disconnect.assert_awaited_once()


async def test_free_syntax_and_result(harness: Harness) -> None:
    from app.modules.calendar.schemas import FreeBusyResult, TimeInterval

    calendar = attach(harness)
    await harness.context.security.lock_state.unlock()
    await harness.send("/free invalid")
    assert "Format:" in harness.replies[-1]
    calendar.service.get_free_busy = AsyncMock(
        return_value=FreeBusyResult(
            busy=[],
            free=[TimeInterval(start="2026-09-25T14:00:00+05:00", end="2026-09-25T20:00:00+05:00")],
        )
    )
    await harness.send("/free 25.09.2026 14:00 20:00")
    assert "14:00-20:00" in harness.replies[-1]
