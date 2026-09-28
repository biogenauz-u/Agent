import asyncio
import signal
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.application import ApplicationContext
from app.run_all import cancel_on_sigterm, coordinate


async def test_sigterm_uses_cancellation_and_restores_handler() -> None:
    previous = signal.getsignal(signal.SIGTERM)
    entered = asyncio.Event()

    async def worker() -> None:
        with cancel_on_sigterm():
            entered.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(worker())
    await entered.wait()
    handler = signal.getsignal(signal.SIGTERM)
    assert callable(handler)
    handler(signal.SIGTERM, None)
    with pytest.raises(asyncio.CancelledError):
        await task
    assert signal.getsignal(signal.SIGTERM) == previous


class FakeServer:
    def __init__(self) -> None:
        self.should_exit = False
        self.closed = False

    async def serve(self) -> None:
        try:
            while not self.should_exit:
                await asyncio.sleep(0.01)
        finally:
            self.closed = True


async def test_bot_failure_stops_web_and_drains_tasks() -> None:
    context = Mock(spec=ApplicationContext)
    context.telegram = Mock()
    context.telegram.poll = AsyncMock(side_effect=RuntimeError("test component failure"))
    context.telegram.stop = AsyncMock()
    server = FakeServer()
    with pytest.raises(RuntimeError, match="test component failure"):
        await coordinate(context, server)
    assert server.closed
    context.telegram.stop.assert_awaited_once()
    assert not any(t.get_name() in {"http-server", "telegram-polling"} for t in asyncio.all_tasks())


async def test_combined_cancellation_drains_both_components() -> None:
    context = Mock(spec=ApplicationContext)
    context.telegram = Mock()
    stopped = asyncio.Event()
    started = asyncio.Event()

    async def poll(handle_signals: bool) -> None:
        started.set()
        await stopped.wait()

    context.telegram.poll = poll
    context.telegram.stop = AsyncMock(side_effect=stopped.set)
    server = FakeServer()
    task = asyncio.create_task(coordinate(context, server))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert server.closed
    assert not any(t.get_name() in {"http-server", "telegram-polling"} for t in asyncio.all_tasks())
