"""Encrypted notebook entries, projects, tags, and attachments."""

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str = "0006"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "notebook_projects",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "slug", name="uq_notebook_projects_user_slug"),
    )
    op.create_index("ix_notebook_projects_user_id", "notebook_projects", ["user_id"])
    op.create_table(
        "notebook_tags",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "slug", name="uq_notebook_tags_user_slug"),
    )
    op.create_index("ix_notebook_tags_user_id", "notebook_tags", ["user_id"])
    op.create_table(
        "notebook_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(200)),
        sa.Column("content_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("project_id", sa.BigInteger()),
        sa.Column("source", sa.String(32), server_default="TELEGRAM_MANUAL", nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["notebook_projects.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_notebook_entries_user_id", "notebook_entries", ["user_id"])
    op.create_index("ix_notebook_entries_entry_date", "notebook_entries", ["entry_date"])
    op.create_index("ix_notebook_entries_project_id", "notebook_entries", ["project_id"])
    op.create_index("ix_notebook_entries_user_date", "notebook_entries", ["user_id", "entry_date"])
    op.create_index("ix_notebook_entries_user_created", "notebook_entries", ["user_id", "created_at"])
    op.create_table(
        "notebook_entry_tags",
        sa.Column("entry_id", sa.BigInteger(), primary_key=True),
        sa.Column("tag_id", sa.BigInteger(), primary_key=True),
        sa.ForeignKeyConstraint(["entry_id"], ["notebook_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["notebook_tags.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "notebook_attachments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("entry_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("storage_name", sa.String(64)),
        sa.Column("mime_type", sa.String(255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("encrypted_path", sa.String(500)),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("telegram_file_id", sa.String(512)),
        sa.Column("telegram_file_unique_id", sa.String(255)),
        sa.Column("link_encrypted", sa.LargeBinary()),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["entry_id"], ["notebook_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("entry_id", "checksum", name="uq_notebook_attachments_entry_checksum"),
    )
    op.create_index("ix_notebook_attachments_entry_id", "notebook_attachments", ["entry_id"])
    op.create_index("ix_notebook_attachments_user_id", "notebook_attachments", ["user_id"])
    op.create_index("ix_notebook_attachments_checksum", "notebook_attachments", ["checksum"])


def downgrade() -> None:
    op.drop_table("notebook_attachments")
    op.drop_table("notebook_entry_tags")
    op.drop_table("notebook_entries")
    op.drop_table("notebook_tags")
    op.drop_table("notebook_projects")
