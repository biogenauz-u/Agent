from collections.abc import Callable
from time import monotonic
from typing import Protocol


class AttemptGuard(Protocol):
    async def blocked(self) -> bool: ...
    async def record_failure(self) -> None: ...
    async def clear(self) -> None: ...
    async def remaining(self) -> int: ...


class UnlockGuard:
    """In-memory failed-attempt policy; one instance per owner and process."""

    def __init__(
        self,
        max_attempts: int = 5,
        lockout_seconds: int = 300,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if max_attempts < 1 or lockout_seconds < 1:
            raise ValueError("Unlock policy values must be positive")
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._clock = clock
        self.failed_attempts = 0
        self._blocked_until = 0.0

    def is_blocked(self) -> bool:
        if self._blocked_until and self._clock() >= self._blocked_until:
            self.reset()
        return self._blocked_until > self._clock()

    def failed(self) -> None:
        self.failed_attempts += 1
        if self.failed_attempts >= self.max_attempts:
            self._blocked_until = self._clock() + self.lockout_seconds

    def reset(self) -> None:
        self.failed_attempts = 0
        self._blocked_until = 0.0

    async def blocked(self) -> bool:
        return self.is_blocked()

    async def record_failure(self) -> None:
        self.failed()

    async def clear(self) -> None:
        self.reset()

    async def remaining(self) -> int:
        from math import ceil

        return max(0, ceil(self._blocked_until - self._clock())) if self.is_blocked() else 0
