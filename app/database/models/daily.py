from datetime import date, datetime, time
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UTCDateTime


class DailyDeliveryType(StrEnum):
    MORNING = "MORNING"
    EVENING = "EVENING"


class DailyDeliveryStatus(StrEnum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class DailySettings(TimestampMixin, Base):
    __tablename__ = "daily_settings"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    morning_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    morning_time: Mapped[time] = mapped_column(Time, default=time(8, 0))
    evening_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    evening_time: Mapped[time] = mapped_column(Time, default=time(20, 0))


class DailyDelivery(TimestampMixin, Base):
    __tablename__ = "daily_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "delivery_type", "scheduled_date", name="uq_daily_delivery_identity"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    delivery_type: Mapped[DailyDeliveryType] = mapped_column(
        Enum(DailyDeliveryType, native_enum=False, length=16), index=True
    )
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    scheduled_for: Mapped[datetime] = mapped_column(UTCDateTime())
    delivered_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    status: Mapped[DailyDeliveryStatus] = mapped_column(
        Enum(DailyDeliveryStatus, native_enum=False, length=16), index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
