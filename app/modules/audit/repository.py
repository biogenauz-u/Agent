from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AuditLog


class AuditRepository:
    """Low-level persistence; callers must validate payloads through AuditService."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, event: AuditLog) -> AuditLog:
        self.session.add(event)
        await self.session.flush()
        return event
