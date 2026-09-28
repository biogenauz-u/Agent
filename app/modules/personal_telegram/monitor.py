import asyncio
import logging

from app.modules.personal_telegram.service import PersonalTelegramService


class PersonalTelegramMonitor:
    """Registers one incoming-only Telethon handler and performs a silent baseline first."""

    def __init__(self, service: PersonalTelegramService, initial_sync_limit: int) -> None:
        self.service, self.initial_sync_limit = service, initial_sync_limit
        self.running = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self.running:
                return
            await self.service.initial_sync(self.initial_sync_limit)

            async def handle(event) -> None:
                try:
                    await self.service.process_event(event)
                except Exception as error:  # noqa: BLE001 - event boundary must remain alive
                    logging.getLogger(__name__).warning(
                        "personal_telegram_event_failed",
                        extra={"error_type": type(error).__name__},
                    )

            self.service._client().register_incoming_handler(handle)
            self.running = True

    async def stop(self) -> None:
        async with self._lock:
            if self.running and self.service.client is not None:
                self.service.client.remove_incoming_handler()
            self.running = False
