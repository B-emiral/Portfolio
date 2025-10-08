# ./utils/get_unprocessed_documents.py
from typing import Any, Dict, List

from loguru import logger
from persistence.models import Document
from persistence.session import get_async_session
from sqlalchemy import select


async def get_unprocessed_documents(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch unprocessed documents -not setnetences- from DB

    Args:
        limit (int): Maximum number of documents to fetch.

    Returns:
        List[Dict[str, Any]]: List of unprocessed documents as dicts.
    """
    async with get_async_session() as session:
        query = (
            select(Document)
            .where(Document.processed_at.is_(None))
            .where(Document.doc_type != "SENTENCE")
            .limit(limit)
        )

        result = await session.execute(query)
        docs = result.scalars().all()

        logger.info(f"Fetched {len(docs)} unprocessed documents from DB.")

        return [doc.__dict__ for doc in docs]
