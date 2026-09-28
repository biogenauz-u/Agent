"""Persistent Telegram reminder occurrences."""

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str = "0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    status = sa.Enum(
        "PENDING",
        "PROCESSING",
        "DELIVERED",
        "FAILED",
        "MISSED",
        "CANCELLED",
        name="reminderstatus",
        native_enum=False,
        length=16,
    )
    channel = sa.Enum("TELEGRAM", name="reminderchannel", native_enum=False, length=16)
    op.create_table(
        "reminders",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("external_calendar_event_id", sa.String(1024), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("offset_minutes", sa.Integer(), nullable=True),
        sa.Column("status", status, server_default="PENDING", nullable=False),
        sa.Column("channel", channel, server_default="TELEGRAM", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(120), nullable=True),
        sa.Column("deduplication_key", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("deduplication_key", name="uq_reminders_deduplication_key"),
    )
    op.create_index("ix_reminders_user_id", "reminders", ["user_id"])
    op.create_index("ix_reminders_remind_at", "reminders", ["remind_at"])
    op.create_index("ix_reminders_status", "reminders", ["status"])
    op.create_index("ix_reminders_status_remind_at", "reminders", ["status", "remind_at"])
    op.create_index(
        "ix_reminders_calendar_event", "reminders", ["external_calendar_event_id", "status"]
    )


def downgrade() -> None:
    op.drop_table("reminders")
