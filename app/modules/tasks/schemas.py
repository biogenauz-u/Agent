from datetime import date, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.database.models.task import TaskPriority, TaskSource, TaskStatus


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10_000)
    priority: TaskPriority = TaskPriority.NORMAL
    due_date: date | None = None
    due_at: AwareDatetime | None = None
    reminder_enabled: bool = False
    reminder_offset_minutes: int | None = Field(default=None, ge=1, le=40320)
    calendar_sync: bool = False
    source: TaskSource = TaskSource.TELEGRAM_MANUAL

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Task title is required")
        return value

    @model_validator(mode="after")
    def consistent_due(self) -> "TaskCreate":
        if self.reminder_enabled and not (self.due_date or self.due_at):
            raise ValueError("Reminder requires a due date")
        if self.calendar_sync and not self.due_at:
            raise ValueError("Calendar sync currently requires a due time")
        return self


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10_000)
    priority: TaskPriority | None = None
    due_date: date | None = None
    due_at: AwareDatetime | None = None
    reminder_enabled: bool | None = None
    reminder_offset_minutes: int | None = Field(default=None, ge=1, le=40320)
    calendar_sync: bool | None = None
    status: TaskStatus | None = None

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        if not value:
            raise ValueError("Task title is required")
        return value


class TaskView(BaseModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    due_at: datetime | None
    completed_at: datetime | None
    reminder_enabled: bool
    reminder_offset_minutes: int | None
    calendar_linked: bool
    created_at: datetime
    warnings: list[str] = Field(default_factory=list)


class TaskDailySummary(BaseModel):
    total: int
    done: int
    remaining: int
    overdue: int
    urgent: int
