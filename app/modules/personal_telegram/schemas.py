from datetime import datetime

from pydantic import BaseModel, Field

from app.database.models.personal_telegram import TelegramDraftStatus, TelegramMessageDirection


class PersonalAccount(BaseModel):
    id: int
    username: str | None = None


class IncomingTelegramMessage(BaseModel):
    """Untrusted external DATA; it cannot authorize tools or message sending."""

    peer_id: int
    peer_type: str = "private"
    sender_id: int | None = None
    sender_username: str | None = None
    sender_display_name: str = "Unknown"
    telegram_message_id: int
    telegram_chat_id: int
    direction: TelegramMessageDirection = TelegramMessageDirection.INCOMING
    text: str = ""
    received_at: datetime
    reply_to_message_id: int | None = None
    has_media: bool = False
    media_type: str | None = None
    is_private: bool = True
    sender_is_bot: bool = False


class PersonalTelegramMessageView(BaseModel):
    id: int
    peer_id: int
    sender_id: int | None
    sender_username: str | None = None
    sender_display_name: str
    telegram_message_id: int
    telegram_chat_id: int
    direction: TelegramMessageDirection
    preview: str
    text: str = ""
    received_at: datetime
    has_media: bool
    media_type: str | None = None


class TelegramReplyDraftView(BaseModel):
    id: int
    target_message_id: int
    target_chat_id: int
    reply_to_message_id: int
    text: str
    status: TelegramDraftStatus


class LoginResult(BaseModel):
    password_required: bool = False
    connected: bool = False


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=20)
