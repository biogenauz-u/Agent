from datetime import date, datetime

from app.database.session import DatabaseManager
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.schemas import TaskDailySummary
from app.modules.users.repository import UserRepository


class TaskReportService:
    def __init__(self, database: DatabaseManager, owner_id: int) -> None:
        self.database, self.owner_id = database, owner_id

    async def daily(self, day: date, now: datetime) -> TaskDailySummary:
        async with self.database.session() as session:
            owner = await UserRepository(session).get_by_telegram_user_id(self.owner_id)
            if owner is None:
                return TaskDailySummary(total=0, done=0, remaining=0, overdue=0, urgent=0)
            return await TaskRepository(session).summary(owner.id, day, now)
