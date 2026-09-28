from app.database.models import User
from app.modules.users.repository import UserRepository


class UserService:
    """Synchronize an already-authorized owner's profile within the caller transaction."""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def synchronize(
        self,
        telegram_user_id: int,
        *,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> User:
        user = await self.repository.get_by_telegram_user_id(telegram_user_id)
        if user is None:
            user = await self.repository.create(
                telegram_user_id,
                telegram_username=username,
                first_name=first_name,
                last_name=last_name,
            )
        else:
            user.telegram_username = username
            user.first_name = first_name
            user.last_name = last_name
        await self.repository.update_last_seen(user.id)
        return user
