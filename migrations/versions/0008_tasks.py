"""Persistent tasks with encrypted descriptions and integration links."""

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str = "0007"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description_encrypted", sa.LargeBinary()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("calendar_event_id", sa.String(1024)),
        sa.Column("reminder_id", sa.BigInteger()),
        sa.Column("reminder_enabled", sa.Boolean(), nullable=False),
        sa.Column("reminder_offset_minutes", sa.Integer()),
        sa.Column("recurrence_rule", sa.String(255)),
        sa.Column("parent_task_id", sa.BigInteger()),
        sa.Column("source", sa.String(32), server_default="TELEGRAM_MANUAL", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_task_id"], ["tasks.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_priority", "tasks", ["priority"])
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"])
    op.create_index("ix_tasks_due_at", "tasks", ["due_at"])
    op.create_index("ix_tasks_deleted_at", "tasks", ["deleted_at"])
    op.create_index("ix_tasks_user_status_due_at", "tasks", ["user_id", "status", "due_at"])
    op.create_index("ix_tasks_user_due_date", "tasks", ["user_id", "due_date"])


def downgrade() -> None:
    op.drop_table("tasks")
