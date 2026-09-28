"""Optional persistence; expected connection failures degrade with explicit warnings."""

import asyncio
import logging

from asyncpg import InvalidAuthorizationSpecificationError, PostgresConnectionError
from sqlalchemy.exc import InterfaceError, OperationalError

from app.database.health import check_database_health
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService

logger = logging.getLogger(__name__)
CONNECTION_ERRORS = (
    OperationalError,
    InterfaceError,
    PostgresConnectionError,
    InvalidAuthorizationSpecificationError,
    OSError,
    TimeoutError,
)


class BotPersistence:
    """Uses existing repositories without storing Telegram objects or raw text."""

    def __init__(self, database: DatabaseManager | None = None) -> None:
        self.database = database

    async def audit(
        self,
        action: AuditAction,
        telegram_user_id: int | None = None,
        command: str | None = None,
    ) -> bool:
        if self.database is None:
            logger.warning(
                "audit_not_persisted_database_unconfigured", extra={"action": action.value}
            )
            return False
        details: dict[str, object] = {}
        if telegram_user_id is not None:
            details["telegram_user_id"] = telegram_user_id
        if command is not None:
            details["command"] = command
        try:
            async with asyncio.timeout(5), self.database.session() as session:
                user = (
                    await UserRepository(session).get_by_telegram_user_id(telegram_user_id)
                    if telegram_user_id is not None
                    else None
                )
                await AuditService(AuditRepository(session)).log_event(
                    action,
                    user_id=user.id if user else None,
                    details=details,
                )
            return True
        except CONNECTION_ERRORS:
            logger.warning(
                "audit_not_persisted_database_unavailable", extra={"action": action.value}
            )
            return False

    async def synchronize(
        self,
        telegram_user_id: int,
        *,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> bool:
        if self.database is None:
            logger.warning("user_not_persisted_database_unconfigured")
            return False
        try:
            async with asyncio.timeout(5), self.database.session() as session:
                await UserService(UserRepository(session)).synchronize(
                    telegram_user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                )
            return True
        except CONNECTION_ERRORS:
            logger.warning("user_not_persisted_database_unavailable")
            return False

    async def status(self) -> str:
        if self.database is None:
            return "Not configured"
        return "Connected" if await check_database_health(self.database.engine) else "Unavailable"
