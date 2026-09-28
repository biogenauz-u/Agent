from email.utils import parseaddr

from app.core.encryption import CredentialEncryption
from app.database.models.email import EmailReplyDraft
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.email.audit import EmailAudit
from app.modules.email.client import GmailClient
from app.modules.email.exceptions import GmailMessageNotFoundError, GmailPermissionError
from app.modules.email.repository import EmailDraftRepository, EmailRepository
from app.modules.email.schemas import EmailReplyDraftView
from app.modules.email.utils import clean_draft
from app.modules.users.repository import UserRepository


class ReplyDraftService:
    """Persists encrypted drafts and sends only after an explicit one-time claim."""

    def __init__(self, database: DatabaseManager, owner_id: int, key, client: GmailClient) -> None:
        self.database = database
        self.owner_id = owner_id
        self.client = client
        self.cipher = CredentialEncryption(key)
        self.audit = EmailAudit(database, owner_id)

    async def _owner(self, session) -> int | None:
        user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
        return user.id if user else None

    def _view(self, row: EmailReplyDraft) -> EmailReplyDraftView:
        return EmailReplyDraftView(
            id=row.id,
            email_id=row.email_id,
            recipient=self.cipher.decrypt(
                row.recipient_encrypted, self.owner_id, "gmail_draft_recipient"
            ),
            subject=self.cipher.decrypt(
                row.subject_encrypted, self.owner_id, "gmail_draft_subject"
            ),
            body=self.cipher.decrypt(row.body_encrypted, self.owner_id, "gmail_draft_body"),
            status=row.status,
        )

    async def create(self, email_id: int, owner_idea: str) -> EmailReplyDraftView:
        body = clean_draft(owner_idea)
        if not body:
            raise ValueError("Draft text is empty.")
        async with self.database.session() as session:
            owner = await self._owner(session)
            target = await EmailRepository(session).get(email_id, owner) if owner else None
            if target is None:
                raise GmailMessageNotFoundError("Email was not found.")
            recipient = parseaddr(target.from_address)[1]
            if not recipient or "@" not in recipient or any(c in recipient for c in "\r\n"):
                raise GmailPermissionError("Email sender address is not safe to reply to.")
            subject = target.subject.strip()
            subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
            row = await EmailDraftRepository(session).create(
                owner,
                target.id,
                self.cipher.encrypt(recipient, self.owner_id, "gmail_draft_recipient"),
                self.cipher.encrypt(subject[:998], self.owner_id, "gmail_draft_subject"),
                self.cipher.encrypt(body, self.owner_id, "gmail_draft_body"),
            )
            view = self._view(row)
        await self.audit.record(AuditAction.EMAIL_REPLY_DRAFT_CREATED, email_id)
        await self.audit.record(AuditAction.EMAIL_SEND_REQUESTED, email_id)
        return view

    async def get(self, draft_id: int) -> EmailReplyDraftView | None:
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = await EmailDraftRepository(session).get(owner, draft_id) if owner else None
            return self._view(row) if row else None

    async def cancel(self, draft_id: int) -> bool:
        async with self.database.session() as session:
            owner = await self._owner(session)
            cancelled = bool(owner and await EmailDraftRepository(session).cancel(owner, draft_id))
        if cancelled:
            await self.audit.record(AuditAction.EMAIL_SEND_CANCELLED)
        return cancelled

    async def confirm_and_send(self, draft_id: int) -> str:
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = await EmailDraftRepository(session).claim(owner, draft_id) if owner else None
            if row is None:
                raise GmailPermissionError("Draft is no longer sendable.")
            target = await EmailRepository(session).get(row.email_id, owner)
            if target is None:
                raise GmailMessageNotFoundError("Original email was not found.")
            view = self._view(row)
            thread_id = target.gmail_thread_id
        await self.audit.record(AuditAction.EMAIL_SEND_CONFIRMED, view.email_id)
        try:
            gmail_id = await self.client.send_message(
                view.recipient, view.subject, view.body, thread_id
            )
        except Exception as error:
            async with self.database.session() as session:
                owner = await self._owner(session)
                if owner:
                    await EmailDraftRepository(session).mark_failed(
                        owner, draft_id, type(error).__name__
                    )
            await self.audit.record(AuditAction.EMAIL_SEND_FAILED, view.email_id)
            raise
        async with self.database.session() as session:
            owner = await self._owner(session)
            saved = bool(
                owner and await EmailDraftRepository(session).mark_sent(owner, draft_id, gmail_id)
            )
        if not saved:
            raise GmailPermissionError(
                "Email may have been sent, but local confirmation could not be finalized."
            )
        await self.audit.record(AuditAction.EMAIL_SENT, view.email_id)
        return gmail_id
