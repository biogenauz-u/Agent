import logging

from app.core.logging import report_error
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.users.repository import UserRepository


class TaskAudit:
    def __init__(self, database: DatabaseManager, owner_id: int) -> None:
        self.database, self.owner_id = database, owner_id

    async def record(
        self, action: AuditAction, task_id: int, details: dict[str, object] | None = None
    ) -> None:
        try:
            async with self.database.session() as session:
                owner = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
                await AuditService(AuditRepository(session)).log_event(
                    action,
                    user_id=owner.id if owner else None,
                    entity_type="task",
                    entity_id=str(task_id),
                    details={"task_id": task_id, **(details or {})},
                )
        except Exception as error:  # noqa: BLE001 - audit failure must not undo task action
            report_error(logging.getLogger(__name__), error)

