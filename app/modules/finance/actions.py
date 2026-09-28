from datetime import date
from decimal import Decimal
from typing import Any

from app.database.models.finance import FinanceCategoryType
from app.modules.calendar.state import TemporaryStore
from app.modules.finance.exceptions import FinanceConfirmationError
from app.modules.finance.schemas import FinanceTransactionCreate, FinanceTransactionUpdate
from app.modules.finance.service import FinanceService


class FinanceActions:
    """Single-use confirmation tokens; callbacks never contain financial payloads."""

    def __init__(self, service: FinanceService, states: TemporaryStore, owner_id: int) -> None:
        self.service, self.states, self.owner_id = service, states, owner_id

    async def prepare(self, kind: str, data: dict[str, Any]) -> str:
        return await self.states.issue(
            "finance_action", {"kind": kind, "data": data, "owner": self.owner_id}
        )

    async def cancel(self, token: str) -> None:
        await self.states.consume("finance_action", token)

    async def confirm(self, token: str) -> str:
        action = await self.states.consume("finance_action", token)
        if not action or action.get("owner") != self.owner_id:
            raise FinanceConfirmationError("Confirmation expired or already processed.")
        kind, data = action["kind"], action["data"]
        if kind == "create_transaction":
            payload = dict(data)
            payload["amount"] = Decimal(payload["amount"])
            payload["transaction_date"] = date.fromisoformat(payload["transaction_date"])
            row = await self.service.create_transaction(FinanceTransactionCreate(**payload))
            return f"Operatsiya saqlandi. ID: {row.id}"
        if kind == "update_transaction":
            values = dict(data["values"])
            if "amount" in values:
                values["amount"] = Decimal(values["amount"])
            if "transaction_date" in values:
                values["transaction_date"] = date.fromisoformat(values["transaction_date"])
            await self.service.update_transaction(
                int(data["id"]), FinanceTransactionUpdate(**values)
            )
            return "Operatsiya yangilandi."
        if kind == "delete_transaction":
            await self.service.delete_transaction(int(data["id"]))
            return "🗑 Operatsiya o‘chirildi."
        if kind == "create_category":
            await self.service.create_category(
                data["name"], FinanceCategoryType(data["category_type"])
            )
            return "Kategoriya yaratildi."
        if kind == "deactivate_category":
            await self.service.deactivate_category(int(data["id"]))
            return "Kategoriya o‘chirildi."
        raise FinanceConfirmationError("Invalid finance confirmation.")
