from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

Reminder = Annotated[int, Field(strict=True, ge=1, le=40320)]


class CalendarEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    title: str = Field(min_length=1, max_length=200)
    start: AwareDatetime
    end: AwareDatetime
    description: str = Field(default="", max_length=2000)
    location: str = Field(default="", max_length=300)
    reminders: list[Reminder] = Field(default_factory=lambda: [10], max_length=5)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Title is required")
        return value.strip()

    @field_validator("reminders")
    @classmethod
    def unique_reminders(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate reminders")
        return value

    @model_validator(mode="after")
    def ordered(self) -> "CalendarEventCreate":
        if self.end <= self.start:
            raise ValueError("End must be after start")
        return self


class CalendarEventUpdate(CalendarEventCreate):
    """Complete editable preview; client PATCH preserves all other Google fields."""

    fields: set[Literal["title", "start", "end", "reminders"]] = Field(
        default_factory=lambda: {"title", "start", "end", "reminders"}, min_length=1
    )


class CalendarEventView(BaseModel):
    id: str
    etag: str
    title: str
    start: datetime | date
    end: datetime | date
    all_day: bool = False
    recurring: bool = False
    description: str = ""
    location: str = ""
    reminders: list[int] = Field(default_factory=list)
    reminder_warning: bool = False

    @model_validator(mode="after")
    def valid_times(self) -> "CalendarEventView":
        for value in (self.start, self.end):
            if isinstance(value, datetime):
                if self.all_day or value.tzinfo is None or value.utcoffset() is None:
                    raise ValueError("Timed events must be timezone-aware")
            elif not self.all_day:
                raise ValueError("Timed event requires a datetime")
        if self.end <= self.start:
            raise ValueError("Invalid event time range")
        return self


class TimeInterval(BaseModel):
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def ordered(self) -> "TimeInterval":
        if self.end <= self.start:
            raise ValueError("End must be after start")
        return self


class FreeBusyResult(BaseModel):
    busy: list[TimeInterval]
    free: list[TimeInterval]
