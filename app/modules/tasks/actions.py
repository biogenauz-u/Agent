from datetime import date, datetime
from typing import Any

from app.modules.calendar.state import TemporaryStore
from app.modules.tasks.exceptions import TaskConfirmationError
from app.modules.tasks.schemas import TaskCreate, TaskUpdate
from app.modules.tasks.service import TaskService


class TaskActions:
    def __init__(self, service: TaskService, states: TemporaryStore, owner_id: int) -> None:
        self.service, self.states, self.owner_id = service, states, owner_id

    async def prepare(self, kind: str, data: dict[str, Any]) -> str:
        return await self.states.issue(
            "task_action", {"kind": kind, "data": data, "owner": self.owner_id}
        )

    async def cancel(self, token: str) -> None:
        await self.states.consume("task_action", token)

    async def confirm(self, token: str) -> str:
        action = await self.states.consume("task_action", token)
        if not action or action.get("owner") != self.owner_id:
            raise TaskConfirmationError("Confirmation expired or already processed.")
        kind, data = action["kind"], dict(action["data"])
        if kind == "create":
            if data.get("due_date"):
                data["due_date"] = date.fromisoformat(data["due_date"])
            if data.get("due_at"):
                data["due_at"] = datetime.fromisoformat(data["due_at"])
            task = await self.service.create_task(TaskCreate(**data))
            return f"Task saqlandi. ID: {task.id}"
        if kind == "update":
            task_id = int(data.pop("id"))
            if data.get("due_date"):
                data["due_date"] = date.fromisoformat(data["due_date"])
            if data.get("due_at"):
                data["due_at"] = datetime.fromisoformat(data["due_at"])
            await self.service.update_task(task_id, TaskUpdate(**data))
            return "Task yangilandi."
        if kind == "complete":
            await self.service.complete_task(int(data["id"]))
            return "Task bajarildi."
        if kind == "delete":
            await self.service.delete_task(int(data["id"]))
            return "Task o'chirildi."
        if kind == "carry":
            await self.service.carry_forward_tasks(
                [int(item) for item in data["ids"]], date.fromisoformat(data["date"])
            )
            return "Tasklar yangi sanaga ko'chirildi."
        raise TaskConfirmationError("Invalid task confirmation.")

