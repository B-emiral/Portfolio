# ./persistence/repository/sentence_repo.py
from __future__ import annotations

from typing import Any

from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from persistence.models.document import Document
from persistence.models.sentence import Sentence
from persistence.session import get_async_session


class SentenceRepository:
    """Async repository for Sentence model. One instance per request/operation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, sentence: Sentence) -> Sentence:
        if not isinstance(sentence, Sentence):
            sentence = Sentence(**sentence)
        self.session.add(sentence)
        await self.session.commit()
        await self.session.refresh(sentence)
        return sentence

    @staticmethod
    async def get_documents_without_sentences(limit: int = 100) -> list[dict[str, Any]]:
        async with get_async_session() as session:
            stmt = (
                select(Document)
                .outerjoin(Sentence, Sentence.doc_id == Document.id)
                .where(Sentence.id.is_(None))
                .limit(limit)
            )
            result = await session.exec(stmt)
            docs = result.all()
            logger.info(f"Fetched {len(docs)} documents with no sentences from DB.")
            return [doc.model_dump() for doc in docs]
