# ./persistence/session.py
from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from config import settings
from loguru import logger
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import Session, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

_engine: AsyncEngine | None = None
_SessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_engine_v2() -> None:
    global _engine, _SessionLocal
    if _engine is not None and _SessionLocal is not None:
        return

    logger.info("Initializing database connection: {}", settings.database_url)

    _engine = create_async_engine(
        settings.database_url,
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
        _engine,
        class_=SQLModelAsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@event.listens_for(Engine, "connect")
def set_sqlite_pragmas_v2(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()
    except Exception as e:
        logger.warning("Could not apply SQLite PRAGMAs: {}", e)


# INFO: get_async_session is legacy, it will be removed
@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    if _SessionLocal is None:
        init_engine_v2()

    async with _SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_async_session_v2() -> AsyncIterator[AsyncSession]:
    if _SessionLocal is None:
        init_engine_v2()

    async with _SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@contextmanager
def get_sync_session() -> Iterator[Session]:
    engine = create_engine(url=settings.database_url_sync)
    with Session(engine) as session:
        yield session
