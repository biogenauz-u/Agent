import asyncio
import logging
from datetime import datetime

from app.core.logging import report_error
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.users.repository import UserRepository


class ReminderAudit:
    """Best-effort audit in an independent transaction, without reminder content."""

    def __init__(self, database: DatabaseManager, owner_id: int) -> None:
        self.database, self.owner_id = database, owner_id

    async def record(
        self, action: AuditAction, reminder_id: int, scheduled_at: datetime | None = None
    ) -> None:
        details: dict[str, object] = {"reminder_id": reminder_id}
        if scheduled_at:
            details["scheduled_at"] = scheduled_at.isoformat()
        try:
            async with asyncio.timeout(5), self.database.session() as session:
                user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
                await AuditService(AuditRepository(session)).log_event(
                    action,
                    user_id=user.id if user else None,
                    entity_type="reminder",
                    entity_id=str(reminder_id),
                    details=details,
                )
        except Exception as error:  # noqa: BLE001 - best-effort boundary after domain action
            report_error(logging.getLogger(__name__), error)
