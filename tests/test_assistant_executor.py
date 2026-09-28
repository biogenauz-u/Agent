from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.database.models.finance import FinanceTransactionType
from app.modules.assistant.actions import AssistantActionType as A
from app.modules.assistant.executor import AssistantActionExecutor
from app.modules.assistant.schemas import ACTION_ADAPTER


def runtime(service, **extra):
    return SimpleNamespace(service=service, **extra)


async def test_calendar_create_uses_existing_service() -> None:
    service = SimpleNamespace(create_event=AsyncMock(return_value=SimpleNamespace(id="event-1")))
    context = SimpleNamespace(
        calendar=runtime(
            service,
            settings=SimpleNamespace(calendar_default_event_duration_minutes=60),
        )
    )
    action = ACTION_ADAPTER.validate_python(
        {
            "action": A.CREATE_CALENDAR_EVENT,
            "confidence": 1,
            "title": "Call",
            "start_at": "2026-09-25T15:00:00+05:00",
        }
    )
    result = await AssistantActionExecutor(context).execute(action)
    assert result.reference_id == "event-1"
    service.create_event.assert_awaited_once()


async def test_reminder_create_uses_existing_service() -> None:
    service = SimpleNamespace(
        create_standalone=AsyncMock(return_value=SimpleNamespace(id=3))
    )
    action = ACTION_ADAPTER.validate_python(
        {
            "action": A.CREATE_REMINDER,
            "confidence": 1,
            "message": "Call",
            "remind_at": "2026-09-25T15:00:00+05:00",
        }
    )
    result = await AssistantActionExecutor(
        SimpleNamespace(reminders=runtime(service))
    ).execute(action)
    assert result.reference_id == "3"


async def test_task_create_and_update_use_existing_service() -> None:
    service = SimpleNamespace(
        create_task=AsyncMock(return_value=SimpleNamespace(id=4)),
        update_task=AsyncMock(return_value=SimpleNamespace(id=4)),
    )
    executor = AssistantActionExecutor(SimpleNamespace(tasks=runtime(service)))
    created = await executor.execute(
        ACTION_ADAPTER.validate_python(
            {"action": A.CREATE_TASK, "confidence": 1, "title": "Ship"}
        )
    )
    updated = await executor.execute(
        ACTION_ADAPTER.validate_python(
            {
                "action": A.UPDATE_TASK,
                "confidence": 1,
                "internal_id": 4,
                "priority": "HIGH",
            }
        )
    )
    assert created.reference_id == updated.reference_id == "4"
    service.update_task.assert_awaited_once()


async def test_finance_create_resolves_category_then_calls_service() -> None:
    service = SimpleNamespace(
        list_categories=AsyncMock(
            return_value=[SimpleNamespace(id=2, name="Taxi", slug="taxi")]
        ),
        create_transaction=AsyncMock(return_value=SimpleNamespace(id=5)),
    )
    context = SimpleNamespace(
        finance=runtime(
            service,
            settings=SimpleNamespace(finance_default_currency="UZS"),
        )
    )
    action = ACTION_ADAPTER.validate_python(
        {
            "action": A.CREATE_EXPENSE,
            "confidence": 1,
            "amount": "85000",
            "currency": "UZS",
            "category": "Taxi",
            "transaction_date": date(2026, 9, 24),
        }
    )
    result = await AssistantActionExecutor(context).execute(action)
    assert result.reference_id == "5"
    assert service.list_categories.await_args.args[0] == FinanceTransactionType.EXPENSE


async def test_notebook_create_uses_existing_service() -> None:
    service = SimpleNamespace(
        create_note=AsyncMock(return_value=SimpleNamespace(id=6)),
        projects=AsyncMock(return_value=[]),
    )
    action = ACTION_ADAPTER.validate_python(
        {
            "action": A.CREATE_NOTE,
            "confidence": 1,
            "content": "Decision",
            "entry_date": "2026-09-24",
        }
    )
    result = await AssistantActionExecutor(
        SimpleNamespace(notebook=runtime(service))
    ).execute(action)
    assert result.reference_id == "6"


@pytest.mark.parametrize(
    ("action_type", "attribute"),
    [
        (A.READ_EMAIL, "email"),
        (A.READ_TELEGRAM_MESSAGE, "personal_telegram"),
    ],
)
async def test_read_actions_call_allowlisted_service(action_type, attribute) -> None:
    service = SimpleNamespace(read=AsyncMock(return_value=SimpleNamespace(id=9)))
    context = SimpleNamespace(**{attribute: runtime(service)})
    action = ACTION_ADAPTER.validate_python(
        {
            "action": action_type,
            "confidence": 1,
            "target_reference": "selected",
            "internal_id": 9,
        }
    )
    await AssistantActionExecutor(context).execute(action)
    service.read.assert_awaited_once_with(9)


async def test_email_reply_draft_never_sends() -> None:
    drafts = SimpleNamespace(create=AsyncMock(return_value="Thanks"))
    service = SimpleNamespace()
    action = ACTION_ADAPTER.validate_python(
        {
            "action": A.CREATE_EMAIL_REPLY_DRAFT,
            "confidence": 1,
            "target_reference": "email",
            "internal_id": 1,
            "instruction": "Thanks",
        }
    )
    result = await AssistantActionExecutor(
        SimpleNamespace(email=runtime(service, drafts=drafts))
    ).execute(action)
    assert "yuborilmadi" in result.message
    drafts.create.assert_awaited_once_with(1, "Thanks")
