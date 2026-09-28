from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.finance.audit import FinanceAudit
from app.modules.finance.repository import FinanceTransactionRepository
from app.modules.finance.schemas import CategorySpend, CurrencyReport, FinancePeriodReport
from app.modules.finance.utils import period_range
from app.modules.users.repository import UserRepository


class FinanceReportService:
    def __init__(
        self,
        database: DatabaseManager,
        owner_id: int,
        timezone: ZoneInfo,
        top_limit: int,
        *,
        now=lambda: datetime.now(UTC),
    ) -> None:
        self.database, self.owner_id, self.timezone = database, owner_id, timezone
        self.top_limit, self.now = top_limit, now
        self.audit = FinanceAudit(database, owner_id)

    async def report(self, period: str) -> FinancePeriodReport:
        start, end = period_range(period, self.now(), self.timezone)
        async with self.database.session() as session:
            owner = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            if owner is None:
                result = FinancePeriodReport(period=period, start=start, end_exclusive=end)
            else:
                repository = FinanceTransactionRepository(session)
                totals = await repository.totals(owner.id, start, end)
                categories = await repository.top_expense_categories(
                    owner.id, start, end, self.top_limit
                )
                result = FinancePeriodReport(
                    period=period,
                    start=start,
                    end_exclusive=end,
                    currencies=[
                        CurrencyReport(
                            currency=currency,
                            income=income,
                            expense=expense,
                            balance=income - expense,
                            transaction_count=count,
                        )
                        for currency, income, expense, count in totals
                    ],
                    top_expense_categories=[
                        CategorySpend(
                            category_id=category_id,
                            category_name=name,
                            currency=currency,
                            amount=Decimal(amount),
                        )
                        for category_id, name, currency, amount in categories
                    ],
                )
        await self.audit.record(
            AuditAction.FINANCE_REPORT_VIEWED,
            entity_type="finance_report",
            details={"period": period},
        )
        return result
