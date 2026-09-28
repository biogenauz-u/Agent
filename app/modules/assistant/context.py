from collections import defaultdict, deque
from datetime import UTC, datetime


class AssistantContextStore:
    """Bounded, expiring minimal context; sensitive FSM input never calls this service."""

    def __init__(self, ttl: int, maximum: int, *, clock=lambda: datetime.now(UTC).timestamp()) -> None:
        self.ttl, self.maximum, self.clock = ttl, maximum, clock
        self.items: dict[int, deque[tuple[float, dict[str, str]]]] = defaultdict(deque)

    async def add(self, owner: int, role: str, text: str, action: str = "") -> None:
        safe = text[:500]
        queue = self.items[owner]
        queue.append((self.clock() + self.ttl, {"role": role, "text": safe, "action": action}))
        while len(queue) > self.maximum:
            queue.popleft()

    async def recent(self, owner: int) -> list[dict[str, str]]:
        queue = self.items[owner]
        now = self.clock()
        while queue and queue[0][0] <= now:
            queue.popleft()
        return [item for _, item in queue]
