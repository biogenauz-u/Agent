from datetime import timedelta

from app.database.models.finance import FinanceTransactionType
from app.modules.assistant.actions import AssistantActionType as A
from app.modules.assistant.exceptions import AssistantValidationError
from app.modules.assistant.schemas import (
    AssistantAction,
    AssistantExecutionResult,
    CalendarCreateAction,
    CalendarUpdateAction,
    FinanceCreateAction,
    FreeTimeAction,
    NoteCreateAction,
    NotesFilterAction,
    SearchAction,
    TargetAction,
    TaskCreateAction,
    TaskUpdateAction,
)
from app.modules.calendar.schemas import CalendarEventCreate, CalendarEventUpdate, TimeInterval
from app.modules.finance.schemas import FinanceTransactionCreate
from app.modules.notebook.schemas import NoteCreate
from app.modules.reminders.schemas import ReminderCreate
from app.modules.tasks.schemas import TaskCreate, TaskUpdate


class AssistantActionExecutor:
    """Allowlisted service calls only; no DB, filesystem, shell, or provider access."""

    def __init__(self, context) -> None:
        self.context = context

    def result(self, action: AssistantAction, message: str, reference=None, data=None):
        return AssistantExecutionResult(
            success=True,
            message=message,
            action_type=action.action,
            reference_id=str(reference) if reference is not None else None,
            data=data or {},
        )

    async def execute(self, action: AssistantAction) -> AssistantExecutionResult:
        a = action.action
        if a == A.GENERAL_QUESTION:
            return self.result(action, action.response)  # type: ignore[attr-defined]
        if a == A.CREATE_CALENDAR_EVENT and isinstance(action, CalendarCreateAction):
            runtime = self._required("calendar")
            end = action.end_at or action.start_at + timedelta(
                minutes=runtime.settings.calendar_default_event_duration_minutes
            )
            row = await runtime.service.create_event(
                CalendarEventCreate(
                    title=action.title,
                    start=action.start_at,
                    end=end,
                    description=action.description,
                    location=action.location,
                    reminders=action.reminder_offsets,
                )
            )
            return self.result(action, "Calendar event yaratildi.", row.id)
        if a in {A.LIST_TODAY_CALENDAR, A.LIST_TOMORROW_CALENDAR, A.LIST_UPCOMING_CALENDAR}:
            service = self._required("calendar").service
            rows = await (
                service.get_today_events() if a == A.LIST_TODAY_CALENDAR else
                service.get_tomorrow_events() if a == A.LIST_TOMORROW_CALENDAR else
                service.list_upcoming_events()
            )
            return self.result(action, self._lines(rows))
        if a == A.UPDATE_CALENDAR_EVENT and isinstance(action, CalendarUpdateAction):
            service = self._required("calendar").service
            current = await service.get_event(action.event_id)
            fields = {
                name
                for name, value in {
                    "title": action.title,
                    "start": action.start_at,
                    "end": action.end_at,
                    "reminders": action.reminder_offsets,
                }.items()
                if value is not None
            }
            if not fields:
                raise AssistantValidationError("Calendar update has no changes.")
            row = await service.update_event(
                action.event_id,
                CalendarEventUpdate(
                    title=action.title or current.title,
                    start=action.start_at or current.start,
                    end=action.end_at or current.end,
                    description=current.description,
                    location=current.location,
                    reminders=(
                        action.reminder_offsets
                        if action.reminder_offsets is not None
                        else current.reminders
                    ),
                    fields=fields,
                ),
                current.etag,
            )
            return self.result(action, "Calendar event yangilandi.", row.id)
        if a == A.DELETE_CALENDAR_EVENT and isinstance(action, TargetAction):
            event_id = action.external_id or action.target_reference
            service = self._required("calendar").service
            current = await service.get_event(event_id)
            await service.delete_event(event_id, current.etag)
            return self.result(action, "Calendar event o'chirildi.", event_id)
        if a == A.GET_FREE_TIME and isinstance(action, FreeTimeAction):
            result = await self._required("calendar").service.get_free_busy(
                TimeInterval(start=action.start_at, end=action.end_at)
            )
            return self.result(action, self._lines(result.free))
        if a == A.CREATE_REMINDER:
            runtime = self._required("reminders")
            row = await runtime.service.create_standalone(
                ReminderCreate(title=action.message, remind_at=action.remind_at)  # type: ignore[attr-defined]
            )
            return self.result(action, "Reminder yaratildi.", row.id)
        if a == A.LIST_REMINDERS:
            return self.result(action, self._lines(await self._required("reminders").service.list_upcoming()))
        if a == A.CANCEL_REMINDER and isinstance(action, TargetAction):
            await self._required("reminders").service.cancel(self._id(action))
            return self.result(action, "Reminder bekor qilindi.")
        if a == A.CREATE_TASK and isinstance(action, TaskCreateAction):
            row = await self._required("tasks").service.create_task(
                TaskCreate(
                    title=action.title,
                    description=action.description,
                    due_date=action.due_date,
                    due_at=action.due_at,
                    priority=action.priority,
                    reminder_enabled=action.reminder_minutes is not None,
                    reminder_offset_minutes=action.reminder_minutes,
                    calendar_sync=action.calendar_sync,
                )
            )
            return self.result(action, "Task yaratildi.", row.id)
        if a in {A.LIST_TASKS, A.LIST_TODAY_TASKS, A.LIST_OVERDUE_TASKS}:
            service = self._required("tasks").service
            rows = await (
                service.today() if a == A.LIST_TODAY_TASKS else
                service.overdue() if a == A.LIST_OVERDUE_TASKS else service.list_tasks()
            )
            return self.result(action, self._lines(rows))
        if a == A.COMPLETE_TASK and isinstance(action, TargetAction):
            row = await self._required("tasks").service.complete_task(self._id(action))
            return self.result(action, "Task bajarildi.", row.id)
        if a == A.UPDATE_TASK and isinstance(action, TaskUpdateAction):
            values = action.model_dump(
                exclude={"action", "confidence", "requires_confirmation", "internal_id"},
                exclude_none=True,
            )
            if "reminder_minutes" in values:
                values["reminder_offset_minutes"] = values.pop("reminder_minutes")
            if not values:
                raise AssistantValidationError("Task update has no changes.")
            row = await self._required("tasks").service.update_task(
                action.internal_id, TaskUpdate.model_validate(values)
            )
            return self.result(action, "Task yangilandi.", row.id)
        if a in {A.CREATE_EXPENSE, A.CREATE_INCOME} and isinstance(action, FinanceCreateAction):
            service = self._required("finance").service
            categories = await service.list_categories(
                FinanceTransactionType.EXPENSE if a == A.CREATE_EXPENSE else FinanceTransactionType.INCOME
            )
            category = next((item for item in categories if action.category.casefold() in {item.name.casefold(), item.slug.casefold()}), None)
            if category is None:
                raise AssistantValidationError("Finance category requires clarification.")
            row = await service.create_transaction(
                FinanceTransactionCreate(
                    transaction_type=FinanceTransactionType.EXPENSE if a == A.CREATE_EXPENSE else FinanceTransactionType.INCOME,
                    category_id=category.id,
                    amount=action.amount,
                    currency=action.currency or self._required("finance").settings.finance_default_currency,
                    description=action.description,
                    transaction_date=action.transaction_date,
                )
            )
            return self.result(action, "Finance operatsiyasi saqlandi.", row.id)
        if a in {A.FINANCE_TODAY, A.FINANCE_WEEK, A.FINANCE_MONTH, A.FINANCE_YEAR}:
            period = {A.FINANCE_TODAY: "today", A.FINANCE_WEEK: "week", A.FINANCE_MONTH: "month", A.FINANCE_YEAR: "year"}[a]
            report = await self._required("finance").service.reports.report(period)
            return self.result(action, str(report.model_dump(mode="json")))
        if a == A.LIST_TRANSACTIONS:
            return self.result(action, self._lines(await self._required("finance").service.list_recent()))
        if a == A.CREATE_NOTE and isinstance(action, NoteCreateAction):
            service = self._required("notebook").service
            project_id = None
            if action.project:
                projects = await service.projects()
                project = next((item for item in projects if action.project.casefold() in {item.name.casefold(), item.slug.casefold()}), None)
                if project is None:
                    raise AssistantValidationError("Notebook project requires clarification.")
                project_id = project.id
            row = await service.create_note(NoteCreate(content=action.content, entry_date=action.entry_date, project_id=project_id, tags=action.tags))
            return self.result(action, "Notebook yozuvi saqlandi.", row.id)
        if a == A.SEARCH_NOTES and isinstance(action, SearchAction):
            return self.result(action, self._lines(await self._required("notebook").service.search(action.query)))
        if a == A.LIST_RECENT_NOTES:
            return self.result(action, self._lines(await self._required("notebook").service.recent()))
        if a in {A.GET_NOTES_BY_DATE, A.GET_NOTES_BY_PROJECT} and isinstance(
            action, NotesFilterAction
        ):
            service = self._required("notebook").service
            project_id = None
            if a == A.GET_NOTES_BY_PROJECT:
                if not action.project:
                    raise AssistantValidationError("Notebook project is required.")
                projects = await service.projects()
                project = next(
                    (
                        item
                        for item in projects
                        if action.project.casefold()
                        in {item.name.casefold(), item.slug.casefold()}
                    ),
                    None,
                )
                if project is None:
                    raise AssistantValidationError("Notebook project requires clarification.")
                project_id = project.id
            rows = await service.recent(entry_date=action.note_date, project_id=project_id)
            return self.result(action, self._lines(rows))
        if a in {A.LIST_RECENT_EMAILS, A.LIST_UNREAD_EMAILS}:
            rows = await self._required("email").service.list_recent(unread_only=a == A.LIST_UNREAD_EMAILS)
            return self.result(action, self._lines(rows))
        if a == A.SEARCH_EMAILS and isinstance(action, SearchAction):
            return self.result(action, self._lines(await self._required("email").service.search(action.query)))
        if a == A.READ_EMAIL and isinstance(action, TargetAction):
            return self.result(action, str(await self._required("email").service.read(self._id(action))))
        if a == A.CREATE_EMAIL_REPLY_DRAFT and isinstance(action, TargetAction):
            draft = await self._required("email").drafts.create(
                self._id(action), action.instruction or ""
            )
            return self.result(action, f"Draft:\n{draft}\n\nEmail yuborilmadi.")
        if a == A.LIST_RECENT_TELEGRAM:
            return self.result(action, self._lines(await self._required("personal_telegram").service.list_recent()))
        if a == A.SEARCH_TELEGRAM and isinstance(action, SearchAction):
            return self.result(action, self._lines(await self._required("personal_telegram").service.search(action.query)))
        if a == A.READ_TELEGRAM_MESSAGE and isinstance(action, TargetAction):
            return self.result(action, str(await self._required("personal_telegram").service.read(self._id(action))))
        if a == A.CREATE_TELEGRAM_REPLY_DRAFT and isinstance(action, TargetAction):
            row = await self._required("personal_telegram").service.create_draft(self._id(action), action.instruction or "")
            return self.result(action, "Telegram reply draft yaratildi; yuborilmadi.", row.id)
        raise AssistantValidationError("Action needs clarification or is not executable.")

    def _required(self, name: str):
        value = getattr(self.context, name, None)
        if value is None:
            raise AssistantValidationError(f"{name} service is unavailable.")
        return value

    @staticmethod
    def _id(action: TargetAction) -> int:
        if action.internal_id is None:
            raise AssistantValidationError("Select a concrete item first.")
        return action.internal_id

    @staticmethod
    def _lines(rows) -> str:
        values = list(rows)
        return "Natija topilmadi." if not values else "\n".join(str(item) for item in values[:20])
