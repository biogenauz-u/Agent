from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UTCDateTime


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    last_seen_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
