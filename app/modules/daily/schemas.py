from datetime import date, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DailySettingsView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    morning_enabled: bool
    morning_time: time
    evening_enabled: bool
    evening_time: time


class Section(BaseModel):
    status: Literal["available", "unavailable", "not_configured"] = "available"
    count: int = 0
    details: list[str] = Field(default_factory=list)


class FinanceLine(BaseModel):
    currency: str
    income: Decimal = Decimal(0)
    expense: Decimal = Decimal(0)


class MorningBriefingData(BaseModel):
    day: date
    calendar: Section
    tasks: Section
    email: Section
    reminders: Section
    finance: Section
    notebook: Section
    personal_telegram: Section
    finance_lines: list[FinanceLine] = Field(default_factory=list)


class EveningSummaryData(BaseModel):
    day: date
    tasks: Section
    calendar: Section
    finance: Section
    email: Section
    notebook: Section
    personal_telegram: Section
    unfinished_task_ids: list[int] = Field(default_factory=list)
    finance_lines: list[FinanceLine] = Field(default_factory=list)
