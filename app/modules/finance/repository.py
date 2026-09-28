from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.finance import (
    FinanceCategory,
    FinanceCategoryType,
    FinanceTransaction,
    FinanceTransactionType,
)
from app.modules.finance.schemas import FinanceTransactionCreate


class FinanceCategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: int, category_id: int) -> FinanceCategory | None:
        return await self.session.scalar(
            select(FinanceCategory).where(
                FinanceCategory.user_id == user_id, FinanceCategory.id == category_id
            )
        )

    async def get_by_slug(self, user_id: int, slug: str) -> FinanceCategory | None:
        return await self.session.scalar(
            select(FinanceCategory).where(
                FinanceCategory.user_id == user_id, FinanceCategory.slug == slug
            )
        )

    async def list(
        self,
        user_id: int,
        transaction_type: FinanceTransactionType | None = None,
        *,
        active_only: bool = True,
    ) -> list[FinanceCategory]:
        query = select(FinanceCategory).where(FinanceCategory.user_id == user_id)
        if active_only:
            query = query.where(FinanceCategory.is_active.is_(True))
        if transaction_type is not None:
            query = query.where(
                FinanceCategory.transaction_type.in_(
                    [FinanceCategoryType(transaction_type.value), FinanceCategoryType.BOTH]
                )
            )
        rows = await self.session.scalars(query.order_by(FinanceCategory.name, FinanceCategory.id))
        return list(rows)

    async def create(
        self,
        user_id: int,
        name: str,
        slug: str,
        category_type: FinanceCategoryType,
        *,
        is_system: bool = False,
    ) -> FinanceCategory:
        row = FinanceCategory(
            user_id=user_id,
            name=name,
            slug=slug,
            transaction_type=category_type,
            is_system=is_system,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def deactivate(self, user_id: int, category_id: int) -> bool:
        result = await self.session.execute(
            update(FinanceCategory)
            .where(
                FinanceCategory.user_id == user_id,
                FinanceCategory.id == category_id,
                FinanceCategory.is_active.is_(True),
            )
            .values(is_active=False)
            .returning(FinanceCategory.id)
        )
        return result.scalar_one_or_none() is not None


class FinanceTransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, user_id: int, request: FinanceTransactionCreate
    ) -> FinanceTransaction:
        row = FinanceTransaction(user_id=user_id, **request.model_dump())
        self.session.add(row)
        await self.session.flush()
        return row

    async def get(self, user_id: int, transaction_id: int) -> FinanceTransaction | None:
        return await self.session.scalar(
            select(FinanceTransaction).where(
                FinanceTransaction.user_id == user_id,
                FinanceTransaction.id == transaction_id,
                FinanceTransaction.deleted_at.is_(None),
            )
        )

    async def list_recent(self, user_id: int, limit: int) -> list[tuple[FinanceTransaction, str]]:
        rows = await self.session.execute(
            select(FinanceTransaction, FinanceCategory.name)
            .join(FinanceCategory, FinanceCategory.id == FinanceTransaction.category_id)
            .where(
                FinanceTransaction.user_id == user_id,
                FinanceTransaction.deleted_at.is_(None),
            )
            .order_by(
                FinanceTransaction.transaction_date.desc(),
                FinanceTransaction.created_at.desc(),
                FinanceTransaction.id.desc(),
            )
            .limit(limit)
        )
        return [(transaction, name) for transaction, name in rows.all()]

    async def update(
        self, user_id: int, transaction_id: int, values: dict[str, object]
    ) -> FinanceTransaction | None:
        if not values:
            return await self.get(user_id, transaction_id)
        await self.session.execute(
            update(FinanceTransaction)
            .where(
                FinanceTransaction.user_id == user_id,
                FinanceTransaction.id == transaction_id,
                FinanceTransaction.deleted_at.is_(None),
            )
            .values(**values)
        )
        await self.session.flush()
        return await self.get(user_id, transaction_id)

    async def soft_delete(self, user_id: int, transaction_id: int) -> bool:
        result = await self.session.execute(
            update(FinanceTransaction)
            .where(
                FinanceTransaction.user_id == user_id,
                FinanceTransaction.id == transaction_id,
                FinanceTransaction.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(UTC))
            .returning(FinanceTransaction.id)
        )
        return result.scalar_one_or_none() is not None

    async def totals(
        self, user_id: int, start: date, end: date
    ) -> list[tuple[str, Decimal, Decimal, int]]:
        rows = await self.session.execute(
            select(
                FinanceTransaction.currency,
                func.coalesce(
                    func.sum(
                        case(
                            (
                                FinanceTransaction.transaction_type
                                == FinanceTransactionType.INCOME,
                                FinanceTransaction.amount,
                            ),
                            else_=Decimal("0.00"),
                        )
                    ),
                    Decimal("0.00"),
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                FinanceTransaction.transaction_type
                                == FinanceTransactionType.EXPENSE,
                                FinanceTransaction.amount,
                            ),
                            else_=Decimal("0.00"),
                        )
                    ),
                    Decimal("0.00"),
                ),
                func.count(FinanceTransaction.id),
            )
            .where(
                FinanceTransaction.user_id == user_id,
                FinanceTransaction.deleted_at.is_(None),
                FinanceTransaction.transaction_date >= start,
                FinanceTransaction.transaction_date < end,
            )
            .group_by(FinanceTransaction.currency)
            .order_by(FinanceTransaction.currency)
        )
        return [
            (currency, Decimal(income), Decimal(expense), int(count))
            for currency, income, expense, count in rows.all()
        ]

    async def top_expense_categories(
        self, user_id: int, start: date, end: date, limit: int
    ) -> list[tuple[int, str, str, Decimal]]:
        total = func.sum(FinanceTransaction.amount).label("total")
        rows = await self.session.execute(
            select(
                FinanceCategory.id,
                FinanceCategory.name,
                FinanceTransaction.currency,
                total,
            )
            .join(FinanceCategory, FinanceCategory.id == FinanceTransaction.category_id)
            .where(
                FinanceTransaction.user_id == user_id,
                FinanceTransaction.deleted_at.is_(None),
                FinanceTransaction.transaction_type == FinanceTransactionType.EXPENSE,
                FinanceTransaction.transaction_date >= start,
                FinanceTransaction.transaction_date < end,
            )
            .group_by(FinanceCategory.id, FinanceCategory.name, FinanceTransaction.currency)
            .order_by(total.desc(), FinanceCategory.name, FinanceTransaction.currency)
            .limit(limit)
        )
        return [(identifier, name, currency, Decimal(amount)) for identifier, name, currency, amount in rows.all()]
