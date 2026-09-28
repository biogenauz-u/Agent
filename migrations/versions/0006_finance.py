"""Finance categories and Decimal transactions."""

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str = "0005"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    category_type = sa.Enum(
        "EXPENSE", "INCOME", "BOTH", name="financecategorytype", native_enum=False, length=16
    )
    transaction_type = sa.Enum(
        "EXPENSE", "INCOME", name="financetransactiontype", native_enum=False, length=16
    )
    source = sa.Enum(
        "TELEGRAM_MANUAL", name="financesource", native_enum=False, length=32
    )
    op.create_table(
        "finance_categories",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("transaction_type", category_type, nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "slug", name="uq_finance_categories_user_slug"),
    )
    op.create_table(
        "finance_transactions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("transaction_type", transaction_type, nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(20, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("source", source, server_default="TELEGRAM_MANUAL", nullable=False),
        sa.Column("external_reference", sa.String(255)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount > 0", name="ck_finance_transactions_amount_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["category_id"], ["finance_categories.id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "ix_finance_transactions_transaction_type",
        "finance_transactions",
        ["transaction_type"],
    )
    op.create_index(
        "ix_finance_transactions_category_id", "finance_transactions", ["category_id"]
    )
    op.create_index("ix_finance_transactions_currency", "finance_transactions", ["currency"])
    op.create_index(
        "ix_finance_transactions_transaction_date",
        "finance_transactions",
        ["transaction_date"],
    )
    op.create_index(
        "ix_finance_transactions_user_date",
        "finance_transactions",
        ["user_id", "transaction_date"],
    )
    op.create_index(
        "ix_finance_transactions_user_type_date",
        "finance_transactions",
        ["user_id", "transaction_type", "transaction_date"],
    )


def downgrade() -> None:
    op.drop_table("finance_transactions")
    op.drop_table("finance_categories")
