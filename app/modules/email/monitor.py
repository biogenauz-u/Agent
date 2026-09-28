import asyncio
import logging

from app.modules.email.exceptions import GmailError
from app.modules.email.service import EmailService


class GmailMonitor:
    def __init__(self, service: EmailService, interval: int, initial_limit: int) -> None:
        self.service, self.interval, self.initial_limit = service, interval, initial_limit
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def poll_once(self) -> int:
        if await self.service.checkpoint() is None:
            await self.service.initial_sync(self.initial_limit)
            return 0
        return await self.service.sync_new()

    async def run_loop(self) -> None:
        failures = 0
        while not self._stop.is_set():
            try:
                await self.poll_once()
                failures = 0
            except GmailError as error:
                failures += 1
                logging.getLogger(__name__).warning("gmail_poll_failed", extra={"error_type": type(error).__name__})
            delay = min(300, self.interval * (2 ** min(failures, 3)))
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=delay)
            except TimeoutError:
                pass

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self.run_loop(), name="gmail-monitor")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task
            self._task = None
