from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UTCDateTime


class TaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class TaskPriority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskSource(StrEnum):
    TELEGRAM_MANUAL = "TELEGRAM_MANUAL"


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_user_status_due_at", "user_id", "status", "due_at"),
        Index("ix_tasks_user_due_date", "user_id", "due_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, length=16), default=TaskStatus.TODO, index=True
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, native_enum=False, length=16), default=TaskPriority.NORMAL, index=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    due_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    calendar_event_id: Mapped[str | None] = mapped_column(String(1024))
    reminder_id: Mapped[int | None] = mapped_column(BigInteger)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_offset_minutes: Mapped[int | None] = mapped_column(Integer)
    recurrence_rule: Mapped[str | None] = mapped_column(String(255))
    parent_task_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tasks.id", ondelete="SET NULL")
    )
    source: Mapped[TaskSource] = mapped_column(
        Enum(TaskSource, native_enum=False, length=32),
        default=TaskSource.TELEGRAM_MANUAL,
        server_default=TaskSource.TELEGRAM_MANUAL.value,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), index=True)
