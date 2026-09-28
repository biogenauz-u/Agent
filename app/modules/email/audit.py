from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.users.repository import UserRepository


class EmailAudit:
    def __init__(self, database: DatabaseManager | None, owner_id: int | None) -> None:
        self.database, self.owner_id = database, owner_id

    async def record(self, action: AuditAction, email_id: int | None = None) -> None:
        if self.database is None or self.owner_id is None:
            return
        async with self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            await AuditService(AuditRepository(session)).log_event(
                action,
                user_id=user.id if user else None,
                entity_type="email" if email_id else "gmail",
                entity_id=str(email_id) if email_id else None,
                details={"email_id": email_id} if email_id else {},
            )
