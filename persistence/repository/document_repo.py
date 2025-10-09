# ./persistence/repository/document_repo.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from persistence.models.document import Document
from persistence.models.sentence import Sentence


class DocumentRepository:
    """Async repository for Document model. One instance per request/operation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, doc: Document) -> Document:
        if not isinstance(doc, Document):
            doc = Document(**doc)
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def get(self, doc_id: int) -> Document | None:
        result = await self.session.exec(select(Document).where(Document.id == doc_id))
        return result.scalar_one_or_none()

    async def list(self, limit: int = 50, offset: int = 0) -> list[Document]:
        result = await self.session.exec(select(Document).offset(offset).limit(limit))
        return result.all()

    async def update(self, doc_id: int, **fields) -> Document | None:
        doc = await self.get(doc_id)
        if not doc:
            return None
        for k, v in fields.items():
            if hasattr(doc, k):
                setattr(doc, k, v)
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def delete(self, doc_id: int) -> bool:
        doc = await self.get(doc_id)
        if not doc:
            return False
        await self.session.delete(doc)
        await self.session.commit()
        return True

    async def upsert_by_external_id(
        self, external_id: str, doc_data: dict
    ) -> tuple[Document, bool]:
        """
        Upsert a document identified by external_id.
        Returns (Document, created_or_updated) where True means created or updated.
        Requires a unique index on external_id at DB level for correctness.
        """
        async with self.session.begin():
            result = await self.session.exec(
                select(Document).where(Document.external_id == external_id)
            )
            doc = result.scalar_one_or_none()
            if doc is None:
                doc = Document(**{**doc_data, "external_id": external_id})
                self.session.add(doc)
                await self.session.flush()
                await self.session.refresh(doc)
                return doc, True
            changed = False
            for k, v in doc_data.items():
                if hasattr(doc, k) and getattr(doc, k) != v:
                    setattr(doc, k, v)
                    changed = True
            if changed:
                doc.updated_at = datetime.now(timezone.utc)
                self.session.add(doc)
                await self.session.flush()
                await self.session.refresh(doc)
                return doc, True
        return doc, False

    async def add_sentences_bulk(
        self, doc_id: int, sentences: Iterable[dict]
    ) -> list[Sentence]:
        """
        Attach multiple Sentence items to a document efficiently within a transaction.
        Accepts dicts or Sentence instances.
        """
        objs: list[Sentence] = []
        async with self.session.begin():
            for s in sentences:
                if not isinstance(s, Sentence):
                    s = Sentence(**s)
                s.doc_id = doc_id
                self.session.add(s)
                objs.append(s)
            await self.session.flush()
            for o in objs:
                await self.session.refresh(o)
        return objs

    async def create_with_sentences(
        self, doc_data: dict, sentences: list[dict]
    ) -> Document:
        """
        Transactionally create a document and its sentences. Rolls back on failure.
        """
        try:
            async with self.session.begin():
                doc = Document(**doc_data)
                self.session.add(doc)
                await self.session.flush()
                objs: list[Sentence] = []
                for s in sentences:
                    sent = Sentence(**s, doc_id=doc.id)
                    self.session.add(sent)
                    objs.append(sent)
                await self.session.flush()
                for o in objs:
                    await self.session.refresh(o)
                await self.session.refresh(doc)
                return doc
        except Exception:
            logger.exception("create_with_sentences failed; rolling back")
            raise

    async def find_by_hash(self, content_hash: str) -> Document | None:
        stmt = select(Document).where(Document.content_hash == content_hash)
        result = await self.session.exec(stmt)
        return result.scalar_one_or_none()
