from app.core.config import Settings
from app.database.session import DatabaseManager
from app.modules.calendar.state import TemporaryStore
from app.modules.notebook.actions import NotebookActions
from app.modules.notebook.service import NotebookService
from app.modules.notebook.storage import EncryptedLocalStorage


class NotebookRuntime:
    def __init__(
        self, settings: Settings, database: DatabaseManager, states: TemporaryStore
    ) -> None:
        assert settings.telegram_owner_id is not None
        self.storage = EncryptedLocalStorage(
            settings.notebook_storage_path,
            settings.data_encryption_key,
            settings.notebook_max_file_size_mb,
        )
        self.service = NotebookService(
            database,
            settings.telegram_owner_id,
            self.storage,
            settings.data_encryption_key,
            settings.timezone,
            settings.notebook_recent_limit,
            settings.notebook_search_scan_limit,
            settings.notebook_allowed_schemes,
        )
        self.actions = NotebookActions(self.service, states, settings.telegram_owner_id)

    async def start(self) -> None:
        await self.storage.initialize()

    async def close(self) -> None:
        return None
