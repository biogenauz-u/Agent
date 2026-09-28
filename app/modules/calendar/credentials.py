import asyncio
from typing import Protocol

from pydantic import SecretStr

from app.core.encryption import CredentialEncryption
from app.database.session import DatabaseManager
from app.modules.calendar.exceptions import CalendarConfigurationError
from app.modules.calendar.repository import GoogleCredentialRepository
from app.modules.users.repository import UserRepository


class CredentialStore(Protocol):
    async def load(self) -> SecretStr | None: ...
    async def save(self, refresh_token: SecretStr) -> None: ...
    async def delete(self) -> None: ...
    async def rotate(self, previous: SecretStr, current: SecretStr) -> bool: ...


class GoogleCredentialStore:
    def __init__(
        self,
        database: DatabaseManager | None,
        owner: int | None,
        key: SecretStr | None,
        provider: str = "google_calendar",
    ) -> None:
        self.database, self.owner, self.key, self.provider = database, owner, key, provider

    def require_configured(self) -> CredentialEncryption:
        if self.database is None or self.owner is None:
            raise CalendarConfigurationError("Calendar requires PostgreSQL and TELEGRAM_OWNER_ID.")
        return CredentialEncryption(self.key)

    async def load(self) -> SecretStr | None:
        cipher = self.require_configured()
        assert self.database is not None and self.owner is not None
        async with asyncio.timeout(10), self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner)
            row = await GoogleCredentialRepository(session).load(user.id, self.provider) if user else None
            return (
                SecretStr(cipher.decrypt(row.refresh_token_encrypted, self.owner, self.provider))
                if row
                else None
            )

    async def save(self, refresh_token: SecretStr) -> None:
        cipher = self.require_configured()
        assert self.database is not None and self.owner is not None
        async with asyncio.timeout(10), self.database.session() as session:
            users = UserRepository(session)
            user = await users.get_by_telegram_user_id(self.owner)
            if user is None:
                user = await users.create(self.owner)
            await GoogleCredentialRepository(session).save(
                user.id,
                cipher.encrypt(refresh_token.get_secret_value(), self.owner, self.provider),
                self.provider,
            )

    async def delete(self) -> None:
        self.require_configured()
        assert self.database is not None and self.owner is not None
        async with asyncio.timeout(10), self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner)
            if user:
                await GoogleCredentialRepository(session).delete(user.id, self.provider)

    async def rotate(self, previous: SecretStr, current: SecretStr) -> bool:
        """Compare-and-swap; delayed refresh must not resurrect a disconnected credential."""
        cipher = self.require_configured()
        assert self.database is not None and self.owner is not None
        async with asyncio.timeout(10), self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner)
            if user is None:
                return False
            repository = GoogleCredentialRepository(session)
            row = await repository.load(user.id, self.provider)
            if (
                row is None
                or cipher.decrypt(row.refresh_token_encrypted, self.owner, self.provider)
                != previous.get_secret_value()
            ):
                return False
            return await repository.replace(
                user.id,
                row.refresh_token_encrypted,
                cipher.encrypt(current.get_secret_value(), self.owner, self.provider),
                self.provider,
            )
