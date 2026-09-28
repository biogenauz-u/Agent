import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.encryption import CredentialEncryption
from app.database.models.task import Task, TaskPriority, TaskStatus
from app.database.session import DatabaseManager
from app.modules.audit.actions import AuditAction
from app.modules.tasks.audit import TaskAudit
from app.modules.tasks.calendar_sync import TaskCalendarPort
from app.modules.tasks.exceptions import TaskConflictError, TaskNotFoundError
from app.modules.tasks.reminders import TaskReminderPort
from app.modules.tasks.reports import TaskReportService
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.schemas import TaskCreate, TaskDailySummary, TaskUpdate, TaskView
from app.modules.tasks.utils import OPEN_STATUSES
from app.modules.users.repository import UserRepository


class TaskService:
    def __init__(
        self,
        database: DatabaseManager,
        owner_id: int,
        encryption_key,
        timezone: ZoneInfo,
        recent_limit: int,
        default_priority: TaskPriority,
        default_reminder_minutes: int,
        reminder: TaskReminderPort | None = None,
        calendar: TaskCalendarPort | None = None,
        *,
        now=lambda: datetime.now(UTC),
    ) -> None:
        self.database, self.owner_id = database, owner_id
        self.cipher = CredentialEncryption(encryption_key)
        self.timezone, self.recent_limit = timezone, recent_limit
        self.default_priority = default_priority
        self.default_reminder_minutes = default_reminder_minutes
        self.reminder, self.calendar = reminder, calendar
        self.now = now
        self.audit = TaskAudit(database, owner_id)
        self.reports = TaskReportService(database, owner_id)

    async def _owner(self, session, *, create: bool = False) -> int | None:
        users = UserRepository(session)
        owner = await users.get_by_telegram_user_id(self.owner_id)
        if owner is None and create:
            owner = await users.create(self.owner_id)
        return owner.id if owner else None

    def _view(self, row: Task, warnings: list[str] | None = None) -> TaskView:
        description = (
            self.cipher.decrypt(row.description_encrypted, self.owner_id, "task_description")
            if row.description_encrypted
            else None
        )
        return TaskView(
            id=row.id,
            title=row.title,
            description=description,
            status=row.status,
            priority=row.priority,
            due_date=row.due_date,
            due_at=row.due_at,
            completed_at=row.completed_at,
            reminder_enabled=row.reminder_enabled,
            reminder_offset_minutes=row.reminder_offset_minutes,
            calendar_linked=row.calendar_event_id is not None,
            created_at=row.created_at,
            warnings=warnings or [],
        )

    async def _row(self, task_id: int) -> Task:
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = await TaskRepository(session).get(owner, task_id) if owner else None
            if row is None:
                raise TaskNotFoundError("Task not found.")
            return row

    async def _set_links(
        self,
        task_id: int,
        *,
        reminder_id: int | None = None,
        calendar_event_id: str | None = None,
    ) -> Task:
        async with self.database.session() as session:
            owner = await self._owner(session)
            row = await TaskRepository(session).get(owner, task_id) if owner else None
            if row is None:
                raise TaskNotFoundError("Task not found.")
            values = {}
            if reminder_id is not None:
                values["reminder_id"] = reminder_id
            if calendar_event_id is not None:
                values["calendar_event_id"] = calendar_event_id
            return await TaskRepository(session).update(row, values)

    async def create_task(self, request: TaskCreate) -> TaskView:
        description = (
            self.cipher.encrypt(request.description, self.owner_id, "task_description")
            if request.description
            else None
        )
        priority = (
            request.priority
            if "priority" in request.model_fields_set
            else self.default_priority
        )
        offset = request.reminder_offset_minutes or self.default_reminder_minutes
        async with self.database.session() as session:
            owner = await self._owner(session, create=True)
            assert owner is not None
            row = await TaskRepository(session).create(
                Task(
                    user_id=owner,
                    title=request.title,
                    description_encrypted=description,
                    priority=priority,
                    due_date=request.due_date,
                    due_at=request.due_at.astimezone(UTC) if request.due_at else None,
                    reminder_enabled=request.reminder_enabled,
                    reminder_offset_minutes=offset if request.reminder_enabled else None,
                    source=request.source,
                )
            )
            task_id = row.id
        warnings: list[str] = []
        if request.reminder_enabled:
            if self.reminder is None:
                warnings.append("Reminder service unavailable.")
            else:
                try:
                    reminder_id = await self.reminder.create(
                        task_id,
                        request.title,
                        request.due_date,
                        request.due_at,
                        offset,
                        self.now(),
                    )
                    await self._set_links(task_id, reminder_id=reminder_id)
                    await self.audit.record(AuditAction.TASK_REMINDER_CREATED, task_id)
                except Exception as error:  # noqa: BLE001 - task remains valid
                    warnings.append(type(error).__name__)
        if request.calendar_sync:
            if self.calendar is None:
                warnings.append("Calendar service unavailable.")
            else:
                try:
                    event_id = await self.calendar.create(task_id, request.title, request.due_at)
                    await self._set_links(task_id, calendar_event_id=event_id)
                    await self.audit.record(AuditAction.TASK_CALENDAR_LINKED, task_id)
                except Exception as error:  # noqa: BLE001 - task remains valid
                    warnings.append(type(error).__name__)
        await self.audit.record(
            AuditAction.TASK_CREATED,
            task_id,
            {"status": TaskStatus.TODO.value, "priority": priority.value},
        )
        return self._view(await self._row(task_id), warnings)

    async def get_task(self, task_id: int) -> TaskView:
        return self._view(await self._row(task_id))

    async def list_tasks(
        self,
        *,
        day: date | None = None,
        overdue: bool = False,
        unfinished_before: date | None = None,
        limit: int | None = None,
    ) -> list[TaskView]:
        async with self.database.session() as session:
            owner = await self._owner(session)
            rows = (
                await TaskRepository(session).list(
                    owner,
                    limit or self.recent_limit,
                    day=day,
                    overdue_before=self.now().astimezone(self.timezone) if overdue else None,
                    unfinished_before=unfinished_before,
                )
                if owner
                else []
            )
            return [self._view(row) for row in rows]

    async def today(self) -> list[TaskView]:
        return await self.list_tasks(day=self.now().astimezone(self.timezone).date())

    async def tomorrow(self) -> list[TaskView]:
        return await self.list_tasks(
            day=self.now().astimezone(self.timezone).date() + timedelta(days=1)
        )

    async def overdue(self) -> list[TaskView]:
        return await self.list_tasks(overdue=True)

    async def complete_task(self, task_id: int) -> TaskView:
        now = self.now()
        async with self.database.session() as session:
            owner = await self._owner(session)
            current = await TaskRepository(session).get(owner, task_id) if owner else None
            if current is None:
                raise TaskNotFoundError("Task not found.")
            reminder_id = current.reminder_id
            row = await TaskRepository(session).complete(owner, task_id, now)
            if row is None:
                raise TaskConflictError("Task is not open.")
        if reminder_id and self.reminder:
            try:
                await self.reminder.cancel(reminder_id)
            except Exception as error:  # noqa: BLE001 - completion remains authoritative
                logging.getLogger(__name__).warning(
                    "task_reminder_cancel_failed", extra={"error_type": type(error).__name__}
                )
        await self.audit.record(AuditAction.TASK_COMPLETED, task_id, {"status": "DONE"})
        return self._view(row)

    async def update_task(self, task_id: int, request: TaskUpdate) -> TaskView:
        values = request.model_dump(exclude_unset=True)
        calendar_requested = values.pop("calendar_sync", None)
        if "description" in values:
            plain = values.pop("description")
            values["description_encrypted"] = (
                self.cipher.encrypt(plain, self.owner_id, "task_description") if plain else None
            )
        if values.get("due_at"):
            values["due_at"] = values["due_at"].astimezone(UTC)
        async with self.database.session() as session:
            owner = await self._owner(session)
            repository = TaskRepository(session)
            row = await repository.get(owner, task_id) if owner else None
            if row is None:
                raise TaskNotFoundError("Task not found.")
            old_priority, reminder_id, event_id = row.priority, row.reminder_id, row.calendar_event_id
            row = await repository.update(row, values)
        warnings: list[str] = []
        offset = row.reminder_offset_minutes or self.default_reminder_minutes
        if row.reminder_enabled and self.reminder:
            try:
                if reminder_id:
                    await self.reminder.reschedule(
                        reminder_id, row.due_date, row.due_at, offset, self.now()
                    )
                else:
                    new_id = await self.reminder.create(
                        row.id, row.title, row.due_date, row.due_at, offset, self.now()
                    )
                    await self._set_links(row.id, reminder_id=new_id)
                    await self.audit.record(AuditAction.TASK_REMINDER_CREATED, row.id)
            except Exception as error:  # noqa: BLE001
                warnings.append(type(error).__name__)
        if (event_id or calendar_requested) and self.calendar:
            try:
                if event_id:
                    await self.calendar.update(event_id, row.title, row.due_at)
                else:
                    new_event = await self.calendar.create(row.id, row.title, row.due_at)
                    await self._set_links(row.id, calendar_event_id=new_event)
                    await self.audit.record(AuditAction.TASK_CALENDAR_LINKED, row.id)
            except Exception as error:  # noqa: BLE001
                warnings.append(type(error).__name__)
        await self.audit.record(AuditAction.TASK_UPDATED, task_id)
        if row.priority != old_priority:
            await self.audit.record(
                AuditAction.TASK_PRIORITY_CHANGED,
                task_id,
                {"priority": row.priority.value},
            )
        return self._view(await self._row(task_id), warnings)

    async def delete_task(self, task_id: int) -> None:
        now = self.now()
        async with self.database.session() as session:
            owner = await self._owner(session)
            current = await TaskRepository(session).get(owner, task_id) if owner else None
            if current is None:
                raise TaskNotFoundError("Task not found.")
            reminder_id = current.reminder_id
            if await TaskRepository(session).soft_delete(owner, task_id, now) is None:
                raise TaskNotFoundError("Task not found.")
        if reminder_id and self.reminder:
            try:
                await self.reminder.cancel(reminder_id)
            except Exception as error:  # noqa: BLE001
                logging.getLogger(__name__).warning(
                    "task_reminder_cancel_failed", extra={"error_type": type(error).__name__}
                )
        await self.audit.record(AuditAction.TASK_CANCELLED, task_id)
        await self.audit.record(AuditAction.TASK_DELETED, task_id)

    async def carry_forward_tasks(self, task_ids: list[int], new_date: date) -> list[TaskView]:
        results: list[TaskView] = []
        for task_id in dict.fromkeys(task_ids):
            row = await self._row(task_id)
            if row.status not in OPEN_STATUSES:
                raise TaskConflictError("Only open tasks can be carried forward.")
            due_at = None
            if row.due_at:
                local_time = row.due_at.astimezone(self.timezone).timetz().replace(tzinfo=None)
                due_at = datetime.combine(new_date, local_time, self.timezone)
            result = await self.update_task(
                task_id, TaskUpdate(due_date=new_date, due_at=due_at)
            )
            await self.audit.record(
                AuditAction.TASK_CARRIED_FORWARD,
                task_id,
                {"due_date": new_date.isoformat()},
            )
            results.append(result)
        return results

    async def list_unfinished_for_date(self, day: date) -> list[TaskView]:
        return await self.list_tasks(unfinished_before=day)

    async def get_daily_summary(self, day: date | None = None) -> TaskDailySummary:
        now = self.now().astimezone(self.timezone)
        return await self.reports.daily(day or now.date(), now)
