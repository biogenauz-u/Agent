from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UTCDateTime


class FinanceTransactionType(StrEnum):
    EXPENSE = "EXPENSE"
    INCOME = "INCOME"


class FinanceCategoryType(StrEnum):
    EXPENSE = "EXPENSE"
    INCOME = "INCOME"
    BOTH = "BOTH"


class FinanceSource(StrEnum):
    TELEGRAM_MANUAL = "TELEGRAM_MANUAL"


class FinanceCategory(TimestampMixin, Base):
    __tablename__ = "finance_categories"
    __table_args__ = (
        UniqueConstraint("user_id", "slug", name="uq_finance_categories_user_slug"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(80))
    transaction_type: Mapped[FinanceCategoryType] = mapped_column(
        Enum(FinanceCategoryType, native_enum=False, length=16)
    )
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class FinanceTransaction(TimestampMixin, Base):
    __tablename__ = "finance_transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_finance_transactions_user_date", "user_id", "transaction_date"),
        Index(
            "ix_finance_transactions_user_type_date",
            "user_id",
            "transaction_type",
            "transaction_date",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    transaction_type: Mapped[FinanceTransactionType] = mapped_column(
        Enum(FinanceTransactionType, native_enum=False, length=16), index=True
    )
    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("finance_categories.id", ondelete="RESTRICT"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    currency: Mapped[str] = mapped_column(String(3), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    occurred_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    source: Mapped[FinanceSource] = mapped_column(
        Enum(FinanceSource, native_enum=False, length=32),
        default=FinanceSource.TELEGRAM_MANUAL,
        server_default=FinanceSource.TELEGRAM_MANUAL.value,
    )
    external_reference: Mapped[str | None] = mapped_column(String(255))
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
