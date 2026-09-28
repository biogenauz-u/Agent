import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


async def check_redis_health(client: Redis) -> bool:
    try:
        async with asyncio.timeout(3):
            return bool(await client.ping())
    except (RedisError, OSError, TimeoutError):
        logger.warning("redis_health_check_failed")
        return False
