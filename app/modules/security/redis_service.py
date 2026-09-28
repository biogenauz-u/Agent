"""Serialize costly verification across processes and fence stale unlock results."""

import logging
from secrets import token_hex

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.exceptions import SecurityStateUnavailable
from app.modules.security.pin_service import PinService
from app.modules.security.redis_state import RedisLockService, RedisUnlockGuard
from app.modules.security.service import SecurityService, UnlockResult
from app.redis.keys import SecurityKeys

logger = logging.getLogger(__name__)
LEASE_SECONDS = 30
RELEASE = """
if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end
return 0
"""
COMPLETE = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return -1 end
if (redis.call('GET', KEYS[2]) or '0') ~= ARGV[2] then return -1 end
if redis.call('EXISTS', KEYS[4]) == 1 then return 2 end
if ARGV[3] == '1' then
    redis.call('DEL', KEYS[3], KEYS[4])
    redis.call('SET', KEYS[5], '0')
    redis.call('INCR', KEYS[2])
    return 0
end
local n = redis.call('INCR', KEYS[3])
redis.call('SET', KEYS[5], '1')
redis.call('INCR', KEYS[2])
if n >= tonumber(ARGV[4]) then
    redis.call('SET', KEYS[4], '1', 'EX', ARGV[5])
    redis.call('EXPIRE', KEYS[3], ARGV[5])
    return 2
end
return 1
"""


class RedisSecurityService(SecurityService):
    def __init__(
        self,
        client: Redis,
        keys: SecurityKeys,
        pin: PinService,
        guard: RedisUnlockGuard,
    ) -> None:
        super().__init__(RedisLockService(client, keys), pin, guard)
        self.client, self.keys = client, keys
        self.redis_guard = guard

    async def unlock(self, candidate: str) -> UnlockResult:
        token = token_hex(16)
        lease = self.keys.key("verification")
        try:
            if not await self.client.set(lease, token, nx=True, ex=LEASE_SECONDS):
                return UnlockResult.BLOCKED
            try:
                version = await self.client.get(self.keys.key("version")) or "0"
                if await self.guard.blocked():
                    return UnlockResult.BLOCKED
                verified = await self._pin.verify_pin(candidate)
                result = await self.client.eval(
                    COMPLETE,
                    5,
                    lease,
                    self.keys.key("version"),
                    self.keys.key("failures"),
                    self.keys.key("lockout"),
                    self.keys.key("locked"),
                    token,
                    version,
                    "1" if verified else "0",
                    self.redis_guard.max_attempts,
                    self.redis_guard.lockout_seconds,
                )
                if result == -1:
                    raise SecurityStateUnavailable("Security state changed; retry unlock.")
                return {0: UnlockResult.SUCCESS, 1: UnlockResult.FAILED, 2: UnlockResult.BLOCKED}[
                    result
                ]
            finally:
                await self.client.eval(RELEASE, 1, lease, token)
        except RedisError:
            logger.warning("security_state_unavailable")
            raise SecurityStateUnavailable("Shared security state is unavailable.") from None
