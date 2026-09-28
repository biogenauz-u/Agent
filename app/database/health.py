"""Credential-free database connectivity check."""

import asyncio
import logging

from asyncpg import PostgresError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def check_database_health(engine: AsyncEngine, timeout_seconds: float = 5) -> bool:
    try:
        async with asyncio.timeout(timeout_seconds):
            async with engine.connect() as connection:
                return await connection.scalar(text("SELECT 1")) == 1
    except (SQLAlchemyError, PostgresError, OSError, TimeoutError):
        logger.warning("database_health_check_failed")
        return False
