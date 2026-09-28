from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from telethon.errors import (
    ChatWriteForbiddenError,
    FloodWaitError,
    PhoneNumberFloodError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)

from app.core.config import Settings
from app.modules.personal_telegram.client import PersonalTelegramClient
from app.modules.personal_telegram.exceptions import (
    PersonalTelegramAuthenticationError,
    PersonalTelegramFloodWaitError,
    PersonalTelegramPasswordRequired,
    PersonalTelegramWriteForbiddenError,
)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        TELEGRAM_API_ID=12345,
        TELEGRAM_API_HASH="api-hash-secret",
    )


def connected_client(raw) -> PersonalTelegramClient:
    client = PersonalTelegramClient(settings())
    client._client = raw
    return client


async def test_code_request_keeps_hash_only_in_memory_and_normalizes_code() -> None:
    raw = SimpleNamespace(
        send_code_request=AsyncMock(
            return_value=SimpleNamespace(
                phone_code_hash="opaque-hash",
                type=SimpleNamespace(),
            )
        ),
        sign_in=AsyncMock(),
    )
    client = connected_client(raw)
    assert await client.send_code_request("+998901234567") == "telegram_app"
    await client.sign_in_code("+998901234567", "12 3-45")
    raw.sign_in.assert_awaited_once_with(
        phone="+998901234567", code="12345", phone_code_hash="opaque-hash"
    )
    assert client._phone_code_hash is None


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (PhoneNumberInvalidError(None), "Xalqaro format"),
        (PhoneNumberFloodError(None), "juda ko‘p"),
    ],
)
async def test_code_request_maps_phone_errors_safely(error, message: str) -> None:
    raw = SimpleNamespace(send_code_request=AsyncMock(side_effect=error))
    client = connected_client(raw)
    with pytest.raises(PersonalTelegramAuthenticationError, match=message):
        await client.send_code_request("+998901234567")


async def test_send_passes_reply_target_exactly() -> None:
    raw = SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(id=81)))
    client = connected_client(raw)
    assert await client.send_message(-10022, "hello", 77) == 81
    raw.send_message.assert_awaited_once_with(-10022, "hello", reply_to=77)


async def test_flood_wait_is_mapped_without_long_sleep() -> None:
    raw = SimpleNamespace(send_message=AsyncMock(side_effect=FloodWaitError(None, 123)))
    client = connected_client(raw)
    with pytest.raises(PersonalTelegramFloodWaitError) as captured:
        await client.send_message(1, "hello", 2)
    assert captured.value.seconds == 123


async def test_write_forbidden_is_safe() -> None:
    raw = SimpleNamespace(send_message=AsyncMock(side_effect=ChatWriteForbiddenError(None)))
    client = connected_client(raw)
    with pytest.raises(PersonalTelegramWriteForbiddenError) as captured:
        await client.send_message(1, "hello", 2)
    assert "RPC" not in str(captured.value)


async def test_two_factor_requirement_is_mapped_safely() -> None:
    raw = SimpleNamespace(sign_in=AsyncMock(side_effect=SessionPasswordNeededError(None)))
    client = connected_client(raw)
    client._phone_code_hash = "opaque-hash"
    with pytest.raises(PersonalTelegramPasswordRequired):
        await client.sign_in_code("+998901234567", "12345")


async def test_registers_incoming_only_and_removes_same_adapter() -> None:
    raw = SimpleNamespace(add_event_handler=Mock(), remove_event_handler=Mock())
    client = connected_client(raw)

    async def handler(event) -> None:
        return None

    client.register_incoming_handler(handler)
    adapter = client._adapter
    assert adapter is not None
    raw.add_event_handler.assert_called_once()
    client.remove_incoming_handler()
    raw.remove_event_handler.assert_called_once_with(adapter)
