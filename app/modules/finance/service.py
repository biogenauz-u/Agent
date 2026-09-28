from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError

from app.database.models.finance import (
    FinanceCategory,
    FinanceCategoryType,
    FinanceTransaction,
    FinanceTransactionType,
)
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.finance.audit import FinanceAudit
from app.modules.finance.categories import DEFAULT_CATEGORIES
from app.modules.finance.exceptions import (
    FinanceDuplicateError,
    FinanceNotFoundError,
    FinanceValidationError,
)
from app.modules.finance.reports import FinanceReportService
from app.modules.finance.repository import (
    FinanceCategoryRepository,
    FinanceTransactionRepository,
)
from app.modules.finance.schemas import (
    FinanceCategoryView,
    FinanceTransactionCreate,
    FinanceTransactionUpdate,
    FinanceTransactionView,
)
from app.modules.finance.utils import category_slug, normalize_category_name
from app.modules.users.repository import UserRepository


class FinanceService:
    def __init__(
        self,
        database: DatabaseManager,
        owner_id: int,
        timezone: ZoneInfo,
        recent_limit: int,
        top_limit: int,
    ) -> None:
        self.database, self.owner_id, self.timezone = database, owner_id, timezone
        self.recent_limit = recent_limit
        self.audit = FinanceAudit(database, owner_id)
        self.reports = FinanceReportService(database, owner_id, timezone, top_limit)

    async def _owner(self, session, *, create: bool = False) -> int | None:
        users = UserRepository(session)
        owner = await users.get_by_telegram_user_id(self.owner_id)
        if owner is None and create:
            owner = await users.create(self.owner_id)
        return owner.id if owner else None

    @staticmethod
    def _category_view(row: FinanceCategory) -> FinanceCategoryView:
        return FinanceCategoryView.model_validate(row, from_attributes=True)

    @staticmethod
    def _transaction_view(
        row: FinanceTransaction, category_name: str
    ) -> FinanceTransactionView:
        return FinanceTransactionView(
            id=row.id,
            transaction_type=row.transaction_type,
            category_id=row.category_id,
            category_name=category_name,
            amount=Decimal(row.amount),
            currency=row.currency,
            description=row.description,
            transaction_date=row.transaction_date,
            occurred_at=row.occurred_at,
            source=row.source,
            created_at=row.created_at,
        )

    async def seed_defaults(self) -> int:
        created = 0
        async with self.database.session() as session:
            owner = await self._owner(session, create=True)
            assert owner is not None
            repository = FinanceCategoryRepository(session)
            for name, slug, category_type in DEFAULT_CATEGORIES:
                if await repository.get_by_slug(owner, slug) is None:
                    await repository.create(
                        owner, name, slug, category_type, is_system=True
                    )
                    created += 1
        return created

    async def list_categories(
        self, transaction_type: FinanceTransactionType | str | None = None
    ) -> list[FinanceCategoryView]:
        if isinstance(transaction_type, str):
            transaction_type = FinanceTransactionType(transaction_type)
        async with self.database.session() as session:
            owner = await self._owner(session)
            rows = (
                await FinanceCategoryRepository(session).list(owner, transaction_type)
                if owner
                else []
            )
            return [self._category_view(row) for row in rows]

    async def create_category(
        self, name: str, category_type: FinanceCategoryType
    ) -> FinanceCategoryView:
        normalized = normalize_category_name(name)
        slug = category_slug(normalized)
        try:
            async with self.database.session() as session:
                owner = await self._owner(session, create=True)
                assert owner is not None
                repository = FinanceCategoryRepository(session)
                if await repository.get_by_slug(owner, slug):
                    raise FinanceDuplicateError("Category already exists.")
                row = await repository.create(owner, normalized, slug, category_type)
                view = self._category_view(row)
        except IntegrityError:
            raise FinanceDuplicateError("Category already exists.") from None
        await self.audit.record(
            AuditAction.FINANCE_CATEGORY_CREATED,
            entity_type="finance_category",
            entity_id=view.id,
            details={"category_id": view.id, "category_type": view.transaction_type.value},
        )
        return view

    async def deactivate_category(self, category_id: int) -> None:
        async with self.database.session() as session:
            owner = await self._owner(session)
            if not owner or not await FinanceCategoryRepository(session).deactivate(
                owner, category_id
            ):
                raise FinanceNotFoundError("Active category not found.")
        await self.audit.record(
            AuditAction.FINANCE_CATEGORY_DEACTIVATED,
            entity_type="finance_category",
            entity_id=category_id,
            details={"category_id": category_id},
        )

    async def _validate_category(
        self,
        session,
        owner: int,
        category_id: int,
        transaction_type: FinanceTransactionType,
    ) -> FinanceCategory:
        category = await FinanceCategoryRepository(session).get(owner, category_id)
        compatible = {
            FinanceCategoryType.BOTH,
            FinanceCategoryType(transaction_type.value),
        }
        if category is None or not category.is_active or category.transaction_type not in compatible:
            raise FinanceValidationError("Category is not compatible with transaction type.")
        return category

    async def create_transaction(
        self, request: FinanceTransactionCreate
    ) -> FinanceTransactionView:
        async with self.database.session() as session:
            owner = await self._owner(session, create=True)
            assert owner is not None
            category = await self._validate_category(
                session, owner, request.category_id, request.transaction_type
            )
            row = await FinanceTransactionRepository(session).create(owner, request)
            view = self._transaction_view(row, category.name)
        action = (
            AuditAction.FINANCE_EXPENSE_CREATED
            if request.transaction_type == FinanceTransactionType.EXPENSE
            else AuditAction.FINANCE_INCOME_CREATED
        )
        await self.audit.record(
            action,
            entity_type="finance_transaction",
            entity_id=view.id,
            details={
                "transaction_id": view.id,
                "category_id": view.category_id,
                "currency": view.currency,
                "amount": str(view.amount),
            },
        )
        return view

    async def get_transaction(self, transaction_id: int) -> FinanceTransactionView:
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = (
                await FinanceTransactionRepository(session).get(owner, transaction_id)
                if owner
                else None
            )
            if row is None:
                raise FinanceNotFoundError("Transaction not found.")
            category = await FinanceCategoryRepository(session).get(owner, row.category_id)
            assert category is not None
            return self._transaction_view(row, category.name)

    async def list_recent(self) -> list[FinanceTransactionView]:
        async with self.database.session() as session:
            owner = await self._owner(session)
            rows = (
                await FinanceTransactionRepository(session).list_recent(
                    owner, self.recent_limit
                )
                if owner
                else []
            )
            return [self._transaction_view(row, name) for row, name in rows]

    async def totals_for_date(self, day: date) -> dict[str, dict[str, Decimal]]:
        async with self.database.session() as session:
            owner = await self._owner(session)
            rows = (
                await FinanceTransactionRepository(session).list_recent(owner, 10_000)
                if owner
                else []
            )
        totals: dict[str, dict[str, Decimal]] = {}
        for row, _ in rows:
            if row.transaction_date != day:
                continue
            currency = totals.setdefault(
                row.currency, {"income": Decimal(0), "expense": Decimal(0)}
            )
            key = (
                "income"
                if row.transaction_type == FinanceTransactionType.INCOME
                else "expense"
            )
            currency[key] += Decimal(row.amount)
        return totals

    async def update_transaction(
        self, transaction_id: int, request: FinanceTransactionUpdate
    ) -> FinanceTransactionView:
        values = request.model_dump(exclude_unset=True)
        async with self.database.session() as session:
            owner = await self._owner(session)
            current = (
                await FinanceTransactionRepository(session).get(owner, transaction_id)
                if owner
                else None
            )
            if current is None or owner is None:
                raise FinanceNotFoundError("Transaction not found.")
            if request.category_id is not None:
                await self._validate_category(
                    session, owner, request.category_id, current.transaction_type
                )
            row = await FinanceTransactionRepository(session).update(
                owner, transaction_id, values
            )
            assert row is not None
            category = await FinanceCategoryRepository(session).get(owner, row.category_id)
            assert category is not None
            view = self._transaction_view(row, category.name)
        await self.audit.record(
            AuditAction.FINANCE_TRANSACTION_UPDATED,
            entity_type="finance_transaction",
            entity_id=transaction_id,
            details={"transaction_id": transaction_id},
        )
        return view

    async def delete_transaction(self, transaction_id: int) -> None:
        async with self.database.session() as session:
            owner = await self._owner(session)
            if not owner or not await FinanceTransactionRepository(session).soft_delete(
                owner, transaction_id
            ):
                raise FinanceNotFoundError("Transaction not found.")
        await self.audit.record(
            AuditAction.FINANCE_TRANSACTION_DELETED,
            entity_type="finance_transaction",
            entity_id=transaction_id,
            details={"transaction_id": transaction_id},
        )

    def today(self) -> date:
        return datetime.now(self.timezone).date()
