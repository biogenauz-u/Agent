"""Single-use opaque capabilities, with native Redis expiration when selected."""

import hashlib
import json
import secrets
import time
from typing import Any, Protocol

from redis.asyncio import Redis


class TemporaryStore(Protocol):
    async def issue(self, purpose: str, data: dict[str, Any], ttl: int = 600) -> str: ...
    async def consume(self, purpose: str, token: str) -> dict[str, Any] | None: ...


class MemoryTemporaryStore:
    """Explicit single-process development store. Restart invalidates all actions."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}

    async def issue(self, purpose: str, data: dict[str, Any], ttl: int = 600) -> str:
        now = time.monotonic()
        self._items = {key: value for key, value in self._items.items() if value[0] > now}
        token = secrets.token_urlsafe(24)
        self._items[purpose, token] = (now + ttl, data)
        return token

    async def consume(self, purpose: str, token: str) -> dict[str, Any] | None:
        item = self._items.pop((purpose, token), None)
        return item[1] if item and item[0] > time.monotonic() else None


class RedisTemporaryStore:
    def __init__(self, client: Redis, prefix: str, owner: int) -> None:
        self.client = client
        self.prefix = f"{prefix}:calendar:{{{owner}}}"

    def key(self, purpose: str, token: str) -> str:
        return f"{self.prefix}:{purpose}:{hashlib.sha256(token.encode()).hexdigest()}"

    async def issue(self, purpose: str, data: dict[str, Any], ttl: int = 600) -> str:
        token = secrets.token_urlsafe(24)
        await self.client.set(self.key(purpose, token), json.dumps(data), ex=ttl, nx=True)
        return token

    async def consume(self, purpose: str, token: str) -> dict[str, Any] | None:
        raw = await self.client.getdel(self.key(purpose, token))
        return json.loads(raw) if raw else None
