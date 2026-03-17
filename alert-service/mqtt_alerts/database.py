"""Database connection and session management."""

import logging
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def _set_wal_mode(dbapi_conn, connection_record):
    """Enable WAL mode for concurrent reads between services."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


async def init_db(db_path: str) -> async_sessionmaker[AsyncSession]:
    """Initialize the database engine and create tables."""
    global _engine, _session_factory

    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
    )

    # Set WAL mode on every new connection
    event.listen(_engine.sync_engine, "connect", _set_wal_mode)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    logger.info("Database initialized at %s", db_path)
    return _session_factory


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory


async def close_db():
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
