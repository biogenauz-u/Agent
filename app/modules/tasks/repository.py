from datetime import date, datetime

from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.task import Task, TaskPriority, TaskStatus
from app.modules.tasks.schemas import TaskDailySummary
from app.modules.tasks.utils import OPEN_STATUSES


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, task: Task) -> Task:
        self.session.add(task)
        await self.session.flush()
        return task

    async def get(self, user_id: int, task_id: int) -> Task | None:
        return await self.session.scalar(
            select(Task).where(
                Task.user_id == user_id, Task.id == task_id, Task.deleted_at.is_(None)
            )
        )

    async def list(
        self,
        user_id: int,
        limit: int,
        *,
        day: date | None = None,
        overdue_before: datetime | None = None,
        unfinished_before: date | None = None,
    ) -> list[Task]:
        query = select(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None))
        if day is not None:
            query = query.where(Task.due_date == day)
        if overdue_before is not None:
            local_day = overdue_before.date()
            query = query.where(
                Task.status.in_(OPEN_STATUSES),
                or_(Task.due_at < overdue_before, and_(Task.due_at.is_(None), Task.due_date < local_day)),
            )
        elif unfinished_before is not None:
            query = query.where(
                Task.status.in_(OPEN_STATUSES), Task.due_date <= unfinished_before
            )
        elif day is None:
            query = query.where(Task.status.in_(OPEN_STATUSES))
        rows = await self.session.scalars(
            query.order_by(
                Task.due_date.is_(None),
                Task.due_date,
                Task.due_at.is_(None),
                Task.due_at,
                Task.priority.desc(),
                Task.id,
            ).limit(limit)
        )
        return list(rows)

    async def update(self, row: Task, values: dict[str, object]) -> Task:
        for key, value in values.items():
            setattr(row, key, value)
        await self.session.flush()
        return row

    async def complete(self, user_id: int, task_id: int, now: datetime) -> Task | None:
        result = await self.session.execute(
            update(Task)
            .where(
                Task.user_id == user_id,
                Task.id == task_id,
                Task.deleted_at.is_(None),
                Task.status.in_(OPEN_STATUSES),
            )
            .values(status=TaskStatus.DONE, completed_at=now)
            .returning(Task)
        )
        return result.scalar_one_or_none()

    async def soft_delete(self, user_id: int, task_id: int, now: datetime) -> Task | None:
        result = await self.session.execute(
            update(Task)
            .where(Task.user_id == user_id, Task.id == task_id, Task.deleted_at.is_(None))
            .values(status=TaskStatus.CANCELLED, deleted_at=now)
            .returning(Task)
        )
        return result.scalar_one_or_none()

    async def summary(self, user_id: int, day: date, now: datetime) -> TaskDailySummary:
        row = (
            await self.session.execute(
                select(
                    func.count(Task.id),
                    func.sum(case((Task.status == TaskStatus.DONE, 1), else_=0)),
                    func.sum(case((Task.status.in_(OPEN_STATUSES), 1), else_=0)),
                    func.sum(
                        case(
                            (
                                and_(
                                    Task.status.in_(OPEN_STATUSES),
                                    or_(
                                        Task.due_at < now,
                                        and_(Task.due_at.is_(None), Task.due_date < now.date()),
                                    ),
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    func.sum(
                        case(
                            (
                                and_(
                                    Task.status.in_(OPEN_STATUSES),
                                    Task.priority == TaskPriority.URGENT,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                ).where(
                    Task.user_id == user_id,
                    Task.deleted_at.is_(None),
                    Task.due_date == day,
                )
            )
        ).one()
        return TaskDailySummary(
            total=int(row[0] or 0),
            done=int(row[1] or 0),
            remaining=int(row[2] or 0),
            overdue=int(row[3] or 0),
            urgent=int(row[4] or 0),
        )
