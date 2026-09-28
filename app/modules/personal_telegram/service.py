from collections.abc import Callable
from datetime import date
from typing import Protocol

from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.encryption import CredentialEncryption
from app.database.models.personal_telegram import (
    PersonalTelegramMessage,
    PersonalTelegramReplyDraft,
    TelegramMessageDirection,
)
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.personal_telegram.audit import PersonalTelegramAudit
from app.modules.personal_telegram.client import PersonalTelegramClient
from app.modules.personal_telegram.draft_service import PersonalTelegramDraftTextService
from app.modules.personal_telegram.exceptions import (
    PersonalTelegramAuthenticationError,
    PersonalTelegramDraftError,
    PersonalTelegramNotConnectedError,
    PersonalTelegramPasswordRequired,
)
from app.modules.personal_telegram.repository import (
    PersonalTelegramDraftRepository,
    PersonalTelegramMessageRepository,
)
from app.modules.personal_telegram.schemas import (
    IncomingTelegramMessage,
    LoginResult,
    PersonalTelegramMessageView,
    TelegramReplyDraftView,
)
from app.modules.personal_telegram.session_store import PersonalTelegramSessionStore
from app.modules.personal_telegram.utils import mask_phone, normalize_message, safe_preview
from app.modules.users.repository import UserRepository


class PersonalTelegramNotifier(Protocol):
    async def send(self, message: PersonalTelegramMessageView) -> None: ...


ClientFactory = Callable[[Settings, str], PersonalTelegramClient]


class PersonalTelegramService:
    def __init__(
        self,
        settings: Settings,
        database: DatabaseManager,
        store: PersonalTelegramSessionStore,
        notifier: PersonalTelegramNotifier | None,
        *,
        client_factory: ClientFactory = PersonalTelegramClient,
    ) -> None:
        assert settings.telegram_owner_id is not None and settings.data_encryption_key is not None
        self.settings, self.database, self.store = settings, database, store
        self.owner_id = settings.telegram_owner_id
        self.notifier, self.client_factory = notifier, client_factory
        self.cipher = CredentialEncryption(settings.data_encryption_key)
        self.audit = PersonalTelegramAudit(database, self.owner_id)
        self.draft_text = PersonalTelegramDraftTextService()
        self.client: PersonalTelegramClient | None = None
        self._login_phone: str | None = None

    def _client(self) -> PersonalTelegramClient:
        if self.client is None:
            raise PersonalTelegramNotConnectedError("Personal Telegram is not connected.")
        return self.client

    async def _owner(self, session, *, create: bool = False) -> int | None:
        users = UserRepository(session)
        owner = await users.get_by_telegram_user_id(self.owner_id)
        if owner is None and create:
            owner = await users.create(self.owner_id)
        return owner.id if owner else None

    async def restore(self) -> bool:
        stored = await self.store.load()
        if stored is None:
            return False
        try:
            client = self.client_factory(self.settings, stored.session.get_secret_value())
        except (ValueError, TypeError):
            await self.store.deactivate()
            return False
        await client.connect()
        if not await client.is_authorized():
            await client.disconnect()
            await self.store.deactivate()
            return False
        self.client = client
        return True

    async def connected(self) -> bool:
        return self.client is not None and await self.client.is_authorized()

    async def start_login(self, phone: str) -> str:
        normalized = "+" + "".join(character for character in phone if character.isdigit())
        if len(normalized) < 8 or len(normalized) > 16:
            raise PersonalTelegramAuthenticationError("Telefon raqam formati noto‘g‘ri.")
        if self.client is not None:
            await self.client.disconnect()
        self.client = self.client_factory(self.settings, "")
        await self.client.connect()
        delivery = await self.client.send_code_request(normalized)
        self._login_phone = normalized
        return delivery

    async def resend_code(self) -> str:
        if self._login_phone is None:
            raise PersonalTelegramAuthenticationError("Login jarayoni eskirgan.")
        return await self._client().send_code_request(self._login_phone)

    async def submit_code(self, code: str) -> LoginResult:
        phone = self._login_phone
        if phone is None:
            raise PersonalTelegramAuthenticationError("Login jarayoni eskirgan.")
        try:
            await self._client().sign_in_code(phone, code.strip())
        except PersonalTelegramPasswordRequired:
            return LoginResult(password_required=True)
        await self._complete_login(phone)
        return LoginResult(connected=True)

    async def submit_password(self, password: str) -> LoginResult:
        phone = self._login_phone
        if phone is None:
            raise PersonalTelegramAuthenticationError("Login jarayoni eskirgan.")
        await self._client().sign_in_password(password)
        await self._complete_login(phone)
        return LoginResult(connected=True)

    async def _complete_login(self, phone: str) -> None:
        client = self._client()
        if not await client.is_authorized():
            raise PersonalTelegramAuthenticationError("Telegram authorization failed.")
        account = await client.get_me()
        session_value = SecretStr(client.session_string())
        await self.store.save(session_value, account.id, account.username, mask_phone(phone))
        self._login_phone = None
        await self.audit.record(AuditAction.PERSONAL_TELEGRAM_CONNECTED)

    async def abort_login(self) -> None:
        self._login_phone = None
        if self.client is not None and not await self.client.is_authorized():
            await self.client.disconnect()
            self.client = None

    async def disconnect(self) -> None:
        if self.client is not None:
            await self.client.disconnect()
            self.client = None
        self._login_phone = None
        await self.store.delete()
        await self.audit.record(AuditAction.PERSONAL_TELEGRAM_DISCONNECTED)

    def _message_view(
        self, row: PersonalTelegramMessage, *, include_text: bool = False
    ) -> PersonalTelegramMessageView:
        text = (
            self.cipher.decrypt(row.text_encrypted, self.owner_id, "personal_telegram_message")
            if include_text and row.text_encrypted
            else ""
        )
        return PersonalTelegramMessageView(
            id=row.id,
            peer_id=row.peer_id,
            sender_id=row.sender_id,
            sender_username=row.sender_username,
            sender_display_name=row.sender_display_name,
            telegram_message_id=row.telegram_message_id,
            telegram_chat_id=row.telegram_chat_id,
            direction=row.direction,
            preview=row.message_preview,
            text=text,
            received_at=row.received_at,
            has_media=row.has_media,
            media_type=row.media_type,
        )

    async def ingest(
        self, message: IncomingTelegramMessage, *, notify: bool = True
    ) -> tuple[PersonalTelegramMessageView, bool]:
        if self.settings.personal_telegram_monitor_scope == "private" and not message.is_private:
            raise ValueError("Non-private message is outside configured monitor scope.")
        encrypted = (
            self.cipher.encrypt(message.text, self.owner_id, "personal_telegram_message")
            if message.text
            else None
        )
        try:
            async with self.database.session() as session:
                owner = await self._owner(session, create=True)
                assert owner is not None
                row, created = await PersonalTelegramMessageRepository(session).create(
                    owner, message, encrypted, safe_preview(message.text)
                )
                view = self._message_view(row)
        except IntegrityError:
            async with self.database.session() as session:
                row = await PersonalTelegramMessageRepository(session).get_by_remote_id(
                    message.telegram_chat_id, message.telegram_message_id
                )
                if row is None:
                    raise
                return self._message_view(row), False
        if created:
            await self.audit.record(
                AuditAction.TELEGRAM_PERSONAL_MESSAGE_RECEIVED, message_id=view.id
            )
        if notify and row.notified_at is None and self.notifier is not None:
            await self.notifier.send(view)
            await self._mark_notified(view.id)
        return view, created

    async def _mark_notified(self, message_id: int) -> None:
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = (
                await PersonalTelegramMessageRepository(session).get(owner, message_id)
                if owner
                else None
            )
            if row and row.notified_at is None:
                await PersonalTelegramMessageRepository(session).mark_notified(row)

    async def initial_sync(self, limit: int) -> int:
        rows = await self._client().get_recent_private_messages(limit)
        count = 0
        for raw in rows:
            message = await normalize_message(raw, is_private=True)
            view, created = await self.ingest(message, notify=False)
            await self._mark_notified(view.id)
            count += int(created)
        return count

    async def process_event(self, event) -> None:
        is_private = bool(getattr(event, "is_private", False))
        if self.settings.personal_telegram_monitor_scope == "private" and not is_private:
            return
        raw = getattr(event, "message", event)
        message = await normalize_message(raw, is_private=is_private)
        if message.direction.value != "INCOMING" or message.sender_is_bot:
            return
        await self.ingest(message)

    async def list_recent(self) -> list[PersonalTelegramMessageView]:
        async with self.database.session() as session:
            owner = await self._owner(session)
            rows = (
                await PersonalTelegramMessageRepository(session).list_recent(
                    owner, self.settings.personal_telegram_recent_limit
                )
                if owner
                else []
            )
            return [self._message_view(row) for row in rows]

    async def incoming_count_for_date(self, day: date, timezone) -> int:
        async with self.database.session() as session:
            owner = await self._owner(session)
            rows = (
                await PersonalTelegramMessageRepository(session).list_recent(owner, 10_000)
                if owner
                else []
            )
            return sum(
                row.direction == TelegramMessageDirection.INCOMING
                and row.received_at.astimezone(timezone).date() == day
                for row in rows
            )

    async def read(self, message_id: int) -> PersonalTelegramMessageView | None:
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = (
                await PersonalTelegramMessageRepository(session).get(owner, message_id)
                if owner
                else None
            )
            return self._message_view(row, include_text=True) if row else None

    async def search(self, query: str) -> list[PersonalTelegramMessageView]:
        if not 1 <= len(query) <= 500:
            raise ValueError("Search query must contain 1-500 characters.")
        raw_rows = await self._client().search_messages(
            query, self.settings.personal_telegram_recent_limit
        )
        views: list[PersonalTelegramMessageView] = []
        for raw in raw_rows[: self.settings.personal_telegram_recent_limit]:
            is_private = bool(getattr(raw, "is_private", True))
            if self.settings.personal_telegram_monitor_scope == "private" and not is_private:
                continue
            view, _ = await self.ingest(
                await normalize_message(raw, is_private=is_private), notify=False
            )
            views.append(view)
        return views

    async def create_draft(self, message_id: int, owner_text: str) -> TelegramReplyDraftView:
        text = await self.draft_text.prepare(owner_text)
        encrypted = self.cipher.encrypt(text, self.owner_id, "personal_telegram_draft")
        async with self.database.session() as session:
            owner = await self._owner(session)
            target = (
                await PersonalTelegramMessageRepository(session).get(owner, message_id)
                if owner
                else None
            )
            if target is None:
                raise PersonalTelegramDraftError("Target message was not found.")
            row = await PersonalTelegramDraftRepository(session).create(owner, target, encrypted)
            view = self._draft_view(row)
        await self.audit.record(AuditAction.TELEGRAM_REPLY_DRAFT_CREATED, draft_id=view.id)
        return view

    def _draft_view(self, row: PersonalTelegramReplyDraft) -> TelegramReplyDraftView:
        return TelegramReplyDraftView(
            id=row.id,
            target_message_id=row.target_message_id,
            target_chat_id=row.target_chat_id,
            reply_to_message_id=row.reply_to_message_id,
            text=self.cipher.decrypt(
                row.draft_text_encrypted, self.owner_id, "personal_telegram_draft"
            ),
            status=row.status,
        )

    async def get_draft(self, draft_id: int) -> TelegramReplyDraftView | None:
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = (
                await PersonalTelegramDraftRepository(session).get(owner, draft_id)
                if owner
                else None
            )
            return self._draft_view(row) if row else None

    async def confirm_and_send(self, draft_id: int) -> int:
        client = self._client()
        if not await client.is_authorized():
            raise PersonalTelegramNotConnectedError("Personal Telegram is not authorized.")
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = (
                await PersonalTelegramDraftRepository(session).claim(owner, draft_id)
                if owner
                else None
            )
            if row is None:
                raise PersonalTelegramDraftError("Draft is no longer sendable.")
            view = self._draft_view(row)
        try:
            remote_id = await client.send_message(
                view.target_chat_id, view.text, view.reply_to_message_id
            )
        except Exception as error:
            async with self.database.session() as session:
                owner = await self._owner(session)
                if owner:
                    await PersonalTelegramDraftRepository(session).mark_failed(
                        owner, draft_id, type(error).__name__
                    )
            await self.audit.record(AuditAction.TELEGRAM_PERSONAL_SEND_FAILED, draft_id=draft_id)
            raise
        async with self.database.session() as session:
            owner = await self._owner(session)
            if not owner or not await PersonalTelegramDraftRepository(session).mark_sent(
                owner, draft_id
            ):
                raise PersonalTelegramDraftError(
                    "Message may have been sent, but local confirmation could not be finalized."
                )
        await self.audit.record(AuditAction.TELEGRAM_PERSONAL_MESSAGE_SENT, draft_id=draft_id)
        return remote_id

    async def cancel_draft(self, draft_id: int) -> bool:
        async with self.database.session() as session:
            owner = await self._owner(session)
            return bool(
                owner and await PersonalTelegramDraftRepository(session).cancel(owner, draft_id)
            )
