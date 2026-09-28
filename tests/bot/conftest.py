"""Dispatch real Aiogram updates through an offline API session."""

from collections.abc import AsyncGenerator, AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import DeleteMessage, GetMe, SendMessage, TelegramMethod
from aiogram.types import Chat, Message, Update, User
from argon2 import PasswordHasher, Type

from app.bot.context import BotContext
from app.bot.dispatcher import create_dispatcher
from app.bot.persistence import BotPersistence
from app.core.config import Settings
from app.modules.security.lock_service import LockService
from app.modules.security.pin_service import PinService
from app.modules.security.service import SecurityService
from app.modules.security.unlock_guard import UnlockGuard

TEST_TOKEN = "123456789:TEST_ONLY_FAKE_TOKEN_NOT_FOR_TELEGRAM_abc"
TEST_PIN = "test-pin-only"
OWNER = 42


@pytest.fixture(autouse=True)
def isolate_bot_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    names = {str(field.alias).upper() for field in Settings.model_fields.values()}
    for name in list(os.environ):
        if name.upper() in names:
            monkeypatch.delenv(name)


class OfflineSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        self.fail_delete = False
        self.closed = False

    async def close(self) -> None:
        self.closed = True

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        timeout: int | None = None,
    ) -> Any:
        self.calls.append(method)
        if isinstance(method, GetMe):
            return User(id=123456789, is_bot=True, first_name="Test", username="test_assistant_bot")
        if isinstance(method, DeleteMessage) and self.fail_delete:
            raise TelegramBadRequest(method=method, message="test deletion denied")
        if isinstance(method, SendMessage):
            return Message(
                message_id=999,
                date=datetime.now(UTC),
                chat=Chat(id=int(method.chat_id), type="private"),
                text=method.text,
            )
        return True

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes, None]:
        raise AssertionError("Network streaming is prohibited in tests")
        yield b""  # pragma: no cover


@dataclass
class Harness:
    bot: Bot
    dispatcher: Dispatcher
    context: BotContext
    api: OfflineSession
    audit: AsyncMock
    sync: AsyncMock
    sequence: int = field(default=0)

    async def send(
        self,
        text: str | None,
        user_id: int | None = OWNER,
        *,
        chat_type: str = "private",
    ) -> None:
        self.sequence += 1
        payload = {
            "update_id": self.sequence,
            "message": {
                "message_id": self.sequence,
                "date": datetime.now(UTC),
                "chat": {"id": user_id or OWNER, "type": chat_type},
                "text": text,
            },
        }
        if user_id is not None:
            payload["message"]["from"] = {"id": user_id, "is_bot": False, "first_name": "Test"}
        update = Update.model_validate(payload, context={"bot": self.bot})
        await self.dispatcher.feed_update(self.bot, update)

    @property
    def replies(self) -> list[str]:
        return [call.text for call in self.api.calls if isinstance(call, SendMessage)]


@pytest.fixture(scope="session")
def pin_hash() -> str:
    return PasswordHasher(type=Type.ID).hash(TEST_PIN)


@pytest_asyncio.fixture
async def harness(pin_hash: str) -> AsyncIterator[Harness]:
    api = OfflineSession()
    bot = Bot(TEST_TOKEN, session=api)
    persistence = BotPersistence()
    audit = AsyncMock(return_value=False)
    sync = AsyncMock(return_value=False)
    persistence.audit = audit
    persistence.synchronize = sync
    context = BotContext(
        OWNER,
        "Asia/Tashkent",
        SecurityService(LockService(), PinService(pin_hash), UnlockGuard()),
        persistence,
    )
    dispatcher = create_dispatcher(context)
    try:
        yield Harness(bot, dispatcher, context, api, audit, sync)
    finally:
        await dispatcher.fsm.close()
        await bot.session.close()
