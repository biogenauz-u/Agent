from aiogram.fsm.storage.redis import RedisStorage


class SharedRedisStorage(RedisStorage):
    """Borrow the application-owned client; FSM shutdown must not close its pool."""

    async def close(self) -> None:
        pass
