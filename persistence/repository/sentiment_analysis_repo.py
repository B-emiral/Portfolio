# ./persistence/repository/sentiment_analysis_repo.py
"""Repository for sentiment analysis entities."""

from __future__ import annotations

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from persistence.models.sentence import SentimentAnalysisEntity


class SentimentAnalysisRepository:
    """Repository for sentiment analysis operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_text_hash(self, text_hash: str) -> SentimentAnalysisEntity | None:
        """Get sentiment analysis entity by text hash and doc_id."""
        result = await self.session.exec(
            select(SentimentAnalysisEntity).where(
                SentimentAnalysisEntity.text_hash == text_hash
            )
        )
        return result.scalar_one_or_none()

    async def create(self, entity: SentimentAnalysisEntity) -> SentimentAnalysisEntity:
        """Create a new sentiment analysis entity."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: SentimentAnalysisEntity) -> SentimentAnalysisEntity:
        """Update an existing sentiment analysis entity."""
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
