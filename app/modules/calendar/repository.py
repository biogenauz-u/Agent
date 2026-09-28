from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import GoogleCredential


class GoogleCredentialRepository:
    """Caller owns transaction; repository only accepts encrypted bytes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load(self, user_id: int, provider: str = "google_calendar") -> GoogleCredential | None:
        return await self.session.scalar(
            select(GoogleCredential).where(
                GoogleCredential.user_id == user_id,
                GoogleCredential.provider == provider,
            )
        )

    async def save(self, user_id: int, encrypted: bytes, provider: str = "google_calendar") -> None:
        row = await self.load(user_id, provider)
        if row is None:
            row = GoogleCredential(user_id=user_id, provider=provider)
            self.session.add(row)
        row.refresh_token_encrypted = encrypted
        await self.session.flush()

    async def delete(self, user_id: int, provider: str = "google_calendar") -> None:
        await self.session.execute(
            delete(GoogleCredential).where(
                GoogleCredential.user_id == user_id,
                GoogleCredential.provider == provider,
            )
        )

    async def replace(
        self, user_id: int, expected: bytes, encrypted: bytes, provider: str = "google_calendar"
    ) -> bool:
        result = await self.session.execute(
            update(GoogleCredential)
            .where(
                GoogleCredential.user_id == user_id,
                GoogleCredential.provider == provider,
                GoogleCredential.refresh_token_encrypted == expected,
            )
            .values(refresh_token_encrypted=encrypted)
            .returning(GoogleCredential.id)
        )
        return result.scalar_one_or_none() is not None
