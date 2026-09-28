from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.database.models.finance import FinanceTransactionType
from app.database.session import DatabaseManager
from app.modules.finance.schemas import FinanceTransactionCreate
from app.modules.finance.service import FinanceService

NOW = datetime(2026, 9, 24, 12, tzinfo=UTC)


async def seeded(engine) -> FinanceService:
    database = DatabaseManager(Settings(_env_file=None))
    database._sessions = async_sessionmaker(engine, expire_on_commit=False)
    finance = FinanceService(database, 42, Settings(_env_file=None).timezone, 10, 5)
    await finance.seed_defaults()
    return finance


async def category_id(finance: FinanceService, slug: str) -> int:
    return next(item.id for item in await finance.list_categories() if item.slug == slug)


async def add(finance, kind, category, amount, currency, day):
    return await finance.create_transaction(
        FinanceTransactionCreate(
            transaction_type=kind,
            category_id=category,
            amount=amount,
            currency=currency,
            transaction_date=day,
        )
    )


async def test_daily_weekly_monthly_yearly_and_multicurrency(engine) -> None:
    finance = await seeded(engine)
    finance.reports.now = lambda: NOW
    taxi = await category_id(finance, "taxi")
    food = await category_id(finance, "food")
    salary = await category_id(finance, "salary")
    await add(finance, FinanceTransactionType.EXPENSE, taxi, "100", "UZS", date(2026, 9, 24))
    await add(finance, FinanceTransactionType.EXPENSE, food, "50", "UZS", date(2026, 9, 24))
    await add(finance, FinanceTransactionType.INCOME, salary, "500", "UZS", date(2026, 9, 24))
    await add(finance, FinanceTransactionType.EXPENSE, taxi, "20", "USD", date(2026, 9, 24))
    await add(finance, FinanceTransactionType.INCOME, salary, "10", "USD", date(2026, 9, 22))
    await add(finance, FinanceTransactionType.EXPENSE, taxi, "30", "EUR", date(2026, 8, 1))
    await add(finance, FinanceTransactionType.INCOME, salary, "1000", "UZS", date(2026, 1, 1))

    daily = await finance.reports.report("today")
    weekly = await finance.reports.report("week")
    monthly = await finance.reports.report("month")
    yearly = await finance.reports.report("year")
    daily_by_currency = {item.currency: item for item in daily.currencies}
    assert daily_by_currency["UZS"].income == Decimal("500.00")
    assert daily_by_currency["UZS"].expense == Decimal("150.00")
    assert daily_by_currency["UZS"].balance == Decimal("350.00")
    assert daily_by_currency["USD"].balance == Decimal("-20.00")
    assert len(daily_by_currency) == 2  # UZS and USD remain separate.
    assert {item.currency for item in weekly.currencies} == {"UZS", "USD"}
    assert {item.currency for item in monthly.currencies} == {"UZS", "USD"}
    assert {item.currency for item in yearly.currencies} == {"EUR", "USD", "UZS"}
    yearly_uzs = next(item for item in yearly.currencies if item.currency == "UZS")
    assert yearly_uzs.income == Decimal("1500.00")


async def test_top_categories_stable_and_deleted_excluded(engine) -> None:
    finance = await seeded(engine)
    finance.reports.now = lambda: NOW
    taxi = await category_id(finance, "taxi")
    food = await category_id(finance, "food")
    taxi_row = await add(
        finance, FinanceTransactionType.EXPENSE, taxi, "100", "UZS", date(2026, 9, 24)
    )
    await add(finance, FinanceTransactionType.EXPENSE, food, "100", "UZS", date(2026, 9, 24))
    report = await finance.reports.report("month")
    assert [item.category_name for item in report.top_expense_categories] == ["Food", "Taxi"]
    await finance.delete_transaction(taxi_row.id)
    report = await finance.reports.report("month")
    assert [item.category_name for item in report.top_expense_categories] == ["Food"]
    assert report.currencies[0].expense == Decimal("100.00")
