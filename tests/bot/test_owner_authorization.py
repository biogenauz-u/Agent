from datetime import UTC, datetime

from aiogram.methods import AnswerCallbackQuery
from aiogram.types import Update

from app.bot.constants import DENIED, LOCKED
from app.modules.audit.actions import AuditAction

from .conftest import Harness


async def test_owner_id_allowed(harness: Harness) -> None:
    await harness.send("/id")
    assert harness.replies[-1] == "Telegram User ID: 42"


async def test_unauthorized_never_reaches_handler(harness: Harness) -> None:
    await harness.send("/start", 99)
    assert harness.replies == [DENIED]
    harness.sync.assert_not_awaited()
    harness.audit.assert_awaited_once_with(AuditAction.UNAUTHORIZED_ACCESS, 99)


async def test_unauthorized_id(harness: Harness) -> None:
    await harness.send("/id", 99)
    assert harness.replies == [DENIED]


async def test_missing_sender(harness: Harness) -> None:
    await harness.send("/start", None)
    assert harness.replies == [DENIED]
    harness.sync.assert_not_awaited()


async def test_group_owner_rejected(harness: Harness) -> None:
    await harness.send("/id", 42, chat_type="group")
    assert harness.replies == [DENIED]


async def test_callback_authorization_and_lock(harness: Harness) -> None:
    for user_id, expected in [(99, DENIED), (42, LOCKED)]:
        update = Update.model_validate(
            {
                "update_id": user_id,
                "callback_query": {
                    "id": "test-callback",
                    "chat_instance": "test-chat",
                    "data": "calendar",
                    "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
                    "message": {
                        "message_id": 1,
                        "date": datetime.now(UTC),
                        "chat": {"id": user_id, "type": "private"},
                    },
                },
            },
            context={"bot": harness.bot},
        )
        await harness.dispatcher.feed_update(harness.bot, update)
        calls = [c for c in harness.api.calls if isinstance(c, AnswerCallbackQuery)]
        assert calls[-1].text == expected


async def test_unsupported_update_rejected(harness: Harness) -> None:
    await harness.dispatcher.feed_update(harness.bot, Update(update_id=555))
    harness.sync.assert_not_awaited()
    assert not harness.replies
    harness.audit.assert_awaited_once_with(AuditAction.UNAUTHORIZED_ACCESS, None)
