from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.database.models import AuditLog, FinanceCategory, FinanceTransaction
from app.database.models.finance import FinanceCategoryType, FinanceTransactionType
from app.database.session import DatabaseManager
from app.modules.finance.exceptions import (
    FinanceDuplicateError,
    FinanceNotFoundError,
    FinanceValidationError,
)
from app.modules.finance.schemas import FinanceTransactionCreate, FinanceTransactionUpdate
from app.modules.finance.service import FinanceService

NOW = datetime(2026, 9, 24, 12, tzinfo=UTC)


def manager(engine) -> DatabaseManager:
    database = DatabaseManager(Settings(_env_file=None))
    database._sessions = async_sessionmaker(engine, expire_on_commit=False)
    return database


def service(engine) -> FinanceService:
    return FinanceService(manager(engine), 42, Settings(_env_file=None).timezone, 10, 5)


async def seeded(engine) -> FinanceService:
    finance = service(engine)
    assert await finance.seed_defaults() == 16
    return finance


async def category_id(finance: FinanceService, slug: str) -> int:
    return next(item.id for item in await finance.list_categories() if item.slug == slug)


def request(kind, category: int, amount="100", currency="UZS", day=date(2026, 9, 24)):
    return FinanceTransactionCreate(
        transaction_type=kind,
        category_id=category,
        amount=amount,
        currency=currency,
        description="private description",
        transaction_date=day,
        occurred_at=NOW,
    )


async def test_default_categories_seed_idempotently(engine) -> None:
    finance = service(engine)
    assert await finance.seed_defaults() == 16
    assert await finance.seed_defaults() == 0
    rows = await finance.list_categories()
    assert len(rows) == 16 and all(row.is_system for row in rows)


async def test_expense_and_income_creation_use_decimal(engine) -> None:
    finance = await seeded(engine)
    expense = await finance.create_transaction(
        request(FinanceTransactionType.EXPENSE, await category_id(finance, "taxi"), "85000")
    )
    income = await finance.create_transaction(
        request(
            FinanceTransactionType.INCOME,
            await category_id(finance, "salary"),
            "15000000",
        )
    )
    assert expense.amount == Decimal("85000.00")
    assert income.amount == Decimal("15000000.00")
    assert expense.transaction_type == FinanceTransactionType.EXPENSE
    assert income.transaction_type == FinanceTransactionType.INCOME


def test_schema_rejects_float_zero_negative_and_naive_timestamp() -> None:
    values = {
        "transaction_type": "EXPENSE",
        "category_id": 1,
        "currency": "UZS",
        "transaction_date": date(2026, 9, 24),
    }
    for amount in (1.5, "0", "-2"):
        with pytest.raises((ValidationError, FinanceValidationError)):
            FinanceTransactionCreate(amount=amount, **values)
    with pytest.raises(ValidationError, match="timezone-aware"):
        FinanceTransactionCreate(
            amount="1",
            occurred_at=datetime(2026, 1, 1),  # noqa: DTZ001 - validation target
            **values,
        )


async def test_category_compatibility_is_service_validated(engine) -> None:
    finance = await seeded(engine)
    salary = await category_id(finance, "salary")
    taxi = await category_id(finance, "taxi")
    with pytest.raises(FinanceValidationError):
        await finance.create_transaction(request(FinanceTransactionType.EXPENSE, salary))
    with pytest.raises(FinanceValidationError):
        await finance.create_transaction(request(FinanceTransactionType.INCOME, taxi))


async def test_custom_category_duplicate_and_deactivation(engine) -> None:
    finance = await seeded(engine)
    custom = await finance.create_category("Professional Services", FinanceCategoryType.INCOME)
    assert not custom.is_system
    with pytest.raises(FinanceDuplicateError):
        await finance.create_category(" professional   services ", FinanceCategoryType.EXPENSE)
    await finance.deactivate_category(custom.id)
    assert all(item.id != custom.id for item in await finance.list_categories())
    with pytest.raises(FinanceNotFoundError):
        await finance.deactivate_category(custom.id)


async def test_recent_order_edit_and_soft_delete(engine) -> None:
    finance = await seeded(engine)
    taxi = await category_id(finance, "taxi")
    food = await category_id(finance, "food")
    older = await finance.create_transaction(
        request(FinanceTransactionType.EXPENSE, taxi, day=date(2026, 9, 23))
    )
    newer = await finance.create_transaction(
        request(FinanceTransactionType.EXPENSE, food, day=date(2026, 9, 24))
    )
    assert [row.id for row in await finance.list_recent()] == [newer.id, older.id]
    updated = await finance.update_transaction(
        older.id,
        FinanceTransactionUpdate(
            amount="250.50", category_id=food, description=None, transaction_date=date(2026, 9, 25)
        ),
    )
    assert updated.amount == Decimal("250.50") and updated.category_name == "Food"
    assert updated.description is None and updated.transaction_date == date(2026, 9, 25)
    await finance.delete_transaction(newer.id)
    assert [row.id for row in await finance.list_recent()] == [older.id]
    with pytest.raises(FinanceNotFoundError):
        await finance.get_transaction(newer.id)


async def test_owner_isolation(engine) -> None:
    finance = await seeded(engine)
    taxi = await category_id(finance, "taxi")
    row = await finance.create_transaction(request(FinanceTransactionType.EXPENSE, taxi))
    other = FinanceService(finance.database, 999, finance.timezone, 10, 5)
    await other.seed_defaults()
    with pytest.raises(FinanceNotFoundError):
        await other.get_transaction(row.id)


async def test_audit_uses_ids_not_description(engine) -> None:
    finance = await seeded(engine)
    taxi = await category_id(finance, "taxi")
    await finance.create_transaction(request(FinanceTransactionType.EXPENSE, taxi))
    async with finance.database.session() as session:
        events = list(await session.scalars(select(AuditLog)))
        serialized = " ".join(str(event.details) for event in events)
        assert "private description" not in serialized
        assert any(event.action == "FINANCE_EXPENSE_CREATED" for event in events)


async def test_database_amount_column_is_numeric_not_float(engine) -> None:
    finance = await seeded(engine)
    taxi = await category_id(finance, "taxi")
    await finance.create_transaction(request(FinanceTransactionType.EXPENSE, taxi, "10.25"))
    async with finance.database.session() as session:
        row = await session.scalar(select(FinanceTransaction))
        assert isinstance(row.amount, Decimal) and row.amount == Decimal("10.25")
        category = await session.scalar(select(FinanceCategory).where(FinanceCategory.slug == "taxi"))
        assert category.user_id == row.user_id
