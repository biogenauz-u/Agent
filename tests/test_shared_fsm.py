import fakeredis.aioredis
from aiogram.fsm.storage.base import DefaultKeyBuilder, StorageKey

from app.bot.storage import SharedRedisStorage


async def test_fsm_survives_storage_shutdown_without_closing_shared_pool() -> None:
    async with fakeredis.aioredis.FakeRedis(decode_responses=True) as client:
        builder = DefaultKeyBuilder(prefix="test:shared_fsm", with_bot_id=True)
        first = SharedRedisStorage(client, key_builder=builder)
        second = SharedRedisStorage(client, key_builder=builder)
        key = StorageKey(bot_id=1, chat_id=42, user_id=42)
        await first.set_state(key, "UnlockFlow:waiting_for_pin")
        await first.close()
        assert await client.ping()
        assert await second.get_state(key) == "UnlockFlow:waiting_for_pin"
        assert await second.get_data(key) == {}
