import asyncio
import logging

from app.core.logging import report_error
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.users.repository import UserRepository


class CalendarAudit:
    """Independent best-effort transaction AFTER provider success; never retries actions."""

    def __init__(self, database: DatabaseManager | None, owner: int | None) -> None:
        self.database, self.owner = database, owner

    async def record(self, action: AuditAction, event_id: str | None = None) -> None:
        if self.database is None or self.owner is None:
            logging.getLogger(__name__).warning("calendar_audit_database_unconfigured")
            return
        try:
            async with asyncio.timeout(5), self.database.session() as session:
                user = await UserRepository(session).get_by_telegram_user_id(self.owner)
                await AuditService(AuditRepository(session)).log_event(
                    action,
                    user_id=user.id if user else None,
                    entity_type="calendar",
                    entity_id=event_id,
                )
        except Exception as error:  # noqa: BLE001 - isolated best-effort audit boundary
            # External action already succeeded; audit errors must not imply retry is safe.
            report_error(logging.getLogger(__name__), error)
