from urllib.parse import urlsplit

from redis.asyncio import Redis

from app.core.config import Settings
from app.core.exceptions import RedisConfigurationError


class RedisManager:
    """Own one Redis connection pool for the entire application lifespan."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Redis | None = None

    def initialize(self) -> None:
        if self._client is not None:
            return
        if not self._settings.redis_url:
            raise RedisConfigurationError("REDIS_URL is not configured.")
        raw = self._settings.redis_url.get_secret_value()
        try:
            url = urlsplit(raw)
            if url.scheme not in {"redis", "rediss"} or not url.hostname:
                raise ValueError("invalid scheme or host")
            _ = url.port
            self._client = Redis.from_url(
                raw,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                health_check_interval=30,
            )
        except ValueError:
            raise RedisConfigurationError(
                "REDIS_URL must be a valid redis:// or rediss:// URL."
            ) from None

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RedisConfigurationError("RedisManager.initialize() must be called first.")
        return self._client

    async def close(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            await client.aclose(close_connection_pool=True)
