# ./persistence/scripts/create_tables.py
import asyncio

from config import settings
from langops.persistence.models.document import DocumentEntity  # noqa: F401
from langops.persistence.models.sentence import SentenceSentimentEntity  # noqa: F401
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel


async def create_tables() -> None:
    print(f"Creating tables in {settings.database_url}")

    engine = create_async_engine(settings.database_url, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    print("Database tables created successfully.")


if __name__ == "__main__":
    asyncio.run(create_tables())
