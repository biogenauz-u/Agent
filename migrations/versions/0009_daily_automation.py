"""Persistent daily settings and idempotent delivery records."""

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str = "0008"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "daily_settings",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("morning_enabled", sa.Boolean(), nullable=False),
        sa.Column("morning_time", sa.Time(), nullable=False),
        sa.Column("evening_enabled", sa.Boolean(), nullable=False),
        sa.Column("evening_time", sa.Time(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_daily_settings_user_id"),
    )
    op.create_index("ix_daily_settings_user_id", "daily_settings", ["user_id"], unique=True)
    op.create_table(
        "daily_deliveries",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("delivery_type", sa.String(16), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "user_id", "delivery_type", "scheduled_date", name="uq_daily_delivery_identity"
        ),
    )
    op.create_index("ix_daily_deliveries_user_id", "daily_deliveries", ["user_id"])
    op.create_index("ix_daily_deliveries_delivery_type", "daily_deliveries", ["delivery_type"])
    op.create_index("ix_daily_deliveries_scheduled_date", "daily_deliveries", ["scheduled_date"])
    op.create_index("ix_daily_deliveries_status", "daily_deliveries", ["status"])


def downgrade() -> None:
    op.drop_table("daily_deliveries")
    op.drop_table("daily_settings")
