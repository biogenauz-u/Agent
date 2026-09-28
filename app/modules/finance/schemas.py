from datetime import UTC, date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.database.models.finance import (
    FinanceCategoryType,
    FinanceSource,
    FinanceTransactionType,
)
from app.modules.finance.utils import normalize_currency, parse_amount


class FinanceCategoryView(BaseModel):
    id: int
    name: str
    slug: str
    transaction_type: FinanceCategoryType
    is_system: bool
    is_active: bool


class FinanceTransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    transaction_type: FinanceTransactionType
    category_id: int = Field(gt=0)
    amount: Decimal
    currency: str
    description: str | None = Field(default=None, max_length=500)
    transaction_date: date
    occurred_at: datetime | None = None
    source: FinanceSource = FinanceSource.TELEGRAM_MANUAL

    @field_validator("amount", mode="before")
    @classmethod
    def amount_valid(cls, value: object) -> Decimal:
        if isinstance(value, float):
            raise ValueError("Float amounts are forbidden")  # noqa: TRY004
        return parse_amount(value)  # type: ignore[arg-type]

    @field_validator("currency")
    @classmethod
    def currency_valid(cls, value: str) -> str:
        return normalize_currency(value)

    @field_validator("description")
    @classmethod
    def description_clean(cls, value: str | None) -> str | None:
        cleaned = " ".join(value.split()) if value else None
        return cleaned or None

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("occurred_at must be timezone-aware")
        return value.astimezone(UTC) if value else None


class FinanceTransactionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    amount: Decimal | None = None
    category_id: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=500)
    transaction_date: date | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def amount_valid(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, float):
            raise ValueError("Float amounts are forbidden")  # noqa: TRY004
        return parse_amount(value)  # type: ignore[arg-type]


class FinanceTransactionView(BaseModel):
    id: int
    transaction_type: FinanceTransactionType
    category_id: int
    category_name: str
    amount: Decimal
    currency: str
    description: str | None
    transaction_date: date
    occurred_at: datetime | None
    source: FinanceSource
    created_at: datetime


class MoneyTotal(BaseModel):
    currency: str
    amount: Decimal


class CurrencyReport(BaseModel):
    currency: str
    income: Decimal = Decimal("0.00")
    expense: Decimal = Decimal("0.00")
    balance: Decimal = Decimal("0.00")
    transaction_count: int = 0


class CategorySpend(BaseModel):
    category_id: int
    category_name: str
    currency: str
    amount: Decimal


class FinancePeriodReport(BaseModel):
    period: str
    start: date
    end_exclusive: date
    currencies: list[CurrencyReport] = Field(default_factory=list)
    top_expense_categories: list[CategorySpend] = Field(default_factory=list)
