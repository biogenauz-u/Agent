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
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UTCDateTime


class NotebookSource(StrEnum):
    TELEGRAM_MANUAL = "TELEGRAM_MANUAL"


class AttachmentType(StrEnum):
    TEXT = "TEXT"
    VOICE = "VOICE"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    PDF = "PDF"
    WORD = "WORD"
    EXCEL = "EXCEL"
    DOCUMENT = "DOCUMENT"
    TELEGRAM_FILE = "TELEGRAM_FILE"
    LINK = "LINK"
    OTHER = "OTHER"


class NotebookProject(TimestampMixin, Base):
    __tablename__ = "notebook_projects"
    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_notebook_projects_user_slug"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class NotebookTag(Base):
    __tablename__ = "notebook_tags"
    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_notebook_tags_user_slug"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class NotebookEntryTag(Base):
    __tablename__ = "notebook_entry_tags"

    entry_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("notebook_entries.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("notebook_tags.id", ondelete="CASCADE"), primary_key=True
    )


class NotebookEntry(TimestampMixin, Base):
    __tablename__ = "notebook_entries"
    __table_args__ = (
        Index("ix_notebook_entries_user_date", "user_id", "entry_date"),
        Index("ix_notebook_entries_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    content_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    project_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("notebook_projects.id", ondelete="RESTRICT"), index=True
    )
    source: Mapped[NotebookSource] = mapped_column(
        Enum(NotebookSource, native_enum=False, length=32),
        default=NotebookSource.TELEGRAM_MANUAL,
        server_default=NotebookSource.TELEGRAM_MANUAL.value,
    )
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    project: Mapped[NotebookProject | None] = relationship(lazy="joined")
    tags: Mapped[list[NotebookTag]] = relationship(secondary="notebook_entry_tags", lazy="selectin")
    attachments: Mapped[list["NotebookAttachment"]] = relationship(lazy="selectin")


class NotebookAttachment(Base):
    __tablename__ = "notebook_attachments"
    __table_args__ = (
        UniqueConstraint("entry_id", "checksum", name="uq_notebook_attachments_entry_checksum"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("notebook_entries.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    storage_name: Mapped[str | None] = mapped_column(String(64))
    mime_type: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(BigInteger)
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    encrypted_path: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[AttachmentType] = mapped_column(Enum(AttachmentType, native_enum=False, length=32))
    telegram_file_id: Mapped[str | None] = mapped_column(String(512))
    telegram_file_unique_id: Mapped[str | None] = mapped_column(String(255))
    link_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
