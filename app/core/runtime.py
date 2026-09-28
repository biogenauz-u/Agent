from dataclasses import dataclass
from typing import Literal

type TelegramState = Literal["not_configured", "configured", "running", "stopped", "error"]
type SchedulerState = Literal["disabled", "running", "stopped", "error"]
type GmailState = Literal["not_configured", "not_connected", "connected", "monitoring", "stopped", "error", "disabled"]
type PersonalTelegramState = Literal[
    "not_configured", "not_connected", "connected", "monitoring", "stopped", "error", "disabled"
]
type NotebookState = Literal["not_configured", "available", "unavailable", "error"]
type DailyState = Literal["disabled", "running", "stopped", "error"]


@dataclass
class RuntimeState:
    startup_complete: bool = False
    telegram: TelegramState = "not_configured"
    telegram_required: bool = False
    reminder_scheduler: SchedulerState = "disabled"
    reminder_scheduler_required: bool = False
    gmail: GmailState = "disabled"
    personal_telegram: PersonalTelegramState = "disabled"
    notebook_storage: NotebookState = "not_configured"
    daily_automation: DailyState = "disabled"
