import base64
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.database.models import EmailDraftStatus, EmailMessage, EmailReplyDraft, User
from app.database.session import DatabaseManager
from app.modules.email.drafts import ReplyDraftService
from app.modules.email.exceptions import GmailPermissionError


def manager(engine) -> DatabaseManager:
    database = DatabaseManager(Settings(_env_file=None))
    database._sessions = async_sessionmaker(engine, expire_on_commit=False)
    return database


def key() -> SecretStr:
    return SecretStr(base64.urlsafe_b64encode(b"e" * 32).decode())


async def seeded_service(engine):
    database = manager(engine)
    async with database.session() as session:
        user = User(telegram_user_id=42)
        session.add(user)
        await session.flush()
        email = EmailMessage(
            user_id=user.id,
            gmail_message_id="gmail-1",
            gmail_thread_id="thread-1",
            from_address="Sender <sender@example.com>",
            subject="Question",
            snippet="",
            received_at=datetime.now(UTC),
            labels=[],
            attachments=[],
        )
        session.add(email)
        await session.flush()
        email_id = email.id
    client = AsyncMock()
    client.send_message.return_value = "sent-1"
    return ReplyDraftService(database, 42, key(), client), client, database, email_id


async def test_draft_is_encrypted_and_only_sends_after_confirmation(engine) -> None:
    service, client, database, email_id = await seeded_service(engine)
    draft = await service.create(email_id, "  I will reply tomorrow.  ")
    assert draft.body == "I will reply tomorrow."
    assert draft.recipient == "sender@example.com"
    assert draft.subject == "Re: Question"
    client.send_message.assert_not_awaited()
    async with database.session() as session:
        stored = await session.get(EmailReplyDraft, draft.id)
        assert b"reply tomorrow" not in stored.body_encrypted
        assert b"sender@example.com" not in stored.recipient_encrypted
        assert stored.status == EmailDraftStatus.DRAFT
    assert await service.confirm_and_send(draft.id) == "sent-1"
    client.send_message.assert_awaited_once_with(
        "sender@example.com", "Re: Question", "I will reply tomorrow.", "thread-1"
    )


async def test_confirmation_is_exactly_once(engine) -> None:
    service, client, _, email_id = await seeded_service(engine)
    draft = await service.create(email_id, "Confirmed reply")
    await service.confirm_and_send(draft.id)
    with pytest.raises(GmailPermissionError, match="no longer sendable"):
        await service.confirm_and_send(draft.id)
    client.send_message.assert_awaited_once()


async def test_cancelled_draft_cannot_send(engine) -> None:
    service, client, _, email_id = await seeded_service(engine)
    draft = await service.create(email_id, "Do not send")
    assert await service.cancel(draft.id)
    with pytest.raises(GmailPermissionError, match="no longer sendable"):
        await service.confirm_and_send(draft.id)
    client.send_message.assert_not_awaited()


async def test_failed_send_is_not_retried_automatically(engine) -> None:
    service, client, database, email_id = await seeded_service(engine)
    client.send_message.side_effect = RuntimeError("offline")
    draft = await service.create(email_id, "Sensitive draft")
    with pytest.raises(RuntimeError, match="offline"):
        await service.confirm_and_send(draft.id)
    async with database.session() as session:
        stored = await session.scalar(select(EmailReplyDraft).where(EmailReplyDraft.id == draft.id))
        assert stored.status == EmailDraftStatus.FAILED
        assert "Sensitive draft" not in (stored.failure_reason or "")
    with pytest.raises(GmailPermissionError, match="no longer sendable"):
        await service.confirm_and_send(draft.id)
    client.send_message.assert_awaited_once()
