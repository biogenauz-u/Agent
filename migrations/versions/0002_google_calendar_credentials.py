"""Encrypted owner Calendar refresh credentials; no access token persistence."""

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "google_credentials",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("refresh_token_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "provider", name="uq_google_credentials_owner_provider"),
    )


def downgrade() -> None:
    op.drop_table("google_credentials")
