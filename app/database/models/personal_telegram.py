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
    UniqueConstraint,
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UTCDateTime


class TelegramMessageDirection(StrEnum):
    INCOMING = "INCOMING"
    OUTGOING = "OUTGOING"


class TelegramDraftStatus(StrEnum):
    DRAFT = "DRAFT"
    SENDING = "SENDING"
    SENT = "SENT"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class PersonalTelegramSession(TimestampMixin, Base):
    """One encrypted Telethon StringSession per owner."""

    __tablename__ = "telegram_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_telegram_sessions_user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    encrypted_session: Mapped[bytes] = mapped_column(LargeBinary)
    phone_hint: Mapped[str | None] = mapped_column(String(32))
    telegram_account_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    last_connected_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class PersonalTelegramMessage(TimestampMixin, Base):
    """Privacy-minimized local index; message text is encrypted at rest."""

    __tablename__ = "telegram_messages"
    __table_args__ = (
        UniqueConstraint(
            "telegram_chat_id",
            "telegram_message_id",
            name="uq_telegram_messages_chat_message",
        ),
        Index("ix_telegram_messages_user_received", "user_id", "received_at"),
        Index("ix_telegram_messages_peer_received", "peer_id", "received_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    peer_id: Mapped[int] = mapped_column(BigInteger, index=True)
    peer_type: Mapped[str] = mapped_column(String(20))
    sender_id: Mapped[int | None] = mapped_column(BigInteger)
    sender_username: Mapped[str | None] = mapped_column(String(64))
    sender_display_name: Mapped[str] = mapped_column(String(255), default="Unknown")
    telegram_message_id: Mapped[int] = mapped_column(BigInteger)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger)
    direction: Mapped[TelegramMessageDirection] = mapped_column(
        Enum(TelegramMessageDirection, native_enum=False, length=16)
    )
    text_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    message_preview: Mapped[str] = mapped_column(String(280), default="")
    received_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    reply_to_message_id: Mapped[int | None] = mapped_column(BigInteger)
    has_media: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    media_type: Mapped[str | None] = mapped_column(String(32))
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    notified_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class PersonalTelegramReplyDraft(TimestampMixin, Base):
    __tablename__ = "telegram_reply_drafts"
    __table_args__ = (
        Index("ix_telegram_reply_drafts_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    target_message_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("telegram_messages.id", ondelete="CASCADE")
    )
    target_chat_id: Mapped[int] = mapped_column(BigInteger)
    reply_to_message_id: Mapped[int] = mapped_column(BigInteger)
    draft_text_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    status: Mapped[TelegramDraftStatus] = mapped_column(
        Enum(TelegramDraftStatus, native_enum=False, length=16),
        default=TelegramDraftStatus.DRAFT,
        server_default=TelegramDraftStatus.DRAFT.value,
        index=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    failure_reason: Mapped[str | None] = mapped_column(String(120))
