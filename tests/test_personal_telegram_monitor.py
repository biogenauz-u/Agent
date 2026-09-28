from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.modules.personal_telegram.monitor import PersonalTelegramMonitor


async def test_initial_sync_precedes_handler_registration() -> None:
    order = []
    client = SimpleNamespace(
        register_incoming_handler=lambda handler: order.append("handler"),
        remove_incoming_handler=lambda: order.append("removed"),
    )
    service = SimpleNamespace(
        initial_sync=AsyncMock(side_effect=lambda limit: order.append(f"sync:{limit}")),
        _client=lambda: client,
        client=client,
    )
    monitor = PersonalTelegramMonitor(service, 30)
    await monitor.start()
    await monitor.start()
    assert order == ["sync:30", "handler"]
    await monitor.stop()
    assert order[-1] == "removed"


async def test_event_failure_does_not_remove_monitor(caplog) -> None:
    captured = {}
    client = SimpleNamespace(
        register_incoming_handler=lambda handler: captured.update(handler=handler),
        remove_incoming_handler=lambda: None,
    )
    service = SimpleNamespace(
        initial_sync=AsyncMock(),
        process_event=AsyncMock(side_effect=RuntimeError("message-content-must-not-log")),
        _client=lambda: client,
        client=client,
    )
    monitor = PersonalTelegramMonitor(service, 10)
    await monitor.start()
    await captured["handler"](object())
    assert monitor.running
    assert "message-content-must-not-log" not in caplog.text
