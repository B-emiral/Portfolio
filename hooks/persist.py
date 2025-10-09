# ./hooks/persist.py
"""Generic persistence hook that works with any persistable entity."""

from __future__ import annotations

from typing import Any

from loguru import logger
from persistence.session import get_async_session


async def persist_sql(payload: dict[str, Any]) -> None:
    """
    Generic persistence hook.

    Automatically detects and persists entities marked as persistable.
    """
    db_entity_model = payload.get("db_entity_model")

    if not db_entity_model:
        logger.debug("persist_sql: no db_entity_model in payload")
        return

    if not getattr(db_entity_model, "persistable", False):
        logger.debug(f"persist_sql: {db_entity_model.__name__} is not persistable")
        return

    text = payload.get("analyzed_text")
    response = payload.get("response")
    llm_output_model_class = payload.get("llm_output_model")

    raw_response = response.get("content", [{}])[0].get("text", "{}")

    if not all([text, response, llm_output_model_class]):
        logger.debug("persist_sql: missing required fields")
        return

    try:
        import json

        from sqlalchemy import select
        from tasks.base import GenericLLMTask

        text_hash = GenericLLMTask._compute_hash(text)

        response_data = json.loads(raw_response)
        llm_output_instance = llm_output_model_class(**response_data)

        logger.debug(f"persist_sql: validated LLM output: {llm_output_instance}")

        doc_id = await _get_or_create_document(text, text_hash)

        async with get_async_session() as session:
            repository_class = _get_repository_for_entity(db_entity_model)
            repo = repository_class(session)

            entity = db_entity_model.from_llm_output(
                llm_output=llm_output_instance,
                text=text,
                text_hash=text_hash,
                doc_id=doc_id,
            )

            result = await session.exec(
                select(db_entity_model).where(
                    db_entity_model.text_hash == text_hash,
                    db_entity_model.doc_id == doc_id,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug("persist_sql: entity already exists, skipping")
                return

            created_entity = await repo.create(entity)
            logger.debug(
                f"persist_sql: created new entity ID={created_entity.id or 'pending'}"
            )

    except Exception as e:
        logger.error(f"persist_sql error: {e}")
        logger.exception("Full persist_sql traceback:")
        raise


async def _get_or_create_document(text: str, text_hash: str) -> int:
    """Get or create document for text."""
    from persistence.models.document import Document, DocumentType
    from persistence.session import get_async_session
    from sqlalchemy import select

    async with get_async_session() as session:
        result = await session.exec(
            select(Document).where(Document.content_hash == text_hash)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            doc = Document(
                title="Auto-generated from task",
                content=text,
                content_hash=text_hash,
                doc_type=DocumentType.SENTENCE,
            )
            session.add(doc)
            await session.flush()
            logger.debug(f"Created document ID={doc.id}")

        return doc.id


def _get_repository_for_entity(entity_model: type) -> type:
    """Get repository class for entity model."""
    from persistence.repository.sentiment_analysis_repo import (
        SentimentAnalysisRepository,
    )

    # Registry pattern
    REPOSITORY_REGISTRY = {
        "SentimentAnalysisEntity": SentimentAnalysisRepository,
        # Add more mappings as needed
    }

    repo_class = REPOSITORY_REGISTRY.get(entity_model.__name__)

    if not repo_class:
        raise ValueError(
            f"No repository registered for {entity_model.__name__}. "
            f"Available: {list(REPOSITORY_REGISTRY.keys())}"
        )

    return repo_class
