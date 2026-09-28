from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, TypeAdapter

from app.database.models.task import TaskPriority
from app.modules.assistant.actions import AssistantActionType as A


class ActionBase(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    confidence: float = Field(ge=0, le=1)
    requires_confirmation: bool | None = None


class CalendarCreateAction(ActionBase):
    action: Literal[A.CREATE_CALENDAR_EVENT]
    title: str = Field(min_length=1, max_length=200)
    start_at: AwareDatetime
    end_at: AwareDatetime | None = None
    reminder_offsets: list[int] = Field(default_factory=list, max_length=5)
    description: str = Field(default="", max_length=2000)
    location: str = Field(default="", max_length=300)


class CalendarUpdateAction(ActionBase):
    action: Literal[A.UPDATE_CALENDAR_EVENT]
    event_id: str = Field(min_length=1, max_length=1024)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    reminder_offsets: list[int] | None = Field(default=None, max_length=5)


class FreeTimeAction(ActionBase):
    action: Literal[A.GET_FREE_TIME]
    start_at: AwareDatetime
    end_at: AwareDatetime


class ReminderCreateAction(ActionBase):
    action: Literal[A.CREATE_REMINDER]
    message: str = Field(min_length=1, max_length=2000)
    remind_at: AwareDatetime


class FinanceCreateAction(ActionBase):
    action: Literal[A.CREATE_EXPENSE, A.CREATE_INCOME]
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    currency: Literal["UZS", "USD", "EUR"] | None = None
    category: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=2000)
    transaction_date: date


class TaskCreateAction(ActionBase):
    action: Literal[A.CREATE_TASK]
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10_000)
    due_date: date | None = None
    due_at: AwareDatetime | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    reminder_minutes: int | None = Field(default=None, ge=1, le=40320)
    calendar_sync: bool = False


class TaskUpdateAction(ActionBase):
    action: Literal[A.UPDATE_TASK]
    internal_id: int = Field(gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10_000)
    due_date: date | None = None
    due_at: AwareDatetime | None = None
    priority: TaskPriority | None = None
    reminder_enabled: bool | None = None
    reminder_minutes: int | None = Field(default=None, ge=1, le=40320)
    calendar_sync: bool | None = None


class NoteCreateAction(ActionBase):
    action: Literal[A.CREATE_NOTE]
    content: str = Field(min_length=1, max_length=100_000)
    entry_date: date
    project: str | None = Field(default=None, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=20)


class SearchAction(ActionBase):
    action: Literal[A.SEARCH_NOTES, A.SEARCH_EMAILS, A.SEARCH_TELEGRAM]
    query: str = Field(min_length=1, max_length=500)


class TargetAction(ActionBase):
    action: Literal[
        A.DELETE_CALENDAR_EVENT,
        A.CANCEL_REMINDER,
        A.COMPLETE_TASK,
        A.READ_EMAIL,
        A.CREATE_EMAIL_REPLY_DRAFT,
        A.READ_TELEGRAM_MESSAGE,
        A.CREATE_TELEGRAM_REPLY_DRAFT,
    ]
    target_reference: str = Field(min_length=1, max_length=300)
    internal_id: int | None = Field(default=None, gt=0)
    external_id: str | None = Field(default=None, min_length=1, max_length=1024)
    instruction: str | None = Field(default=None, max_length=4000)


class NotesFilterAction(ActionBase):
    action: Literal[A.GET_NOTES_BY_DATE, A.GET_NOTES_BY_PROJECT]
    note_date: date | None = None
    project: str | None = Field(default=None, max_length=80)


class ReadAction(ActionBase):
    action: Literal[
        A.LIST_TODAY_CALENDAR,
        A.LIST_TOMORROW_CALENDAR,
        A.LIST_UPCOMING_CALENDAR,
        A.LIST_REMINDERS,
        A.LIST_TASKS,
        A.LIST_TODAY_TASKS,
        A.LIST_OVERDUE_TASKS,
        A.FINANCE_TODAY,
        A.FINANCE_WEEK,
        A.FINANCE_MONTH,
        A.FINANCE_YEAR,
        A.LIST_TRANSACTIONS,
        A.LIST_RECENT_NOTES,
        A.LIST_RECENT_EMAILS,
        A.LIST_UNREAD_EMAILS,
        A.LIST_RECENT_TELEGRAM,
    ]


class GeneralAction(ActionBase):
    action: Literal[A.GENERAL_QUESTION, A.UNKNOWN]
    response: str = Field(min_length=1, max_length=4000)


AssistantAction = Annotated[
    CalendarCreateAction
    | CalendarUpdateAction
    | FreeTimeAction
    | ReminderCreateAction
    | FinanceCreateAction
    | TaskCreateAction
    | TaskUpdateAction
    | NoteCreateAction
    | SearchAction
    | TargetAction
    | NotesFilterAction
    | ReadAction
    | GeneralAction,
    Field(discriminator="action"),
]
ACTION_ADAPTER = TypeAdapter(AssistantAction)


class AssistantRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    current_datetime: datetime
    timezone: str
    context: list[dict[str, str]] = Field(default_factory=list, max_length=20)


class AssistantClarification(BaseModel):
    needs_clarification: Literal[True] = True
    question: str = Field(min_length=1, max_length=500)


class AssistantExecutionResult(BaseModel):
    success: bool
    message: str
    action_type: A
    reference_id: str | None = None
    data: dict[str, object] = Field(default_factory=dict)


class AssistantRouteResult(BaseModel):
    kind: Literal["executed", "confirmation", "clarification", "answer"]
    message: str
    action_id: str | None = None
    execution: AssistantExecutionResult | None = None
