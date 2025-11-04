# ./persistence/session.py
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from config import settings
from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

_engine: AsyncEngine | None = None
_SessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str | None = None) -> None:
    global _engine, _SessionLocal
    if _engine is not None and _SessionLocal is not None:
        return  # Already initialized

    db_url = database_url or settings.database_url
    logger.info("Initializing database connection: {}", db_url)

    _engine = create_async_engine(
        db_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        connect_args={
            "check_same_thread": False,
            "timeout": 10,
        },
    )

    _SessionLocal = async_sessionmaker(
        _engine, class_=SQLModelAsyncSession, expire_on_commit=False, autoflush=False
    )

    asyncio.get_event_loop().create_task(_init_sqlite_pragmas())


async def _init_sqlite_pragmas() -> None:
    global _engine
    if _engine is None:
        return
    try:
        async with _engine.begin() as conn:
            await conn.exec_driver_sql("PRAGMA journal_mode = WAL;")
            await conn.exec_driver_sql("PRAGMA synchronous = NORMAL;")
            await conn.exec_driver_sql("PRAGMA temp_store = MEMORY;")
        logger.debug("SQLite PRAGMA settings applied.")
    except Exception as e:
        logger.warning(f"Could not apply SQLite PRAGMAs: {e}")


@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    global _SessionLocal
    if _SessionLocal is None:
        init_engine()

    if _SessionLocal is None:
        raise RuntimeError("Database session could not be initialized")

    async with _SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
