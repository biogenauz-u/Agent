"""Safe local runtime diagnostic. It never prints connection URLs or credentials."""

import asyncio
import platform
import secrets
from urllib.parse import urlsplit

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.api.app import create_app
from app.core.config import Settings
from app.database.session import DatabaseManager
from app.redis.manager import RedisManager


async def database_check(settings: Settings) -> tuple[bool, dict[str, object]]:
    if settings.database_url is None:
        return False, {"status": "BLOCKED", "reason": "DATABASE_URL is not configured"}
    manager = DatabaseManager(settings)
    try:
        manager.initialize()
        async with manager.engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        "SELECT version(), current_database(), "
                        "(SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema = 'public')"
                    )
                )
            ).one()
            current = await connection.scalar(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
        return True, {
            "status": "CONNECTED",
            "version": str(row[0]).split(",", 1)[0],
            "database": row[1],
            "tables": row[2],
            "migration": current,
        }
    except Exception as error:  # noqa: BLE001 - executable diagnostic boundary
        return False, {"status": "FAIL", "reason": type(error).__name__}
    finally:
        await manager.dispose()


async def redis_check(settings: Settings) -> tuple[bool, dict[str, object]]:
    if settings.redis_url is None:
        return False, {"status": "BLOCKED", "reason": "REDIS_URL is not configured"}
    manager = RedisManager(settings)
    key = f"{settings.redis_key_prefix}:diagnostic:{secrets.token_hex(8)}"
    initialized = False
    try:
        manager.initialize()
        initialized = True
        pong = await manager.client.ping()
        await manager.client.set(key, "ok", ex=10)
        value = await manager.client.get(key)
        ttl = await manager.client.ttl(key)
        await manager.client.delete(key)
        raw = settings.redis_url.get_secret_value()
        path = urlsplit(raw).path.strip("/")
        return bool(pong and value == "ok" and 0 < ttl <= 10), {
            "status": "CONNECTED",
            "database": int(path) if path.isdigit() else 0,
            "ttl": ttl,
        }
    except Exception as error:  # noqa: BLE001 - executable diagnostic boundary
        return False, {"status": "FAIL", "reason": type(error).__name__}
    finally:
        if initialized:
            await manager.client.delete(key)
        await manager.close()


async def main() -> int:
    settings = Settings()
    head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
    print("Personal AI Runtime Check")
    print(f"Python: {platform.python_version()}")
    print("Config: OK")
    print(f"Timezone: {settings.app_timezone}")
    print(f"Security backend: {settings.security_state_backend}")
    print(f"Migration head: {head}")
    database_ok, database = await database_check(settings)
    redis_ok, redis = await redis_check(settings)
    print(f"Database: {database}")
    print(f"Redis: {redis}")
    create_app(settings)
    print("FastAPI app: OK")
    return 0 if database_ok and redis_ok else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
