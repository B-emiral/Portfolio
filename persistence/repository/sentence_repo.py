# ./persistence/repository/sentiment_repo.py
"""Repository for sentiment analysis entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from persistence.models.sentence import SentimentAnalysisEntity
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SentimentAnalysisRepository:
    """Repository for sentiment analysis task."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_text_hash(
        self, text_hash: str, doc_id: int
    ) -> SentimentAnalysisEntity | None:
        """Get entity by text hash and document ID."""
        result = await self.session.execute(
            select(SentimentAnalysisEntity).where(
                SentimentAnalysisEntity.text_hash == text_hash,
                SentimentAnalysisEntity.doc_id == doc_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, entity: SentimentAnalysisEntity) -> SentimentAnalysisEntity:
        """Create new entity."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        logger.debug(f"Created SentimentAnalysisEntity ID={entity.id}")
        return entity

    async def get_by_id(self, entity_id: int) -> SentimentAnalysisEntity | None:
        """Get entity by ID."""
        result = await self.session.execute(
            select(SentimentAnalysisEntity).where(
                SentimentAnalysisEntity.id == entity_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_doc_id(self, doc_id: int) -> list[SentimentAnalysisEntity]:
        """Get all entities for a document."""
        result = await self.session.execute(
            select(SentimentAnalysisEntity).where(
                SentimentAnalysisEntity.doc_id == doc_id
            )
        )
        return list(result.scalars().all())
