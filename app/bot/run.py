"""Telegram-only entrypoint using the same application lifecycle as the API."""

import asyncio
import logging

from app.core.application import ApplicationContext
from app.core.config import get_settings
from app.core.exceptions import RedisConfigurationError, TelegramConfigurationError
from app.core.logging import configure_logging, report_error


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    context = ApplicationContext(settings, telegram=True)
    try:
        await context.start()
        assert context.telegram is not None
        await context.telegram.poll()
    finally:
        await context.close()


def run() -> int:
    configure_logging()
    try:
        asyncio.run(main())
    except (TelegramConfigurationError, RedisConfigurationError) as error:
        print(str(error))
        return 1
    except KeyboardInterrupt:
        return 0
    except Exception as error:  # noqa: BLE001 - executable boundary
        print(f"Bot stopped. Error ID: {report_error(logging.getLogger('app.bot.run'), error)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
