"""Encrypted personal Telegram session, message index, and reply drafts."""

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str = "0004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    direction = sa.Enum(
        "INCOMING", "OUTGOING", name="telegrammessagedirection", native_enum=False, length=16
    )
    draft_status = sa.Enum(
        "DRAFT",
        "SENDING",
        "SENT",
        "CANCELLED",
        "FAILED",
        name="telegramdraftstatus",
        native_enum=False,
        length=16,
    )
    op.create_table(
        "telegram_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("encrypted_session", sa.LargeBinary(), nullable=False),
        sa.Column("phone_hint", sa.String(32)),
        sa.Column("telegram_account_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_connected_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_telegram_sessions_user_id"),
    )
    op.create_table(
        "telegram_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("peer_id", sa.BigInteger(), nullable=False),
        sa.Column("peer_type", sa.String(20), nullable=False),
        sa.Column("sender_id", sa.BigInteger()),
        sa.Column("sender_username", sa.String(64)),
        sa.Column("sender_display_name", sa.String(255), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("direction", direction, nullable=False),
        sa.Column("text_encrypted", sa.LargeBinary()),
        sa.Column("message_preview", sa.String(280), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reply_to_message_id", sa.BigInteger()),
        sa.Column("has_media", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("media_type", sa.String(32)),
        sa.Column("is_processed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("notified_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "telegram_chat_id",
            "telegram_message_id",
            name="uq_telegram_messages_chat_message",
        ),
    )
    op.create_index("ix_telegram_messages_peer_id", "telegram_messages", ["peer_id"])
    op.create_index("ix_telegram_messages_received_at", "telegram_messages", ["received_at"])
    op.create_index(
        "ix_telegram_messages_user_received", "telegram_messages", ["user_id", "received_at"]
    )
    op.create_index(
        "ix_telegram_messages_peer_received", "telegram_messages", ["peer_id", "received_at"]
    )
    op.create_table(
        "telegram_reply_drafts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("target_message_id", sa.BigInteger(), nullable=False),
        sa.Column("target_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("reply_to_message_id", sa.BigInteger(), nullable=False),
        sa.Column("draft_text_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("status", draft_status, server_default="DRAFT", nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.String(120)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["target_message_id"], ["telegram_messages.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_telegram_reply_drafts_status", "telegram_reply_drafts", ["status"]
    )
    op.create_index(
        "ix_telegram_reply_drafts_user_status",
        "telegram_reply_drafts",
        ["user_id", "status"],
    )


def downgrade() -> None:
    op.drop_table("telegram_reply_drafts")
    op.drop_table("telegram_messages")
    op.drop_table("telegram_sessions")
