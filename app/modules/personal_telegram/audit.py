import logging

from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.users.repository import UserRepository


class PersonalTelegramAudit:
    """Audit internal IDs only; message/session/login content is prohibited."""

    def __init__(self, database: DatabaseManager, owner_id: int) -> None:
        self.database, self.owner_id = database, owner_id

    async def record(
        self,
        action: AuditAction,
        *,
        message_id: int | None = None,
        draft_id: int | None = None,
    ) -> None:
        try:
            async with self.database.session() as session:
                owner = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
                details: dict[str, object] = {}
                if message_id is not None:
                    details["internal_message_id"] = message_id
                if draft_id is not None:
                    details["internal_draft_id"] = draft_id
                await AuditService(AuditRepository(session)).log_event(
                    action,
                    user_id=owner.id if owner else None,
                    entity_type="personal_telegram",
                    entity_id=str(draft_id or message_id) if draft_id or message_id else None,
                    details=details,
                )
        except Exception as error:  # noqa: BLE001 - audit failure cannot repeat external actions
            logging.getLogger(__name__).warning(
                "personal_telegram_audit_failed", extra={"error_type": type(error).__name__}
            )
