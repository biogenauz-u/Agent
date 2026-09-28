from typing import Protocol


class LockStore(Protocol):
    async def read(self) -> bool: ...
    async def write(self, locked: bool) -> None: ...


class MemoryLockStore:
    def __init__(self) -> None:
        self._locked = True

    async def read(self) -> bool:
        return self._locked

    async def write(self, locked: bool) -> None:
        self._locked = locked


class LockService:
    """A single-owner session, locked by default with replaceable storage."""

    def __init__(self, store: LockStore | None = None) -> None:
        self._store = store if store is not None else MemoryLockStore()

    async def is_locked(self) -> bool:
        return await self._store.read()

    async def lock(self) -> None:
        await self._store.write(True)

    async def unlock(self) -> None:
        await self._store.write(False)
