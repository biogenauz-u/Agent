import asyncio
import importlib
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import pytest
import pytest_asyncio
from argon2 import PasswordHasher
from redis.asyncio import Redis

from app.core.config import Settings
from app.core.exceptions import RedisConfigurationError, SecurityStateUnavailable
from app.modules.security.pin_service import PinService
from app.modules.security.redis_service import RedisSecurityService
from app.modules.security.redis_state import RedisLockService, RedisUnlockGuard
from app.modules.security.service import UnlockResult
from app.redis.health import check_redis_health
from app.redis.keys import SecurityKeys
from app.redis.manager import RedisManager


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[Redis]:
    async with fakeredis.aioredis.FakeRedis(decode_responses=True) as client:
        yield client


def test_import_does_not_construct_redis_client() -> None:
    with patch("redis.asyncio.Redis.from_url") as create:
        importlib.reload(importlib.import_module("app.redis.manager"))
        create.assert_not_called()


def test_manager_explicit_missing_and_invalid_url() -> None:
    with patch("app.redis.manager.Redis.from_url") as create:
        manager = RedisManager(Settings(_env_file=None, REDIS_URL=None))
        create.assert_not_called()
        with pytest.raises(RedisConfigurationError, match="not configured"):
            manager.initialize()
    with pytest.raises(RedisConfigurationError):
        RedisManager(Settings(_env_file=None, REDIS_URL="https://bad.example")).initialize()


async def test_manager_reuses_and_closes() -> None:
    client = AsyncMock()
    with patch("app.redis.manager.Redis.from_url", return_value=client) as create:
        manager = RedisManager(Settings(_env_file=None, REDIS_URL="redis://localhost/0"))
        manager.initialize()
        manager.initialize()
        assert manager.client is client
        create.assert_called_once()
        await manager.close()
        await manager.close()
        client.aclose.assert_awaited_once()


async def test_health(redis_client: Redis) -> None:
    assert await check_redis_health(redis_client)
    with patch.object(redis_client, "ping", side_effect=OSError("test-secret")):
        assert not await check_redis_health(redis_client)


async def test_lock_default_persistence_and_corruption(redis_client: Redis) -> None:
    keys = SecurityKeys("test", 42)
    first = RedisLockService(redis_client, keys)
    assert await first.is_locked()
    await first.unlock()
    assert not await RedisLockService(redis_client, keys).is_locked()
    await first.lock()
    assert await first.is_locked()
    await redis_client.set(keys.key("locked"), "invalid")
    assert await first.is_locked()


async def test_guard_atomic_threshold_ttl_and_clear(redis_client: Redis) -> None:
    keys = SecurityKeys("test", 42)
    guard = RedisUnlockGuard(redis_client, keys, max_attempts=5, lockout_seconds=300)
    assert not await guard.blocked()
    await asyncio.gather(*[guard.record_failure() for _ in range(5)])
    assert await redis_client.get(keys.key("failures")) == "5"
    assert await guard.blocked()
    assert 0 < await guard.remaining() <= 300
    assert 0 < await redis_client.ttl(keys.key("failures")) <= 300
    await guard.clear()
    assert not await guard.blocked()
    assert await redis_client.get(keys.key("failures")) is None


async def test_guard_ttl_expires(redis_client: Redis) -> None:
    guard = RedisUnlockGuard(redis_client, SecurityKeys("test", 42), 1, 1)
    await guard.record_failure()
    await asyncio.sleep(1.05)
    assert not await guard.blocked()
    assert await guard.remaining() == 0


async def test_success_resets_failures(redis_client: Redis) -> None:
    keys = SecurityKeys("test", 42)
    pin = PinService(PasswordHasher().hash("test-pin-only"))
    guard = RedisUnlockGuard(redis_client, keys)
    service = RedisSecurityService(redis_client, keys, pin, guard)
    assert await service.unlock("wrong-test-only") == UnlockResult.FAILED
    assert await service.unlock("test-pin-only") == UnlockResult.SUCCESS
    assert not await service.lock_state.is_locked()
    assert await redis_client.get(keys.key("failures")) is None


async def test_lock_during_verification_cannot_be_undone(redis_client: Redis) -> None:
    keys = SecurityKeys("test", 42)
    pin = AsyncMock(spec=PinService)
    service = RedisSecurityService(redis_client, keys, pin, RedisUnlockGuard(redis_client, keys))

    async def verify(candidate: str) -> bool:
        await service.lock()
        return True

    pin.verify_pin.side_effect = verify
    with pytest.raises(SecurityStateUnavailable):
        await service.unlock("test-pin-only")
    assert await service.lock_state.is_locked()


async def test_expired_lease_cannot_unlock(redis_client: Redis) -> None:
    keys = SecurityKeys("test", 42)
    pin = AsyncMock(spec=PinService)
    service = RedisSecurityService(redis_client, keys, pin, RedisUnlockGuard(redis_client, keys))

    async def verify(candidate: str) -> bool:
        await redis_client.delete(keys.key("verification"))
        return True

    pin.verify_pin.side_effect = verify
    with pytest.raises(SecurityStateUnavailable):
        await service.unlock("test-pin-only")
    assert await service.lock_state.is_locked()


async def test_multiple_instances_share_lockout(redis_client: Redis) -> None:
    keys = SecurityKeys("test", 42)
    pin = AsyncMock(spec=PinService)
    pin.verify_pin.return_value = False
    one = RedisSecurityService(redis_client, keys, pin, RedisUnlockGuard(redis_client, keys, 1))
    two = RedisSecurityService(redis_client, keys, pin, RedisUnlockGuard(redis_client, keys, 1))
    assert await one.unlock("wrong-test-only") == UnlockResult.BLOCKED
    assert await two.unlock("test-pin-only") == UnlockResult.BLOCKED
    assert pin.verify_pin.await_count == 1
