from dataclasses import dataclass

from pydantic import SecretStr

from app.core.encryption import CredentialEncryption
from app.database.session import DatabaseManager
from app.modules.personal_telegram.repository import PersonalTelegramSessionRepository
from app.modules.users.repository import UserRepository


@dataclass(frozen=True, repr=False)
class StoredPersonalTelegramSession:
    session: SecretStr
    account_id: int
    username: str | None


class PersonalTelegramSessionStore:
    """Encrypt/decrypt StringSession only at the persistence boundary."""

    def __init__(
        self, database: DatabaseManager, owner_id: int, encryption_key: SecretStr
    ) -> None:
        self.database, self.owner_id = database, owner_id
        self.cipher = CredentialEncryption(encryption_key)

    async def _owner(self, session, *, create: bool = False):
        users = UserRepository(session)
        owner = await users.get_by_telegram_user_id(self.owner_id)
        if owner is None and create:
            owner = await users.create(self.owner_id)
        return owner

    async def load(self) -> StoredPersonalTelegramSession | None:
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = (
                await PersonalTelegramSessionRepository(session).load(owner.id) if owner else None
            )
            if row is None:
                return None
            value = self.cipher.decrypt(
                row.encrypted_session, self.owner_id, "personal_telegram_session"
            )
            return StoredPersonalTelegramSession(
                session=SecretStr(value), account_id=row.telegram_account_id, username=row.username
            )

    async def save(
        self,
        value: SecretStr,
        account_id: int,
        username: str | None,
        phone_hint: str | None,
    ) -> None:
        encrypted = self.cipher.encrypt(
            value.get_secret_value(), self.owner_id, "personal_telegram_session"
        )
        async with self.database.session() as session:
            owner = await self._owner(session, create=True)
            assert owner is not None
            await PersonalTelegramSessionRepository(session).save(
                owner.id, encrypted, account_id, username, phone_hint
            )

    async def deactivate(self) -> None:
        async with self.database.session() as session:
            owner = await self._owner(session)
            if owner:
                await PersonalTelegramSessionRepository(session).deactivate(owner.id)

    async def delete(self) -> None:
        async with self.database.session() as session:
            owner = await self._owner(session)
            if owner:
                await PersonalTelegramSessionRepository(session).delete(owner.id)
