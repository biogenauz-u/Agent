from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database.base import Base, TimestampMixin, UTCDateTime

JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class EmailDraftStatus(StrEnum):
    DRAFT = "DRAFT"
    SENDING = "SENDING"
    SENT = "SENT"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class EmailMessage(TimestampMixin, Base):
    __tablename__ = "emails"
    __table_args__ = (
        Index("ix_emails_user_received_at", "user_id", "received_at"),
        Index("ix_emails_gmail_thread_id", "gmail_thread_id"),
        Index("ix_emails_is_unread", "is_unread"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    gmail_message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    gmail_thread_id: Mapped[str] = mapped_column(String(255))
    history_id: Mapped[str | None] = mapped_column(String(255))
    from_address: Mapped[str] = mapped_column(String(320), default="")
    from_name: Mapped[str | None] = mapped_column(String(255))
    to_addresses: Mapped[list[str]] = mapped_column(JSON_TYPE, default=list)
    cc_addresses: Mapped[list[str]] = mapped_column(JSON_TYPE, default=list)
    subject: Mapped[str] = mapped_column(Text, default="(No subject)")
    snippet: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    labels: Mapped[list[str]] = mapped_column(JSON_TYPE, default=list)
    attachments: Mapped[list[dict[str, object]]] = mapped_column(JSON_TYPE, default=list)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    is_unread: Mapped[bool] = mapped_column(Boolean, default=False)
    is_important: Mapped[bool] = mapped_column(Boolean, default=False)
    body_text_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    summary_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    body_hash: Mapped[str | None] = mapped_column(String(64))
    notified_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class IntegrationState(TimestampMixin, Base):
    __tablename__ = "integration_states"
    __table_args__ = (
        Index(
            "uq_integration_states_owner_provider_key", "user_id", "provider", "key", unique=True
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(64))
    key: Mapped[str] = mapped_column(String(128))
    value: Mapped[str] = mapped_column(Text)


class EmailReplyDraft(TimestampMixin, Base):
    __tablename__ = "email_reply_drafts"
    __table_args__ = (Index("ix_email_reply_drafts_user_status", "user_id", "status"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    email_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("emails.id", ondelete="CASCADE"))
    recipient_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    subject_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    body_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    status: Mapped[EmailDraftStatus] = mapped_column(
        Enum(EmailDraftStatus, native_enum=False, length=16),
        default=EmailDraftStatus.DRAFT,
        server_default=EmailDraftStatus.DRAFT.value,
        index=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    gmail_sent_message_id: Mapped[str | None] = mapped_column(String(255))
    failure_reason: Mapped[str | None] = mapped_column(String(120))
