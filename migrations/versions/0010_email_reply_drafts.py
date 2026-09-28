"""Encrypted owner-confirmed Gmail reply drafts."""

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str = "0009"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    status = sa.Enum(
        "DRAFT",
        "SENDING",
        "SENT",
        "CANCELLED",
        "FAILED",
        name="emaildraftstatus",
        native_enum=False,
        length=16,
    )
    op.create_table(
        "email_reply_drafts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("email_id", sa.BigInteger(), nullable=False),
        sa.Column("recipient_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("subject_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("body_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("status", status, server_default="DRAFT", nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("gmail_sent_message_id", sa.String(255)),
        sa.Column("failure_reason", sa.String(120)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["email_id"], ["emails.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_email_reply_drafts_user_status", "email_reply_drafts", ["user_id", "status"]
    )
    op.create_index("ix_email_reply_drafts_status", "email_reply_drafts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_email_reply_drafts_status", table_name="email_reply_drafts")
    op.drop_index("ix_email_reply_drafts_user_status", table_name="email_reply_drafts")
    op.drop_table("email_reply_drafts")
