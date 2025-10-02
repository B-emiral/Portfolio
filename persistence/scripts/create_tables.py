# ./scripts/create_tables.py
from __future__ import annotations

import asyncio

from config import settings
from persistence.models.document import Document  # noqa: F401
from persistence.models.sentence import SentimentAnalysisEntity  # noqa: F401
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel


async def create_tables() -> None:
    """Create all database tables."""
    print(f"Creating tables in {settings.database_url}")

    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)

    print("Database tables created successfully.")


if __name__ == "__main__":
    asyncio.run(create_tables())
