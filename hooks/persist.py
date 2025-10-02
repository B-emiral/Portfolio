# ./hooks/persist.py
from __future__ import annotations

import hashlib
import json
from typing import Any

from loguru import logger
from persistence.models.sentence import SentimentOut
from persistence.repository.document_repo import DocumentRepository
from persistence.repository.sentence_repo import SentenceRepository
from persistence.session import get_session

from hooks.utils import extract_text


async def persist_sql(payload: dict[str, Any]) -> None:
    """
    SQL persistence hook that saves LLM analysis results.
    Uses existing domain models and repository methods.
    """
    try:
        # Extract metadata from payload
        doc_id = payload.get("document_id")
        text = payload.get("text", "").strip()
        sql_table_name = payload.get("sql_table_name")

        # Skip if no table specified or no text/document
        if not sql_table_name:
            logger.debug("persist_sql: skipping, no SQL table name specified")
            return

        if not text and not doc_id:
            logger.debug("persist_sql: skipping, no text or document_id provided")
            return

        # Get response text
        response = payload.get("response", {})
        response_text = extract_text(response)
        if not response_text:
            logger.warning("persist_sql: unable to extract response text")
            return

        # Parse sentiment from response
        try:
            # Extract JSON data from response
            start = response_text.find("{")
            end = response_text.rfind("}")

            if start != -1 and end != -1 and end > start:
                json_str = response_text[start : end + 1]
            else:
                json_str = response_text

            # Parse with the domain model's SentimentOut
            sentiment_data = json.loads(json_str)
            sentiment_out = SentimentOut(**sentiment_data)

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("persist_sql: failed to parse response: {}", e)
            return

        # Use database session and repositories
        async for session in get_session():
            try:
                # Get the repositories
                doc_repo = DocumentRepository(session)
                sent_repo = SentenceRepository(session)

                # Resolve document - either use the provided ID or find by hash
                if doc_id:
                    document = await doc_repo.get(doc_id)
                    if not document:
                        logger.error("persist_sql: document ID {} not found", doc_id)
                        return
                else:
                    # Use hash lookup that's already in the domain model
                    content_hash = hashlib.md5(text.encode()).hexdigest()
                    document = await doc_repo.find_by_hash(content_hash)

                    if not document:
                        logger.error("persist_sql: no matching document found for text")
                        return

                    doc_id = document.id

                # Use SentenceRepository's upsert method to create/update sentence
                # This leverages the Sentence.apply_sentiment method
                sentence, is_new = await sent_repo.upsert_by_doc_text(
                    doc_id=doc_id,
                    text=text,
                    sentiment_out=sentiment_out,  # Uses the domain model
                )

                action = "created" if is_new else "updated"
                logger.info(
                    "persist_sql: {} sentiment record, doc_id={}, sentence_id={}, sentiment={}",
                    action,
                    doc_id,
                    sentence.id,
                    sentence.sentiment_label,
                )

                # Commit the changes
                await session.commit()

            except Exception as e:
                logger.error("persist_sql db error: {}", e)
                await session.rollback()

    except Exception as e:
        # Non-fatal
        logger.error("persist_sql hook failed: {}", e)
