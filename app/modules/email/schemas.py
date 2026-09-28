from datetime import datetime

from pydantic import BaseModel, Field

from app.database.models.email import EmailDraftStatus


class AttachmentMetadata(BaseModel):
    filename: str
    mime_type: str
    size: int = 0
    attachment_id: str | None = None


class EmailContent(BaseModel):
    """Normalized untrusted external data; it must never authorize tools or actions."""

    gmail_message_id: str
    gmail_thread_id: str
    history_id: str | None = None
    from_address: str = ""
    from_name: str | None = None
    to_addresses: list[str] = Field(default_factory=list)
    cc_addresses: list[str] = Field(default_factory=list)
    subject: str = "(No subject)"
    snippet: str = ""
    received_at: datetime
    labels: list[str] = Field(default_factory=list)
    body_text: str = ""
    attachments: list[AttachmentMetadata] = Field(default_factory=list)

    @property
    def is_unread(self) -> bool:
        return "UNREAD" in self.labels

    @property
    def is_important(self) -> bool:
        return "IMPORTANT" in self.labels


class EmailView(BaseModel):
    id: int
    gmail_message_id: str
    from_address: str
    from_name: str | None
    subject: str
    snippet: str
    received_at: datetime
    is_unread: bool
    is_important: bool
    has_attachments: bool
    attachment_count: int
    summary: str
    body_text: str = ""


class EmailReplyDraftView(BaseModel):
    id: int
    email_id: int
    recipient: str
    subject: str
    body: str
    status: EmailDraftStatus
