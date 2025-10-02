# ./persistence/session.py
from __future__ import annotations

from typing import AsyncIterator

from config import settings
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Global session factory
_SessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str | None = None) -> None:
    """Initialize the database engine and session factory."""
    global _SessionLocal
    if _SessionLocal is not None:
        return  # Already initialized

    # Use provided URL or get from settings
    db_url = database_url or settings.database_url

    logger.info("Initializing database connection: {}", db_url)

    engine = create_async_engine(
        db_url,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,
    )

    _SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Get a database session as an async context manager."""
    global _SessionLocal

    if _SessionLocal is None:
        init_engine()

    if _SessionLocal is None:
        raise RuntimeError("Database session could not be initialized")

    async with _SessionLocal() as session:
        yield session
