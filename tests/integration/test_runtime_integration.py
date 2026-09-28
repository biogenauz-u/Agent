import os
import secrets

import pytest
from sqlalchemy import text

from app.core.config import Settings
from app.database.session import DatabaseManager
from app.modules.security.redis_state import RedisLockService
from app.redis.keys import SecurityKeys
from app.redis.manager import RedisManager

pytestmark = pytest.mark.integration


def integration_settings() -> Settings:
    if os.getenv("RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_INTEGRATION_TESTS=1 to use real local infrastructure.")
    settings = Settings()
    if settings.database_url is None or settings.redis_url is None:
        pytest.skip("DATABASE_URL and REDIS_URL are required for integration tests.")
    return settings


async def test_real_postgres_connection_and_migration_head() -> None:
    manager = DatabaseManager(integration_settings())
    try:
        manager.initialize()
        async with manager.engine.connect() as connection:
            assert await connection.scalar(text("SELECT 1")) == 1
            assert await connection.scalar(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            ) == "0009"
    finally:
        await manager.dispose()


async def test_real_redis_ttl_and_persistent_lock() -> None:
    settings = integration_settings()
    manager = RedisManager(settings)
    suffix = secrets.token_hex(8)
    keys = SecurityKeys(f"{settings.redis_key_prefix}:integration:{suffix}", 0)
    temporary = f"{settings.redis_key_prefix}:diagnostic:{suffix}"
    initialized = False
    try:
        manager.initialize()
        initialized = True
        assert await manager.client.ping()
        await manager.client.set(temporary, "ok", ex=5)
        assert await manager.client.get(temporary) == "ok"
        assert 0 < await manager.client.ttl(temporary) <= 5

        first = RedisLockService(manager.client, keys)
        assert await first.is_locked()
        await first.unlock()
        second = RedisLockService(manager.client, keys)
        assert not await second.is_locked()
        await second.lock()
        assert await first.is_locked()
    finally:
        if initialized:
            await RedisLockService(manager.client, keys).lock()
            await manager.client.delete(temporary)
            await manager.client.delete(keys.key("locked"), keys.key("version"))
        await manager.close()
