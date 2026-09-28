from datetime import datetime

from sqlalchemy import JSON, BigInteger, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[str | None] = mapped_column(String(255))
    details: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict, server_default="{}"
    )
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now(), index=True
    )
