import hashlib
from datetime import date
from typing import Protocol

from app.core.encryption import CredentialEncryption
from app.database.models.email import EmailMessage
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.email.audit import EmailAudit
from app.modules.email.client import GmailClient
from app.modules.email.exceptions import GmailMessageNotFoundError
from app.modules.email.parser import parse_gmail_message
from app.modules.email.repository import EmailRepository, IntegrationStateRepository
from app.modules.email.schemas import EmailContent, EmailView
from app.modules.email.summarizer import EmailSummarizer
from app.modules.users.repository import UserRepository


class EmailNotifier(Protocol):
    async def send(self, email: EmailView) -> None: ...


class EmailService:
    def __init__(self, database: DatabaseManager, owner_id: int, key, client: GmailClient, summarizer: EmailSummarizer, notifier: EmailNotifier | None, *, recent_limit: int = 10, notify_mode: str = "all") -> None:
        self.database, self.owner_id, self.client = database, owner_id, client
        self.cipher = CredentialEncryption(key)
        self.summarizer, self.notifier = summarizer, notifier
        self.recent_limit, self.notify_mode = recent_limit, notify_mode
        self.audit = EmailAudit(database, owner_id)

    async def _owner(self, session) -> int:
        users = UserRepository(session)
        user = await users.get_by_telegram_user_id(self.owner_id)
        if user is None:
            user = await users.create(self.owner_id)
        return user.id

    def _decrypt(self, value: bytes | None, purpose: str) -> str:
        return self.cipher.decrypt(value, self.owner_id, purpose) if value else ""

    def _view(self, row: EmailMessage, *, include_body: bool = False) -> EmailView:
        return EmailView(id=row.id, gmail_message_id=row.gmail_message_id, from_address=row.from_address, from_name=row.from_name, subject=row.subject, snippet=row.snippet, received_at=row.received_at, is_unread=row.is_unread, is_important=row.is_important, has_attachments=row.has_attachments, attachment_count=len(row.attachments or []), summary=self._decrypt(row.summary_encrypted, "gmail_summary"), body_text=self._decrypt(row.body_text_encrypted, "gmail_body") if include_body else "")

    async def _persist(self, content: EmailContent) -> tuple[EmailView, bool, bool]:
        summary = await self.summarizer.summarize(content)
        body = self.cipher.encrypt(content.body_text, self.owner_id, "gmail_body") if content.body_text else None
        encrypted_summary = self.cipher.encrypt(summary, self.owner_id, "gmail_summary") if summary else None
        digest = hashlib.sha256(content.body_text.encode()).hexdigest() if content.body_text else None
        async with self.database.session() as session:
            owner = await self._owner(session)
            row, created = await EmailRepository(session).create_or_update(owner, content, body, encrypted_summary, digest)
            notify_pending = row.notified_at is None
            return self._view(row), created, notify_pending

    async def initial_sync(self, limit: int) -> int:
        listing = await self.client.list_messages(limit=limit)
        last_history = "0"
        for item in listing.get("messages", []):
            content = parse_gmail_message(await self.client.get_message(str(item["id"])))
            view, _, _ = await self._persist(content)
            # Baseline rows are acknowledged without alerts so a restart cannot flood Telegram.
            async with self.database.session() as session:
                owner = await self._owner(session)
                row = await EmailRepository(session).get(view.id, owner)
                if row and row.notified_at is None:
                    await EmailRepository(session).mark_notified(row)
            if content.history_id and int(content.history_id) > int(last_history):
                last_history = content.history_id
        profile = await self.client.get_profile()
        checkpoint = str(profile.get("historyId") or last_history)
        async with self.database.session() as session:
            owner = await self._owner(session)
            await IntegrationStateRepository(session).set(owner, "gmail", "history_id", checkpoint)
        return len(listing.get("messages", []))

    async def checkpoint(self) -> str | None:
        async with self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            return await IntegrationStateRepository(session).get(user.id, "gmail", "history_id") if user else None

    def _should_notify(self, content: EmailContent) -> bool:
        return self.notify_mode == "all" or (self.notify_mode == "important" and content.is_important) or (self.notify_mode == "unread" and content.is_unread)

    async def sync_new(self) -> int:
        checkpoint = await self.checkpoint()
        if checkpoint is None:
            return 0
        try:
            history = await self.client.list_history(checkpoint)
        except GmailMessageNotFoundError:
            # Gmail history checkpoints expire; establish a fresh silent baseline.
            await self.initial_sync(self.recent_limit)
            return 0
        ids: list[str] = []
        for entry in history.get("history", []):
            ids.extend(str(added["message"]["id"]) for added in entry.get("messagesAdded", []) if "message" in added)
        delivered = 0
        for message_id in dict.fromkeys(ids):
            content = parse_gmail_message(await self.client.get_message(message_id))
            view, created, pending = await self._persist(content)
            if created:
                await self.audit.record(AuditAction.EMAIL_RECEIVED, view.id)
            if pending and self.notifier and self._should_notify(content):
                await self.notifier.send(view)
                async with self.database.session() as session:
                    owner = await self._owner(session)
                    row = await EmailRepository(session).get(view.id, owner)
                    if row:
                        await EmailRepository(session).mark_notified(row)
                delivered += 1
        new_checkpoint = str(history.get("historyId") or checkpoint)
        async with self.database.session() as session:
            owner = await self._owner(session)
            await IntegrationStateRepository(session).set(owner, "gmail", "history_id", new_checkpoint)
        return delivered

    async def list_recent(self, unread_only: bool = False) -> list[EmailView]:
        async with self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            rows = await EmailRepository(session).list_recent(user.id, self.recent_limit, unread_only) if user else []
            return [self._view(row) for row in rows]

    async def daily_counts(self, day: date, timezone) -> tuple[int, int]:
        async with self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            if user is None:
                return 0, 0
            recent = await EmailRepository(session).list_recent(user.id, 10_000)
            unread = await EmailRepository(session).list_recent(user.id, 10_000, True)
            return (
                sum(item.received_at.astimezone(timezone).date() == day for item in recent),
                len(unread),
            )

    async def read(self, email_id: int) -> EmailView | None:
        async with self.database.session() as session:
            user = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            row = await EmailRepository(session).get(email_id, user.id) if user else None
            view = self._view(row, include_body=True) if row else None
        if view:
            await self.audit.record(AuditAction.EMAIL_VIEWED, email_id)
        return view

    async def search(self, query: str) -> list[EmailView]:
        listing = await self.client.search_messages(query[:500], self.recent_limit)
        views = []
        for item in listing.get("messages", []):
            view, _, _ = await self._persist(parse_gmail_message(await self.client.get_message(str(item["id"]))))
            views.append(view)
        await self.audit.record(AuditAction.EMAIL_SEARCHED)
        return views
