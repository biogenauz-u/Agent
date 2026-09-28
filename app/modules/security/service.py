import asyncio
from enum import StrEnum

from app.modules.security.lock_service import LockService
from app.modules.security.pin_service import PinService
from app.modules.security.unlock_guard import AttemptGuard


class UnlockResult(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"


class SecurityService:
    """Serialize lock transitions and verification, including concurrent callers."""

    def __init__(self, lock: LockService, pin: PinService, guard: AttemptGuard) -> None:
        self.lock_state = lock
        self._pin = pin
        self.guard = guard
        self._mutex = asyncio.Lock()

    async def lock(self) -> None:
        async with self._mutex:
            await self.lock_state.lock()

    async def unlock(self, candidate: str) -> UnlockResult:
        async with self._mutex:
            if await self.guard.blocked():
                return UnlockResult.BLOCKED
            if not await self._pin.verify_pin(candidate):
                await self.guard.record_failure()
                await self.lock_state.lock()
                return UnlockResult.BLOCKED if await self.guard.blocked() else UnlockResult.FAILED
            await self.guard.clear()
            await self.lock_state.unlock()
            return UnlockResult.SUCCESS
