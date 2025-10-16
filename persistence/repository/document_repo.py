# ./persistence/repository/document_repo.py
from __future__ import annotations

from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from persistence.models.document import DocumentEntity, DocumentType
from persistence.repository.base_repo import BaseRepository


class DocumentRepository(BaseRepository):
    entity = DocumentEntity
    parent_entity = None
    fk_field = None

    def __init__(self) -> None:
        super().__init__()

    async def get_or_create_document(
        self, session: AsyncSession, doc_id: str, content: str
    ) -> int:
        doc = await self.get_by_id(session, doc_id)
        if doc:
            logger.debug(f"Found document ID={doc_id}")
            return doc_id
        else:
            doc = DocumentEntity(
                title=f"Auto-generated from {self.get_or_create_document.__name__}",
                content=content,
                content_hash=self.compute_hash(content),
                doc_type=DocumentType.SENTENCE,
            )
            created_doc = await self.create(session, doc)
            logger.debug(f"Created document ID={created_doc.id}")
            return created_doc.id
