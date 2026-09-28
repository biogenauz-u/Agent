"""One event loop and one resource owner for the explicit combined development mode."""

import asyncio
import logging
import signal
import socket
from collections.abc import Iterator
from contextlib import contextmanager
from types import FrameType

import uvicorn

from app.api.app import create_app
from app.core.application import ApplicationContext
from app.core.config import get_settings
from app.core.logging import configure_logging, report_error


class DevelopmentServer(uvicorn.Server):
    async def serve(self, sockets: list[socket.socket] | None = None) -> None:
        try:
            await super().serve(sockets=sockets)
        except SystemExit:
            raise RuntimeError("HTTP server startup failed.") from None

    @contextmanager
    def capture_signals(self) -> Iterator[None]:
        # asyncio.run owns Ctrl+C; avoid competing Uvicorn/Aiogram signal handlers.
        yield


@contextmanager
def cancel_on_sigterm() -> Iterator[None]:
    """Route service-manager termination through the same cleanup as Ctrl+C."""
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    assert task is not None
    previous = signal.getsignal(signal.SIGTERM)

    def terminate(signum: int, frame: FrameType | None) -> None:
        loop.call_soon_threadsafe(task.cancel)

    signal.signal(signal.SIGTERM, terminate)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


async def coordinate(context: ApplicationContext, server: uvicorn.Server) -> None:
    assert context.telegram is not None
    web = asyncio.create_task(server.serve(), name="http-server")
    bot = asyncio.create_task(context.telegram.poll(handle_signals=False), name="telegram-polling")
    try:
        done, _ = await asyncio.wait({web, bot}, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        server.should_exit = True
        try:
            await context.telegram.stop()
        except Exception as error:  # noqa: BLE001 - still drain both tasks after stop failure
            report_error(logging.getLogger(__name__), error)
        try:
            async with asyncio.timeout(15):
                await asyncio.gather(web, bot, return_exceptions=True)
        except TimeoutError:
            web.cancel()
            bot.cancel()
            await asyncio.gather(web, bot, return_exceptions=True)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    context = ApplicationContext(settings, telegram=True)
    with cancel_on_sigterm():
        try:
            await context.start()
            server = DevelopmentServer(
                uvicorn.Config(
                    create_app(context=context),
                    host=settings.api_host,
                    port=settings.api_port,
                    log_config=None,
                    access_log=False,
                    timeout_graceful_shutdown=10,
                )
            )
            await coordinate(context, server)
        finally:
            await context.close()


def run() -> int:
    configure_logging()
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        return 0
    except Exception as error:  # noqa: BLE001 - executable boundary
        report_error(logging.getLogger("app.run_all"), error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
