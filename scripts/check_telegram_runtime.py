"""Read-only Telegram runtime diagnostic with secret-safe output."""

import asyncio

from app.bot.factory import create_bot
from app.core.config import Settings
from app.database.health import check_database_health
from app.database.session import DatabaseManager
from app.redis.health import check_redis_health
from app.redis.manager import RedisManager


async def check_database(settings: Settings) -> str:
    if settings.database_url is None:
        return "NOT_CONFIGURED"
    manager = DatabaseManager(settings)
    try:
        manager.initialize()
        return "CONNECTED" if await check_database_health(manager.engine) else "UNAVAILABLE"
    except Exception as error:  # noqa: BLE001 - diagnostic process boundary
        return f"ERROR ({type(error).__name__})"
    finally:
        await manager.dispose()


async def check_redis(settings: Settings) -> str:
    if settings.redis_url is None:
        return "NOT_CONFIGURED"
    manager = RedisManager(settings)
    try:
        manager.initialize()
        return "CONNECTED" if await check_redis_health(manager.client) else "UNAVAILABLE"
    except Exception as error:  # noqa: BLE001 - diagnostic process boundary
        return f"ERROR ({type(error).__name__})"
    finally:
        await manager.close()


async def main() -> int:
    settings = Settings()
    print("Personal AI Telegram Runtime Check")
    print(f"Bot token configured: {settings.telegram_bot_token is not None}")
    print(f"Owner ID configured: {settings.telegram_owner_id is not None}")
    pin_mode = "argon2id" if settings.bot_pin_hash else "development" if settings.bot_pin else "missing"
    print(f"PIN mode: {pin_mode}")
    print(f"Security backend: {settings.security_state_backend}")
    print(f"Database: {await check_database(settings)}")
    print(f"Redis: {await check_redis(settings)}")

    if not settings.is_owner_configured:
        print("Telegram API: BLOCKED (token or owner ID missing)")
        return 2

    bot = create_bot(settings)
    try:
        identity = await bot.get_me()
        webhook = await bot.get_webhook_info()
        print("Telegram API: CONNECTED")
        print(f"Bot ID: {identity.id}")
        print(f"Bot username: @{identity.username}" if identity.username else "Bot username: NOT_SET")
        print(f"Webhook active: {bool(webhook.url)}")
    except Exception as error:  # noqa: BLE001 - sanitized external diagnostic
        print(f"Telegram API: ERROR ({type(error).__name__})")
        return 1
    finally:
        await bot.session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
