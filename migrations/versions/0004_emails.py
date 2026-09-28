"""Encrypted Gmail index and persistent monitor state."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str = "0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "emails",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("gmail_message_id", sa.String(255), nullable=False),
        sa.Column("gmail_thread_id", sa.String(255), nullable=False),
        sa.Column("history_id", sa.String(255)),
        sa.Column("from_address", sa.String(320), nullable=False),
        sa.Column("from_name", sa.String(255)),
        sa.Column("to_addresses", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cc_addresses", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attachments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("has_attachments", sa.Boolean(), nullable=False),
        sa.Column("is_unread", sa.Boolean(), nullable=False),
        sa.Column("is_important", sa.Boolean(), nullable=False),
        sa.Column("body_text_encrypted", sa.LargeBinary()),
        sa.Column("summary_encrypted", sa.LargeBinary()),
        sa.Column("body_hash", sa.String(64)),
        sa.Column("notified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("gmail_message_id", name="uq_emails_gmail_message_id"),
    )
    op.create_index("ix_emails_gmail_message_id", "emails", ["gmail_message_id"])
    op.create_index("ix_emails_gmail_thread_id", "emails", ["gmail_thread_id"])
    op.create_index("ix_emails_received_at", "emails", ["received_at"])
    op.create_index("ix_emails_is_unread", "emails", ["is_unread"])
    op.create_index("ix_emails_user_received_at", "emails", ["user_id", "received_at"])
    op.create_table(
        "integration_states",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("uq_integration_states_owner_provider_key", "integration_states", ["user_id", "provider", "key"], unique=True)


def downgrade() -> None:
    op.drop_table("integration_states")
    op.drop_table("emails")
