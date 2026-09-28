from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.modules.calendar.state import MemoryTemporaryStore
from app.modules.finance.actions import FinanceActions
from app.modules.finance.exceptions import FinanceConfirmationError


async def test_expense_confirmation_is_single_use() -> None:
    service = AsyncMock()
    service.create_transaction.return_value.id = 7
    actions = FinanceActions(service, MemoryTemporaryStore(), 42)
    token = await actions.prepare(
        "create_transaction",
        {
            "transaction_type": "EXPENSE",
            "category_id": 1,
            "amount": "85000.00",
            "currency": "UZS",
            "description": "Taxi",
            "transaction_date": date(2026, 9, 24).isoformat(),
        },
    )
    assert service.create_transaction.await_count == 0
    assert "ID: 7" in await actions.confirm(token)
    service.create_transaction.assert_awaited_once()
    with pytest.raises(FinanceConfirmationError):
        await actions.confirm(token)
    service.create_transaction.assert_awaited_once()


async def test_income_cancel_never_persists() -> None:
    service = AsyncMock()
    actions = FinanceActions(service, MemoryTemporaryStore(), 42)
    token = await actions.prepare("create_transaction", {"transaction_type": "INCOME"})
    await actions.cancel(token)
    with pytest.raises(FinanceConfirmationError):
        await actions.confirm(token)
    service.create_transaction.assert_not_awaited()


async def test_update_delete_and_category_actions_dispatch() -> None:
    service = AsyncMock()
    service.update_transaction.return_value = object()
    actions = FinanceActions(service, MemoryTemporaryStore(), 42)
    update = await actions.prepare(
        "update_transaction", {"id": 3, "values": {"amount": "12.50"}}
    )
    delete = await actions.prepare("delete_transaction", {"id": 4})
    category = await actions.prepare(
        "create_category", {"name": "Books", "category_type": "EXPENSE"}
    )
    deactivate = await actions.prepare("deactivate_category", {"id": 9})
    await actions.confirm(update)
    await actions.confirm(delete)
    await actions.confirm(category)
    await actions.confirm(deactivate)
    service.update_transaction.assert_awaited_once()
    service.delete_transaction.assert_awaited_once_with(4)
    service.create_category.assert_awaited_once()
    service.deactivate_category.assert_awaited_once_with(9)
