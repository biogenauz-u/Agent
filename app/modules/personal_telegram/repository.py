from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.personal_telegram import (
    PersonalTelegramMessage,
    PersonalTelegramReplyDraft,
    PersonalTelegramSession,
    TelegramDraftStatus,
)
from app.modules.personal_telegram.schemas import IncomingTelegramMessage


class PersonalTelegramSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load(self, user_id: int) -> PersonalTelegramSession | None:
        return await self.session.scalar(
            select(PersonalTelegramSession).where(
                PersonalTelegramSession.user_id == user_id,
                PersonalTelegramSession.is_active.is_(True),
            )
        )

    async def save(
        self,
        user_id: int,
        encrypted: bytes,
        account_id: int,
        username: str | None,
        phone_hint: str | None,
    ) -> PersonalTelegramSession:
        row = await self.session.scalar(
            select(PersonalTelegramSession).where(PersonalTelegramSession.user_id == user_id)
        )
        if row is None:
            row = PersonalTelegramSession(
                user_id=user_id,
                encrypted_session=encrypted,
                telegram_account_id=account_id,
            )
            self.session.add(row)
        row.encrypted_session = encrypted
        row.telegram_account_id = account_id
        row.username = username
        row.phone_hint = phone_hint
        row.is_active = True
        row.last_connected_at = datetime.now(UTC)
        await self.session.flush()
        return row

    async def deactivate(self, user_id: int) -> None:
        await self.session.execute(
            update(PersonalTelegramSession)
            .where(PersonalTelegramSession.user_id == user_id)
            .values(is_active=False)
        )

    async def delete(self, user_id: int) -> None:
        await self.session.execute(
            delete(PersonalTelegramSession).where(PersonalTelegramSession.user_id == user_id)
        )


class PersonalTelegramMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_remote_id(
        self, chat_id: int, message_id: int
    ) -> PersonalTelegramMessage | None:
        return await self.session.scalar(
            select(PersonalTelegramMessage).where(
                PersonalTelegramMessage.telegram_chat_id == chat_id,
                PersonalTelegramMessage.telegram_message_id == message_id,
            )
        )

    async def get(self, user_id: int, message_id: int) -> PersonalTelegramMessage | None:
        return await self.session.scalar(
            select(PersonalTelegramMessage).where(
                PersonalTelegramMessage.user_id == user_id,
                PersonalTelegramMessage.id == message_id,
            )
        )

    async def create(
        self,
        user_id: int,
        message: IncomingTelegramMessage,
        encrypted_text: bytes | None,
        preview: str,
    ) -> tuple[PersonalTelegramMessage, bool]:
        row = await self.get_by_remote_id(
            message.telegram_chat_id, message.telegram_message_id
        )
        if row is not None:
            return row, False
        row = PersonalTelegramMessage(
            user_id=user_id,
            peer_id=message.peer_id,
            peer_type=message.peer_type,
            sender_id=message.sender_id,
            sender_username=message.sender_username,
            sender_display_name=message.sender_display_name,
            telegram_message_id=message.telegram_message_id,
            telegram_chat_id=message.telegram_chat_id,
            direction=message.direction,
            text_encrypted=encrypted_text,
            message_preview=preview,
            received_at=message.received_at,
            reply_to_message_id=message.reply_to_message_id,
            has_media=message.has_media,
            media_type=message.media_type,
            is_processed=True,
        )
        self.session.add(row)
        await self.session.flush()
        return row, True

    async def list_recent(self, user_id: int, limit: int) -> list[PersonalTelegramMessage]:
        result = await self.session.scalars(
            select(PersonalTelegramMessage)
            .where(PersonalTelegramMessage.user_id == user_id)
            .order_by(PersonalTelegramMessage.received_at.desc())
            .limit(limit)
        )
        return list(result)

    async def mark_notified(self, row: PersonalTelegramMessage) -> None:
        row.notified_at = datetime.now(UTC)
        await self.session.flush()


class PersonalTelegramDraftRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        target: PersonalTelegramMessage,
        encrypted_text: bytes,
    ) -> PersonalTelegramReplyDraft:
        row = PersonalTelegramReplyDraft(
            user_id=user_id,
            target_message_id=target.id,
            target_chat_id=target.telegram_chat_id,
            reply_to_message_id=target.telegram_message_id,
            draft_text_encrypted=encrypted_text,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get(self, user_id: int, draft_id: int) -> PersonalTelegramReplyDraft | None:
        return await self.session.scalar(
            select(PersonalTelegramReplyDraft).where(
                PersonalTelegramReplyDraft.user_id == user_id,
                PersonalTelegramReplyDraft.id == draft_id,
            )
        )

    async def claim(self, user_id: int, draft_id: int) -> PersonalTelegramReplyDraft | None:
        result = await self.session.execute(
            update(PersonalTelegramReplyDraft)
            .where(
                PersonalTelegramReplyDraft.user_id == user_id,
                PersonalTelegramReplyDraft.id == draft_id,
                PersonalTelegramReplyDraft.status == TelegramDraftStatus.DRAFT,
            )
            .values(status=TelegramDraftStatus.SENDING, confirmed_at=datetime.now(UTC))
            .returning(PersonalTelegramReplyDraft)
        )
        return result.scalar_one_or_none()

    async def mark_sent(self, user_id: int, draft_id: int) -> bool:
        result = await self.session.execute(
            update(PersonalTelegramReplyDraft)
            .where(
                PersonalTelegramReplyDraft.user_id == user_id,
                PersonalTelegramReplyDraft.id == draft_id,
                PersonalTelegramReplyDraft.status == TelegramDraftStatus.SENDING,
            )
            .values(status=TelegramDraftStatus.SENT, sent_at=datetime.now(UTC))
            .returning(PersonalTelegramReplyDraft.id)
        )
        return result.scalar_one_or_none() is not None

    async def mark_failed(self, user_id: int, draft_id: int, reason: str) -> None:
        await self.session.execute(
            update(PersonalTelegramReplyDraft)
            .where(
                PersonalTelegramReplyDraft.user_id == user_id,
                PersonalTelegramReplyDraft.id == draft_id,
                PersonalTelegramReplyDraft.status == TelegramDraftStatus.SENDING,
            )
            .values(status=TelegramDraftStatus.FAILED, failure_reason=reason[:120])
        )

    async def cancel(self, user_id: int, draft_id: int) -> bool:
        result = await self.session.execute(
            update(PersonalTelegramReplyDraft)
            .where(
                PersonalTelegramReplyDraft.user_id == user_id,
                PersonalTelegramReplyDraft.id == draft_id,
                PersonalTelegramReplyDraft.status == TelegramDraftStatus.DRAFT,
            )
            .values(status=TelegramDraftStatus.CANCELLED)
            .returning(PersonalTelegramReplyDraft.id)
        )
        return result.scalar_one_or_none() is not None
