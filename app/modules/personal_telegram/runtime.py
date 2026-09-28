import logging

from aiogram import Bot

from app.core.config import Settings
from app.core.runtime import RuntimeState
from app.database.session import DatabaseManager
from app.modules.personal_telegram.delivery import PersonalTelegramBotDelivery
from app.modules.personal_telegram.exceptions import PersonalTelegramError
from app.modules.personal_telegram.monitor import PersonalTelegramMonitor
from app.modules.personal_telegram.service import PersonalTelegramService
from app.modules.personal_telegram.session_store import PersonalTelegramSessionStore


class PersonalTelegramRuntime:
    def __init__(
        self,
        settings: Settings,
        database: DatabaseManager,
        state: RuntimeState,
        bot: Bot | None,
    ) -> None:
        assert settings.telegram_owner_id is not None and settings.data_encryption_key is not None
        self.settings, self.state = settings, state
        self.store = PersonalTelegramSessionStore(
            database, settings.telegram_owner_id, settings.data_encryption_key
        )
        notifier = (
            PersonalTelegramBotDelivery(bot, settings.telegram_owner_id) if bot else None
        )
        self.service = PersonalTelegramService(settings, database, self.store, notifier)
        self.monitor = PersonalTelegramMonitor(
            self.service, settings.personal_telegram_initial_sync_limit
        )

    async def start(self) -> None:
        try:
            if not await self.service.restore():
                self.state.personal_telegram = "not_connected"
                return
            self.state.personal_telegram = "connected"
            if self.settings.run_personal_telegram_monitor and self.service.notifier:
                await self.monitor.start()
                self.state.personal_telegram = "monitoring"
        except PersonalTelegramError:
            self.state.personal_telegram = "error"
        except Exception as error:  # noqa: BLE001 - optional integration must not crash the app
            logging.getLogger(__name__).warning(
                "personal_telegram_start_failed",
                extra={"error_type": type(error).__name__},
            )
            self.state.personal_telegram = "error"

    async def activate_monitor(self) -> None:
        self.state.personal_telegram = "connected"
        if self.settings.run_personal_telegram_monitor and self.service.notifier:
            await self.monitor.start()
            self.state.personal_telegram = "monitoring"

    async def disconnect(self) -> None:
        await self.monitor.stop()
        await self.service.disconnect()
        self.state.personal_telegram = "not_connected"

    async def close(self) -> None:
        await self.monitor.stop()
        if self.service.client is not None:
            await self.service.client.disconnect()
            self.service.client = None
        if self.state.personal_telegram in {"connected", "monitoring"}:
            self.state.personal_telegram = "stopped"
