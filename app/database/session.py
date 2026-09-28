"""Explicit, reusable database lifecycle with caller-owned transactions."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.core.exceptions import DatabaseConfigurationError


def database_url(settings: Settings) -> URL:
    """Validate only when database initialization is requested; never expose the URL."""
    if not settings.database_url:
        raise DatabaseConfigurationError("DATABASE_URL is not configured.")
    try:
        url = make_url(settings.database_url.get_secret_value())
        valid = url.drivername == "postgresql+asyncpg" and bool(url.host and url.database)
        _ = url.port
    except (ArgumentError, ValueError):
        raise DatabaseConfigurationError("DATABASE_URL is invalid.") from None
    if not valid:
        raise DatabaseConfigurationError(
            "DATABASE_URL must use postgresql+asyncpg with host/database."
        )
    return url


class DatabaseManager:
    """Own one engine/pool per application lifespan; inject this instance into services."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: AsyncEngine | None = None
        self._sessions: async_sessionmaker[AsyncSession] | None = None

    def initialize(self) -> None:
        if self._engine is not None:
            return
        self._engine = create_async_engine(
            database_url(self._settings),
            pool_pre_ping=True,
            echo=False,
            hide_parameters=True,
            connect_args={"server_settings": {"timezone": "UTC"}, "timeout": 10},
        )
        self._sessions = async_sessionmaker(self._engine, expire_on_commit=False)

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise DatabaseConfigurationError("DatabaseManager.initialize() must be called first.")
        return self._engine

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Commit on successful scope exit; rollback and close on failure/cancellation."""
        if self._sessions is None:
            raise DatabaseConfigurationError("DatabaseManager.initialize() must be called first.")
        async with self._sessions.begin() as session:
            yield session

    async def dispose(self) -> None:
        """Close the pool after all active work has finished."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessions = None
