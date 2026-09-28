import asyncio

from app.modules.security.lock_service import LockService
from app.modules.security.pin_service import PinService
from app.modules.security.service import SecurityService, UnlockResult
from app.modules.security.unlock_guard import UnlockGuard


async def test_lock_default_and_reset() -> None:
    lock = LockService()
    assert await lock.is_locked()
    await lock.unlock()
    assert not await lock.is_locked()
    await lock.lock()
    assert await lock.is_locked()
    assert await LockService().is_locked()


def test_guard_expiration() -> None:
    clock = [0.0]
    guard = UnlockGuard(max_attempts=2, lockout_seconds=300, clock=lambda: clock[0])
    guard.failed()
    assert not guard.is_blocked()
    guard.failed()
    assert guard.is_blocked()
    clock[0] = 301
    assert not guard.is_blocked()
    assert guard.failed_attempts == 0


async def test_parallel_attempts_cannot_bypass_limit(pin_hash: str) -> None:
    guard = UnlockGuard(max_attempts=2)
    service = SecurityService(LockService(), PinService(pin_hash), guard)
    results = await asyncio.gather(*[service.unlock("wrong-test-only") for _ in range(4)])
    assert results.count(UnlockResult.BLOCKED) == 3
    assert guard.failed_attempts == 2
    assert await service.lock_state.is_locked()
