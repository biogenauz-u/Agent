from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.database.models import EmailMessage, User


async def test_email_model_and_unique_gmail_id(session) -> None:
    user = User(telegram_user_id=777)
    session.add(user)
    await session.flush()
    values = {"user_id": user.id, "gmail_message_id": "unique", "gmail_thread_id": "thread", "from_address": "x@example.com", "subject": "Subject", "snippet": "", "received_at": datetime.now(UTC), "labels": [], "attachments": [], "has_attachments": False, "is_unread": True, "is_important": False}
    session.add(EmailMessage(**values))
    await session.flush()
    session.add(EmailMessage(**values))
    with pytest.raises(IntegrityError):
        await session.flush()
