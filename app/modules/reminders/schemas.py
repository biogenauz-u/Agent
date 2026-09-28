from datetime import UTC, datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.database.models.reminder import ReminderChannel, ReminderStatus

Offset = Annotated[int, Field(strict=True, ge=1, le=40320)]


class ReminderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    title: str = Field(min_length=1, max_length=200)
    message: str | None = Field(default=None, max_length=2000)
    remind_at: AwareDatetime

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Reminder text is required")
        return value.strip()


class CalendarReminderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    external_calendar_event_id: str = Field(min_length=1, max_length=1024)
    title: str = Field(min_length=1, max_length=200)
    event_start_at: AwareDatetime
    offsets: list[Offset] = Field(default_factory=lambda: [10], min_length=1, max_length=5)

    @field_validator("offsets")
    @classmethod
    def unique_offsets(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate reminder offsets")
        return value


class ReminderView(BaseModel):
    id: int
    title: str
    message: str | None
    remind_at: datetime
    event_start_at: datetime | None
    offset_minutes: int | None
    status: ReminderStatus
    channel: ReminderChannel
    attempt_count: int
    max_attempts: int
    external_calendar_event_id: str | None

    @field_validator("remind_at", "event_start_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Timezone-aware datetime required")
        return value.astimezone(UTC) if value else None


class ReminderDeliveryResult(BaseModel):
    success: bool
    failure_reason: str | None = None
