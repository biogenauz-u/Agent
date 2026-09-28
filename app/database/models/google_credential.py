from sqlalchemy import BigInteger, ForeignKey, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class GoogleCredential(TimestampMixin, Base):
    """Persist only the encrypted refresh token; access tokens remain in memory."""

    __tablename__ = "google_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_google_credentials_owner_provider"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(32), default="google_calendar")
    refresh_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
