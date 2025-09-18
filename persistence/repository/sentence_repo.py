from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from persistence.models.sentence import Sentence, SentimentOut
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Select, select


class SentenceRepository:
    """Async repository for Sentence model. One instance per request/operation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, sentence: Sentence) -> Sentence:
        if not isinstance(sentence, Sentence):
            sentence = Sentence(**sentence)  # type: ignore[arg-type]
        self.session.add(sentence)
        await self.session.commit()
        await self.session.refresh(sentence)
        return sentence

    async def bulk_create(self, sentences: Iterable[Sentence]) -> list[Sentence]:
        objs: list[Sentence] = []
        for s in sentences:
            if not isinstance(s, Sentence):
                s = Sentence(**s)  # type: ignore[arg-type]
            self.session.add(s)
            objs.append(s)
        await self.session.commit()
        for o in objs:
            await self.session.refresh(o)
        return objs

    async def get(self, sentence_id: int) -> Sentence | None:
        result = await self.session.exec(
            select(Sentence).where(Sentence.id == sentence_id)
        )
        return result.scalar_one_or_none()

    async def list_for_document(
        self, doc_id: int, limit: int = 100, offset: int = 0
    ) -> list[Sentence]:
        result = await self.session.exec(
            select(Sentence)
            .where(Sentence.doc_id == doc_id)
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def update(self, sentence_id: int, **fields) -> Sentence | None:
        s = await self.get(sentence_id)
        if not s:
            return None
        for k, v in fields.items():
            if hasattr(s, k):
                setattr(s, k, v)
        self.session.add(s)
        await self.session.commit()
        await self.session.refresh(s)
        return s

    async def delete(self, sentence_id: int) -> bool:
        s = await self.get(sentence_id)
        if not s:
            return False
        await self.session.delete(s)
        await self.session.commit()
        return True

    async def count_for_document(self, doc_id: int) -> int:
        result = await self.session.exec(
            select(Sentence).where(Sentence.doc_id == doc_id)
        )
        return len(result.all())

    async def attach_to_document(
        self, doc_id: int, sentences: Iterable[Sentence]
    ) -> list[Sentence]:
        objs: list[Sentence] = []
        for s in sentences:
            if not isinstance(s, Sentence):
                s = Sentence(**s)  # type: ignore[arg-type]
            s.doc_id = doc_id
            self.session.add(s)
            objs.append(s)
        await self.session.commit()
        for o in objs:
            await self.session.refresh(o)
        return objs

    async def _select_for_update(self, doc_id: int, text: str) -> Sentence | None:
        """
        Best-effort select ... FOR UPDATE to reduce race; falls back if unsupported.
        """
        stmt: Select = select(Sentence).where(
            Sentence.doc_id == doc_id, Sentence.text == text
        )
        try:
            stmt = stmt.with_for_update()
            result = await self.session.exec(stmt)
            return result.scalar_one_or_none()
        except Exception:
            result = await self.session.exec(
                select(Sentence).where(Sentence.doc_id == doc_id, Sentence.text == text)
            )
            return result.scalar_one_or_none()

    async def upsert_by_doc_text(
        self, doc_id: int, text: str, sentiment_out: SentimentOut | None = None
    ) -> tuple[Sentence, bool]:
        """
        Upsert a sentence identified by (doc_id, text).

        - If not exists: create (apply sentiment_out if provided).
        - If exists and sentiment_out provided and differs: apply_sentiment(), refresh.
        - Returns (Sentence, created_or_updated: bool) where True means new or updated.
        """
        now = datetime.now(timezone.utc)

        async with self.session.begin():
            s = await self._select_for_update(doc_id, text)

            if s is None:
                s = Sentence(doc_id=doc_id, text=text)
                if sentiment_out is not None:
                    s.apply_sentiment(sentiment_out, now=now)
                self.session.add(s)
                await self.session.flush()
                await self.session.refresh(s)
                return s, True

            # exists; optionally apply sentiment update
            if sentiment_out is not None:
                changed = s.apply_sentiment(sentiment_out, now=now)
                if changed:
                    self.session.add(s)
                    await self.session.flush()
                    await self.session.refresh(s)
                    return s, True

        return s, False
