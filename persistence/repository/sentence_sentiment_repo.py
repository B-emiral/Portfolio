# ./persistence/repository/sentence_sentiment_repo.py

from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger as log
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from persistence.models.sentence import (
    SentenceEntity,
    SentenceSentimentEntity,
    SentenceSentimentResponseModel,
)
from persistence.repository.base_repo import BaseRepository


class SentenceSentimentRepository(BaseRepository):
    entity = SentenceSentimentEntity
    parent_entity = SentenceEntity
    fk_field = "sentence_id"

    def __init__(self) -> None:
        super().__init__()

    async def get_by_sentence_id_and_hash(
        self, session: AsyncSession, sentence_id: int, text: str
    ) -> SentenceSentimentEntity | None:
        stmt_sentence = select(SentenceEntity).where(SentenceEntity.id == sentence_id)
        result_sentence = await session.exec(stmt_sentence)
        sentence = result_sentence.scalar_one_or_none()
        if not sentence:
            return None
        if sentence.text_hash != self.compute_hash(text):
            return None

        stmt_sentiment = select(SentenceSentimentEntity).where(
            SentenceSentimentEntity.sentence_id == sentence_id
        )
        sentence_sentiment_entity = await session.exec(stmt_sentiment)
        return sentence_sentiment_entity.scalar_one_or_none()

    async def upsert(
        self,
        session: AsyncSession,
        sentence_id: int | None,
        text: str,
        response_llm_instance: SentenceSentimentResponseModel,
        persist_override: bool,
    ) -> tuple[SentenceSentimentEntity, str]:
        if sentence_id is None:
            raise ValueError("sentence_id cannot be None during upsert()")

        existing = await self.get_by_sentence_id_and_hash(session, sentence_id, text)

        if existing:
            log.info("Existing sentiment analysis found, proceeding")

            if persist_override:
                log.info("Existing sentiment analysis found re-analyzing")

                existing.sentiment = response_llm_instance.sentiment
                existing.sentiment_confidence = (
                    response_llm_instance.sentiment_confidence
                )
                existing.sentiment_calls += 1
                existing.updated_at = datetime.now(timezone.utc)

                await self.update(session, existing)

                log.info(f"Updated sentiment id={existing.id}")
                return response_llm_instance, "updated"

            if not persist_override and existing.sentiment is None:
                log.info("Existing sentiment analysis found but empty, re-analyzing")
                log.warning(
                    "override=False but sentiment is empty ⇒ semantic overriding"
                )

                existing.sentiment = response_llm_instance.sentiment
                existing.sentiment_confidence = (
                    response_llm_instance.sentiment_confidence
                )
                existing.sentiment_calls += 1
                existing.updated_at = datetime.now(timezone.utc)

                await self.update(session, existing)
                await session.flush()
                await session.refresh(existing)
                log.info(f"Updated sentiment id={existing.id}")
                return existing, "updated semantically"

        if not existing:
            log.info("No existing sentiment analysis found, proceeding")
            # REFACTOR: from_llm_output base method that must be overridden by subclass
            new_entity = SentenceSentimentEntity.from_llm_output(
                llm_output=response_llm_instance,
                sentence_id=sentence_id,
            )
            await self.create(session, new_entity)
            await session.flush()
            await session.refresh(new_entity)
            log.info(f"Created new sentiment id={new_entity.id}")
            return new_entity, "created"
        return None, "error"
