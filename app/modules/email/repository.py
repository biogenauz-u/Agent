from datetime import UTC, datetime

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.email import (
    EmailDraftStatus,
    EmailMessage,
    EmailReplyDraft,
    IntegrationState,
)
from app.modules.email.schemas import EmailContent


class EmailRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_gmail_message_id(self, message_id: str) -> EmailMessage | None:
        return await self.session.scalar(
            select(EmailMessage).where(EmailMessage.gmail_message_id == message_id)
        )

    async def get(self, email_id: int, user_id: int) -> EmailMessage | None:
        return await self.session.scalar(
            select(EmailMessage).where(EmailMessage.id == email_id, EmailMessage.user_id == user_id)
        )

    async def create_or_update(
        self,
        user_id: int,
        content: EmailContent,
        body: bytes | None,
        summary: bytes | None,
        body_hash: str | None,
    ) -> tuple[EmailMessage, bool]:
        row = await self.get_by_gmail_message_id(content.gmail_message_id)
        created = row is None
        if row is None:
            row = EmailMessage(
                user_id=user_id,
                gmail_message_id=content.gmail_message_id,
                gmail_thread_id=content.gmail_thread_id,
                received_at=content.received_at,
            )
            self.session.add(row)
        row.gmail_thread_id = content.gmail_thread_id
        row.history_id = content.history_id
        row.from_address, row.from_name = content.from_address, content.from_name
        row.to_addresses, row.cc_addresses = content.to_addresses, content.cc_addresses
        row.subject, row.snippet = content.subject, content.snippet
        row.received_at, row.labels = content.received_at, content.labels
        row.attachments = [item.model_dump() for item in content.attachments]
        row.has_attachments = bool(content.attachments)
        row.is_unread, row.is_important = content.is_unread, content.is_important
        row.body_text_encrypted, row.summary_encrypted, row.body_hash = body, summary, body_hash
        await self.session.flush()
        return row, created

    async def list_recent(
        self, user_id: int, limit: int, unread_only: bool = False
    ) -> list[EmailMessage]:
        query = select(EmailMessage).where(EmailMessage.user_id == user_id)
        if unread_only:
            query = query.where(EmailMessage.is_unread.is_(True))
        result = await self.session.scalars(
            query.order_by(EmailMessage.received_at.desc()).limit(limit)
        )
        return list(result)

    async def search_local(self, user_id: int, term: str, limit: int) -> list[EmailMessage]:
        escaped = term.replace("%", "\\%").replace("_", "\\_")
        result = await self.session.scalars(
            select(EmailMessage)
            .where(
                EmailMessage.user_id == user_id,
                or_(
                    EmailMessage.subject.ilike(f"%{escaped}%", escape="\\"),
                    EmailMessage.from_address.ilike(f"%{escaped}%", escape="\\"),
                    EmailMessage.snippet.ilike(f"%{escaped}%", escape="\\"),
                ),
            )
            .order_by(EmailMessage.received_at.desc())
            .limit(limit)
        )
        return list(result)

    async def mark_notified(self, row: EmailMessage) -> None:
        row.notified_at = datetime.now(UTC)
        await self.session.flush()


class IntegrationStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: int, provider: str, key: str) -> str | None:
        row = await self.session.scalar(
            select(IntegrationState).where(
                IntegrationState.user_id == user_id,
                IntegrationState.provider == provider,
                IntegrationState.key == key,
            )
        )
        return row.value if row else None

    async def set(self, user_id: int, provider: str, key: str, value: str) -> None:
        row = await self.session.scalar(
            select(IntegrationState).where(
                IntegrationState.user_id == user_id,
                IntegrationState.provider == provider,
                IntegrationState.key == key,
            )
        )
        if row is None:
            row = IntegrationState(user_id=user_id, provider=provider, key=key, value=value)
            self.session.add(row)
        else:
            row.value = value
        await self.session.flush()


class EmailDraftRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        email_id: int,
        recipient: bytes,
        subject: bytes,
        body: bytes,
    ) -> EmailReplyDraft:
        row = EmailReplyDraft(
            user_id=user_id,
            email_id=email_id,
            recipient_encrypted=recipient,
            subject_encrypted=subject,
            body_encrypted=body,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get(self, user_id: int, draft_id: int) -> EmailReplyDraft | None:
        return await self.session.scalar(
            select(EmailReplyDraft).where(
                EmailReplyDraft.user_id == user_id,
                EmailReplyDraft.id == draft_id,
            )
        )

    async def claim(self, user_id: int, draft_id: int) -> EmailReplyDraft | None:
        result = await self.session.execute(
            update(EmailReplyDraft)
            .where(
                EmailReplyDraft.user_id == user_id,
                EmailReplyDraft.id == draft_id,
                EmailReplyDraft.status == EmailDraftStatus.DRAFT,
            )
            .values(status=EmailDraftStatus.SENDING, confirmed_at=datetime.now(UTC))
            .returning(EmailReplyDraft)
        )
        return result.scalar_one_or_none()

    async def mark_sent(self, user_id: int, draft_id: int, gmail_id: str) -> bool:
        result = await self.session.execute(
            update(EmailReplyDraft)
            .where(
                EmailReplyDraft.user_id == user_id,
                EmailReplyDraft.id == draft_id,
                EmailReplyDraft.status == EmailDraftStatus.SENDING,
            )
            .values(
                status=EmailDraftStatus.SENT,
                sent_at=datetime.now(UTC),
                gmail_sent_message_id=gmail_id,
            )
            .returning(EmailReplyDraft.id)
        )
        return result.scalar_one_or_none() is not None

    async def mark_failed(self, user_id: int, draft_id: int, reason: str) -> None:
        await self.session.execute(
            update(EmailReplyDraft)
            .where(
                EmailReplyDraft.user_id == user_id,
                EmailReplyDraft.id == draft_id,
                EmailReplyDraft.status == EmailDraftStatus.SENDING,
            )
            .values(status=EmailDraftStatus.FAILED, failure_reason=reason[:120])
        )

    async def cancel(self, user_id: int, draft_id: int) -> bool:
        result = await self.session.execute(
            update(EmailReplyDraft)
            .where(
                EmailReplyDraft.user_id == user_id,
                EmailReplyDraft.id == draft_id,
                EmailReplyDraft.status == EmailDraftStatus.DRAFT,
            )
            .values(status=EmailDraftStatus.CANCELLED)
            .returning(EmailReplyDraft.id)
        )
        return result.scalar_one_or_none() is not None
