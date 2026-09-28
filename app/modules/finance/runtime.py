from app.core.config import Settings
from app.database.session import DatabaseManager
from app.modules.calendar.state import TemporaryStore
from app.modules.finance.actions import FinanceActions
from app.modules.finance.service import FinanceService


class FinanceRuntime:
    def __init__(
        self,
        settings: Settings,
        database: DatabaseManager,
        states: TemporaryStore,
    ) -> None:
        assert settings.telegram_owner_id is not None
        self.settings = settings
        self.service = FinanceService(
            database,
            settings.telegram_owner_id,
            settings.timezone,
            settings.finance_recent_limit,
            settings.finance_top_category_limit,
        )
        self.actions = FinanceActions(self.service, states, settings.telegram_owner_id)

    async def start(self) -> None:
        await self.service.seed_defaults()

    async def close(self) -> None:
        return None
