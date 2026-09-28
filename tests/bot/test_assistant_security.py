from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.types import Update

from app.bot.constants import LOCKED

from .conftest import OWNER, Harness


async def test_locked_session_blocks_assistant_text(harness: Harness) -> None:
    router = SimpleNamespace(route=AsyncMock())
    harness.context.assistant = SimpleNamespace(router=router, stt=None)
    await harness.send("Ertaga uchrashuv yarat")
    assert harness.replies[-1] == LOCKED
    router.route.assert_not_awaited()


async def test_locked_session_blocks_voice_before_download(harness: Harness) -> None:
    stt = SimpleNamespace(transcribe_bytes=AsyncMock(), max_bytes=1024)
    harness.context.assistant = SimpleNamespace(
        router=SimpleNamespace(route=AsyncMock()), stt=stt
    )
    payload = {
        "update_id": 500,
        "message": {
            "message_id": 500,
            "date": datetime.now(UTC),
            "chat": {"id": OWNER, "type": "private"},
            "from": {"id": OWNER, "is_bot": False, "first_name": "Owner"},
            "voice": {
                "file_id": "voice-id",
                "file_unique_id": "voice-unique",
                "duration": 1,
                "file_size": 10,
            },
        },
    }
    update = Update.model_validate(payload, context={"bot": harness.bot})
    await harness.dispatcher.feed_update(harness.bot, update)
    assert harness.replies[-1] == LOCKED
    stt.transcribe_bytes.assert_not_awaited()
