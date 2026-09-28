"""Shared security state. Atomic Redis scripts store no PIN or hash."""

from redis.asyncio import Redis

from app.modules.security.lock_service import LockService
from app.redis.keys import SecurityKeys

WRITE_LOCK = """
redis.call('SET', KEYS[1], ARGV[1])
redis.call('INCR', KEYS[2])
return 1
"""
FAILURE = """
if redis.call('EXISTS', KEYS[2]) == 1 then return tonumber(ARGV[1]) end
local n = redis.call('INCR', KEYS[1])
if n >= tonumber(ARGV[1]) then
    redis.call('SET', KEYS[2], '1', 'EX', ARGV[2])
    redis.call('EXPIRE', KEYS[1], ARGV[2])
end
return n
"""


class RedisLockStore:
    def __init__(self, client: Redis, keys: SecurityKeys) -> None:
        self.client, self.keys = client, keys

    async def read(self) -> bool:
        # Missing, corrupt or unexpected values can never unlock the session.
        return await self.client.get(self.keys.key("locked")) not in {"0", b"0"}

    async def write(self, locked: bool) -> None:
        await self.client.eval(
            WRITE_LOCK,
            2,
            self.keys.key("locked"),
            self.keys.key("version"),
            "1" if locked else "0",
        )


class RedisLockService(LockService):
    def __init__(self, client: Redis, keys: SecurityKeys) -> None:
        super().__init__(RedisLockStore(client, keys))


class RedisUnlockGuard:
    """Atomic failure increments with native TTL for lockout and counter expiration."""

    def __init__(
        self,
        client: Redis,
        keys: SecurityKeys,
        max_attempts: int = 5,
        lockout_seconds: int = 300,
    ) -> None:
        self.client, self.keys = client, keys
        self.max_attempts, self.lockout_seconds = max_attempts, lockout_seconds

    async def blocked(self) -> bool:
        return bool(await self.client.exists(self.keys.key("lockout")))

    async def record_failure(self) -> None:
        await self.client.eval(
            FAILURE,
            2,
            self.keys.key("failures"),
            self.keys.key("lockout"),
            self.max_attempts,
            self.lockout_seconds,
        )

    async def clear(self) -> None:
        await self.client.delete(self.keys.key("failures"), self.keys.key("lockout"))

    async def remaining(self) -> int:
        return max(0, await self.client.ttl(self.keys.key("lockout")))
