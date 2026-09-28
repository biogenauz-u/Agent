from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


class UserRepository:
    """Persist users in an injected session without committing transactions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_telegram_user_id(self, telegram_user_id: int) -> User | None:
        return await self.session.scalar(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )

    async def create(
        self,
        telegram_user_id: int,
        *,
        telegram_username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        if telegram_user_id <= 0:
            raise ValueError("Telegram user ID must be positive")
        user = User(
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            first_name=first_name,
            last_name=last_name,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_last_seen(self, user_id: int, at: datetime | None = None) -> bool:
        timestamp = at if at is not None else datetime.now(UTC)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Timezone-aware datetime required")
        result = await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_seen_at=timestamp.astimezone(UTC))
            .returning(User.id)
        )
        await self.session.flush()
        return result.scalar_one_or_none() is not None
