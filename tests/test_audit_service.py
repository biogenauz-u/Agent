import math

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuditDetailsError
from app.database.models import AuditLog, User
from app.modules.audit.actions import AuditAction
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService, validated_details
from app.modules.users.repository import UserRepository


async def test_system_event_json_and_rollback(session: AsyncSession) -> None:
    service = AuditService(AuditRepository(session))
    details = {"command": "/start", "result": {"accepted": True}, "count": 1}
    event = await service.log_event(AuditAction.BOT_STARTED, details=details)
    await session.refresh(event)
    assert event.id is not None
    assert event.user_id is None
    assert event.details == details
    assert event.created_at.tzinfo is not None
    assert "accepted" not in repr(event)
    await session.rollback()
    assert await session.scalar(select(AuditLog)) is None


async def test_user_deletion_preserves_audit(session: AsyncSession) -> None:
    user = await UserRepository(session).create(42)
    event = await AuditService(AuditRepository(session)).log_event(
        AuditAction.AUTHORIZED_ACCESS, user_id=user.id, ip_address="127.0.0.1"
    )
    await session.execute(delete(User).where(User.id == user.id))
    await session.refresh(event)
    assert event.user_id is None
    assert event.details == {}


@pytest.mark.parametrize(
    "details",
    [
        {"token": "never-store-me"},
        {"nested": [{"BOT_PIN": "never-store-me"}]},
        {"value": object()},
        {"value": math.nan},
        {1: "bad-key"},
        {"payload": "x" * 17000},
    ],
)
def test_unsafe_details_rejected(details: dict[str, object]) -> None:
    with pytest.raises(AuditDetailsError) as caught:
        validated_details(details)
    assert "never-store-me" not in str(caught.value)


def test_circular_details_rejected() -> None:
    details: dict[str, object] = {}
    details["nested"] = details
    with pytest.raises(AuditDetailsError):
        validated_details(details)


def test_actions() -> None:
    assert {action.value for action in AuditAction} == {
        "GOOGLE_CALENDAR_CONNECTED",
        "GOOGLE_CALENDAR_DISCONNECTED",
        "CALENDAR_EVENT_CREATED",
        "CALENDAR_EVENT_UPDATED",
        "CALENDAR_EVENT_DELETED",
        "REMINDER_CREATED",
        "REMINDER_CANCELLED",
        "REMINDER_RESCHEDULED",
        "REMINDER_DELIVERED",
        "REMINDER_FAILED",
        "REMINDER_RETRY",
        "BOT_STARTED",
        "BOT_STOPPED",
        "AUTHORIZED_ACCESS",
        "UNAUTHORIZED_ACCESS",
        "COMMAND_RECEIVED",
        "LOGIN_SUCCESS",
        "LOGIN_FAILED",
        "SESSION_LOCKED",
        "SESSION_UNLOCKED",
        "GMAIL_CONNECTED",
        "GMAIL_DISCONNECTED",
        "EMAIL_RECEIVED",
        "EMAIL_VIEWED",
        "EMAIL_SEARCHED",
        "EMAIL_REPLY_DRAFT_CREATED",
        "EMAIL_SEND_REQUESTED",
        "EMAIL_SEND_CONFIRMED",
        "EMAIL_SENT",
        "EMAIL_SEND_FAILED",
        "EMAIL_SEND_CANCELLED",
        "PERSONAL_TELEGRAM_CONNECTED",
        "PERSONAL_TELEGRAM_DISCONNECTED",
        "TELEGRAM_PERSONAL_MESSAGE_RECEIVED",
        "TELEGRAM_REPLY_DRAFT_CREATED",
        "TELEGRAM_PERSONAL_MESSAGE_SENT",
        "TELEGRAM_PERSONAL_SEND_FAILED",
        "FINANCE_EXPENSE_CREATED",
        "FINANCE_INCOME_CREATED",
        "FINANCE_TRANSACTION_UPDATED",
        "FINANCE_TRANSACTION_DELETED",
        "FINANCE_CATEGORY_CREATED",
        "FINANCE_CATEGORY_DEACTIVATED",
        "FINANCE_REPORT_VIEWED",
        "NOTE_CREATED",
        "NOTE_UPDATED",
        "NOTE_DELETED",
        "NOTE_VIEWED",
        "NOTE_SEARCHED",
        "NOTE_ATTACHMENT_ADDED",
        "NOTE_ATTACHMENT_VIEWED",
        "NOTE_PROJECT_CREATED",
        "NOTE_TAG_CREATED",
        "TASK_CREATED",
        "TASK_UPDATED",
        "TASK_COMPLETED",
        "TASK_CANCELLED",
        "TASK_DELETED",
        "TASK_CARRIED_FORWARD",
        "TASK_PRIORITY_CHANGED",
        "TASK_CALENDAR_LINKED",
        "TASK_REMINDER_CREATED",
        "AI_REQUEST_RECEIVED",
        "AI_ACTION_PARSED",
        "AI_ACTION_CONFIRMATION_REQUESTED",
        "AI_ACTION_CONFIRMED",
        "AI_ACTION_CANCELLED",
        "AI_ACTION_EXECUTED",
        "AI_ACTION_FAILED",
        "VOICE_TRANSCRIBED",
        "MORNING_BRIEFING_SENT",
        "EVENING_SUMMARY_SENT",
        "DAILY_SETTINGS_UPDATED",
        "DAILY_DELIVERY_FAILED",
        "TASK_CARRY_FORWARD_CONFIRMED",
    }
