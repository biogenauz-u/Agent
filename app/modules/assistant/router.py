from collections import defaultdict, deque
from datetime import UTC, datetime

from app.modules.assistant.actions import AssistantActionType as A
from app.modules.assistant.audit import AssistantAudit
from app.modules.assistant.confirmation import ActionConfirmationPolicy, PendingActionStore
from app.modules.assistant.context import AssistantContextStore
from app.modules.assistant.exceptions import AssistantRateLimitError
from app.modules.assistant.executor import AssistantActionExecutor
from app.modules.assistant.parser import AssistantParser
from app.modules.assistant.schemas import (
    AssistantClarification,
    AssistantRequest,
    AssistantRouteResult,
)
from app.modules.audit.actions import AuditAction


class MinuteRateLimiter:
    def __init__(self, limit: int, *, clock=lambda: datetime.now(UTC).timestamp()) -> None:
        self.limit, self.clock = limit, clock
        self.items: dict[int, deque[float]] = defaultdict(deque)

    async def check(self, owner: int) -> None:
        now = self.clock()
        queue = self.items[owner]
        while queue and queue[0] <= now - 60:
            queue.popleft()
        if len(queue) >= self.limit:
            raise AssistantRateLimitError("Juda ko'p AI so'rovi. Birozdan keyin urinib ko'ring.")
        queue.append(now)


class AssistantRouter:
    def __init__(
        self,
        owner_id: int,
        timezone,
        parser: AssistantParser,
        executor: AssistantActionExecutor,
        pending: PendingActionStore,
        context: AssistantContextStore,
        audit: AssistantAudit,
        confidence_threshold: float,
        rate_limit: int,
        *,
        now=lambda: datetime.now(UTC),
    ) -> None:
        self.owner_id, self.timezone = owner_id, timezone
        self.parser, self.executor, self.pending = parser, executor, pending
        self.context, self.audit = context, audit
        self.threshold, self.now = confidence_threshold, now
        self.policy = ActionConfirmationPolicy()
        self.rate = MinuteRateLimiter(rate_limit)

    async def route(self, text: str) -> AssistantRouteResult:
        await self.rate.check(self.owner_id)
        await self.audit.record(AuditAction.AI_REQUEST_RECEIVED, {})
        recent = await self.context.recent(self.owner_id)
        parsed = await self.parser.parse(
            AssistantRequest(
                text=text,
                current_datetime=self.now().astimezone(self.timezone),
                timezone=str(self.timezone),
                context=recent,
            )
        )
        if isinstance(parsed, AssistantClarification):
            return AssistantRouteResult(kind="clarification", message=parsed.question)
        await self.audit.record(AuditAction.AI_ACTION_PARSED, {"action_type": parsed.action.value})
        await self.context.add(self.owner_id, "user", text, parsed.action.value)
        if parsed.confidence < self.threshold:
            return AssistantRouteResult(
                kind="clarification", message="So'rov yetarlicha aniq emas. Iltimos, aniqlashtiring."
            )
        if self.policy.requires_confirmation(parsed):
            action_id = await self.pending.put(self.owner_id, parsed)
            await self.audit.record(
                AuditAction.AI_ACTION_CONFIRMATION_REQUESTED,
                {"action_type": parsed.action.value, "action_id": action_id},
            )
            return AssistantRouteResult(
                kind="confirmation",
                message=self.preview(parsed),
                action_id=action_id,
            )
        try:
            execution = await self.executor.execute(parsed)
        except Exception:
            await self.audit.record(
                AuditAction.AI_ACTION_FAILED, {"action_type": parsed.action.value}
            )
            raise
        await self.audit.record(
            AuditAction.AI_ACTION_EXECUTED, {"action_type": parsed.action.value}
        )
        return AssistantRouteResult(kind="executed", message=execution.message, execution=execution)

    async def confirm(self, owner: int, action_id: str) -> AssistantRouteResult:
        action = await self.pending.consume(owner, action_id)
        await self.audit.record(
            AuditAction.AI_ACTION_CONFIRMED,
            {"action_type": action.action.value, "action_id": action_id},
        )
        try:
            execution = await self.executor.execute(action)
        except Exception:
            await self.audit.record(
                AuditAction.AI_ACTION_FAILED, {"action_type": action.action.value}
            )
            raise
        await self.audit.record(
            AuditAction.AI_ACTION_EXECUTED, {"action_type": action.action.value}
        )
        return AssistantRouteResult(kind="executed", message=execution.message, execution=execution)

    async def cancel(self, owner: int, action_id: str) -> None:
        action = await self.pending.consume(owner, action_id)
        await self.audit.record(
            AuditAction.AI_ACTION_CANCELLED,
            {"action_type": action.action.value, "action_id": action_id},
        )

    @staticmethod
    def preview(action) -> str:
        names = {
            A.CREATE_CALENDAR_EVENT: "Yangi Calendar event",
            A.CREATE_REMINDER: "Yangi reminder",
            A.CREATE_EXPENSE: "Xarajat",
            A.CREATE_INCOME: "Daromad",
            A.CREATE_TASK: "Yangi task",
            A.CREATE_NOTE: "Notebook yozuvi",
        }
        title = names.get(action.action, action.action.value)
        fields = action.model_dump(mode="json", exclude={"confidence", "requires_confirmation"})
        fields.pop("action", None)
        lines = [f"{key}: {value}" for key, value in fields.items() if value not in (None, "", [])]
        return f"{title}\n\n" + "\n".join(lines) + "\n\nTasdiqlaysizmi?"
