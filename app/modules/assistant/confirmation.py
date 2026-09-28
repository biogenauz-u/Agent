import asyncio
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from app.modules.assistant.actions import AssistantActionType as A
from app.modules.assistant.exceptions import AssistantConfirmationError
from app.modules.assistant.schemas import ACTION_ADAPTER, AssistantAction

CONFIRM_REQUIRED = frozenset(
    {
        A.CREATE_CALENDAR_EVENT,
        A.UPDATE_CALENDAR_EVENT,
        A.DELETE_CALENDAR_EVENT,
        A.CREATE_REMINDER,
        A.CANCEL_REMINDER,
        A.CREATE_EXPENSE,
        A.CREATE_INCOME,
        A.CREATE_TASK,
        A.UPDATE_TASK,
        A.COMPLETE_TASK,
        A.CREATE_NOTE,
        A.CREATE_EMAIL_REPLY_DRAFT,
        A.CREATE_TELEGRAM_REPLY_DRAFT,
    }
)


class ActionConfirmationPolicy:
    def requires_confirmation(self, action: AssistantAction) -> bool:
        return action.action in CONFIRM_REQUIRED


class PendingActionStore(Protocol):
    async def put(self, owner: int, action: AssistantAction) -> str: ...
    async def consume(self, owner: int, action_id: str) -> AssistantAction: ...


@dataclass
class _Pending:
    owner: int
    payload: str
    expires: float


class MemoryPendingActionStore:
    def __init__(self, ttl: int = 900, *, clock=lambda: datetime.now(UTC).timestamp()) -> None:
        self.ttl, self.clock = ttl, clock
        self.items: dict[str, _Pending] = {}
        self.lock = asyncio.Lock()

    async def put(self, owner: int, action: AssistantAction) -> str:
        action_id = secrets.token_urlsafe(18)
        payload = action.model_dump_json()
        async with self.lock:
            self.items[action_id] = _Pending(owner, payload, self.clock() + self.ttl)
        return action_id

    async def consume(self, owner: int, action_id: str) -> AssistantAction:
        async with self.lock:
            item = self.items.get(action_id)
            if item is None or item.owner != owner or item.expires <= self.clock():
                if item is not None and item.expires <= self.clock():
                    self.items.pop(action_id, None)
                raise AssistantConfirmationError("Action expired or already consumed.")
            self.items.pop(action_id)
        return ACTION_ADAPTER.validate_json(item.payload)


class RedisPendingActionStore:
    def __init__(self, redis, prefix: str, ttl: int = 900) -> None:
        self.redis, self.prefix, self.ttl = redis, prefix, ttl

    def key(self, owner: int, action_id: str) -> str:
        return f"{self.prefix}:assistant:pending:{owner}:{action_id}"

    async def put(self, owner: int, action: AssistantAction) -> str:
        action_id = secrets.token_urlsafe(18)
        payload = json.dumps({"owner": owner, "action": action.model_dump(mode="json")})
        await self.redis.set(self.key(owner, action_id), payload, ex=self.ttl)
        return action_id

    async def consume(self, owner: int, action_id: str) -> AssistantAction:
        raw = await self.redis.getdel(self.key(owner, action_id))
        if not raw:
            raise AssistantConfirmationError("Action expired or already consumed.")
        data = json.loads(raw)
        if data.get("owner") != owner:
            raise AssistantConfirmationError("Action owner mismatch.")
        return ACTION_ADAPTER.validate_python(data["action"])
