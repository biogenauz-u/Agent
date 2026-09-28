"""Async online migrations and PostgreSQL-only offline SQL generation."""

import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.database.base import Base, UTCDateTime
from app.database.models import AuditLog, User  # noqa: F401
from app.database.session import database_url

target_metadata = Base.metadata


def render_item(item_type: str, obj: object, autogen_context: object) -> str | bool:
    if item_type == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    engine = create_async_engine(
        database_url(get_settings()),
        poolclass=pool.NullPool,
        hide_parameters=True,
        connect_args={"server_settings": {"timezone": "UTC"}, "timeout": 10},
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    context.configure(
        dialect_name="postgresql",
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_online())
