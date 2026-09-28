from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.database.models.notebook import AttachmentType, NotebookSource


class NoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    title: str | None = Field(default=None, max_length=200)
    entry_date: date
    project_id: int | None = Field(default=None, gt=0)
    tags: list[str] = Field(default_factory=list, max_length=20)
    source: NotebookSource = NotebookSource.TELEGRAM_MANUAL
    is_pinned: bool = False


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=100_000)
    entry_date: date | None = None
    project_id: int | None = Field(default=None, gt=0)
    tags: list[str] | None = Field(default=None, max_length=20)
    is_pinned: bool | None = None


class ProjectView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    description: str | None
    is_active: bool


class TagView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str


class AttachmentView(BaseModel):
    id: int
    original_name: str
    mime_type: str
    file_size: int
    checksum: str
    source_type: AttachmentType
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None


class NoteView(BaseModel):
    id: int
    title: str | None
    content: str
    entry_date: date
    project: ProjectView | None
    tags: list[TagView]
    attachments: list[AttachmentView]
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


class AttachmentInput(BaseModel):
    original_name: str
    mime_type: str = "application/octet-stream"
    source_type: AttachmentType
    telegram_file_id: str | None = None
    telegram_file_unique_id: str | None = None
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None

