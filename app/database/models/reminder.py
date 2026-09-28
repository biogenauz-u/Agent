from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UTCDateTime


class ReminderStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    MISSED = "MISSED"
    CANCELLED = "CANCELLED"


class ReminderChannel(StrEnum):
    TELEGRAM = "TELEGRAM"


class Reminder(TimestampMixin, Base):
    __tablename__ = "reminders"
    __table_args__ = (
        Index("ix_reminders_status_remind_at", "status", "remind_at"),
        Index("ix_reminders_calendar_event", "external_calendar_event_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    external_calendar_event_id: Mapped[str | None] = mapped_column(String(1024))
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str | None] = mapped_column(Text)
    remind_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    retry_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    event_start_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    offset_minutes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus, native_enum=False, length=16),
        default=ReminderStatus.PENDING,
        server_default=ReminderStatus.PENDING.value,
        index=True,
    )
    channel: Mapped[ReminderChannel] = mapped_column(
        Enum(ReminderChannel, native_enum=False, length=16),
        default=ReminderChannel.TELEGRAM,
        server_default=ReminderChannel.TELEGRAM.value,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer)
    processing_started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    delivered_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    failed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    failure_reason: Mapped[str | None] = mapped_column(String(120))
    deduplication_key: Mapped[str] = mapped_column(String(64), unique=True)
