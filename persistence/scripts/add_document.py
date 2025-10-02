from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
from persistence.exceptions import DuplicateDocumentError
from persistence.models.document import Document, DocumentType
from persistence.session import get_session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--json-path",
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    help="Path to the JSON file containing document data",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Set logging level",
)
@click.option(
    "--skip-duplicates",
    is_flag=True,
    help="Skip duplicate documents without error",
)
def add_document_cli(json_path: str, log_level: str, skip_duplicates: bool) -> None:
    """CLI wrapper to add a document into the database."""
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))
    try:
        document = asyncio.run(
            add_document_from_json(json_path, skip_duplicates=skip_duplicates)
        )
        click.secho(
            f"✓ Document added: ID={document.id}, Title='{document.title}'", fg="green"
        )
    except Exception as e:
        click.secho(f"✗ Error: {e}", fg="red", err=True)
        logger.exception("Document import failed")
        raise click.Abort()


async def add_document_from_json(
    json_path: str,
    skip_duplicates: bool,
    session: AsyncSession | None = None,
) -> Document:
    """
    Add a document from JSON file to the database.
    If no session is provided, creates one internally.
    """
    json_path = Path(json_path)
    logger.info(f"Loading document from {json_path}")

    doc_data = _parse_document_json(json_path)
    _validate_document_data(doc_data)
    doc_fields = _extract_document_fields(doc_data)

    if session is not None:
        return await _add_document_logic(doc_fields, skip_duplicates, session)

    async with _get_db_session() as new_session:
        return await _add_document_logic(doc_fields, skip_duplicates, new_session)


async def _add_document_logic(
    doc_fields: dict[str, Any],
    skip_duplicates: bool,
    session: AsyncSession,
) -> Document:
    """Core logic to insert or skip a document in the database."""
    content_hash = hashlib.md5(doc_fields["text"].encode()).hexdigest()

    try:
        result = await session.execute(
            select(Document).where(Document.content_hash == content_hash)
        )
        existing_doc = result.scalar_one_or_none()

        if existing_doc:
            logger.warning(
                f"Document hash: {content_hash} already exists (ID: {existing_doc.id})"
            )
            if skip_duplicates:
                return existing_doc
            raise DuplicateDocumentError(content_hash, existing_doc.id)

        document = Document(
            title=doc_fields["title"],
            text=doc_fields["text"],
            doc_type=doc_fields["doc_type"],
            content_hash=content_hash,
            document_date=doc_fields["document_date"],
        )

        session.add(document)
        await session.commit()
        await session.refresh(document)
        logger.info(f"Successfully added document (ID: {document.id})")
        return document

    except IntegrityError as e:
        await session.rollback()
        if "UNIQUE constraint failed: document.content_hash" in str(e):
            result = await session.execute(
                select(Document).where(Document.content_hash == content_hash)
            )
            existing_doc = result.scalar_one_or_none()
            raise DuplicateDocumentError(
                content_hash, existing_doc.id if existing_doc else None
            )
        raise


def _parse_document_json(json_path: Path) -> dict[str, Any]:
    """Parse and validate JSON document file."""
    try:
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {e}")
        raise click.BadParameter(f"Invalid JSON format: {e}")
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise click.BadParameter(f"Error reading file: {e}")


def _validate_document_data(doc_data: dict[str, Any]) -> None:
    """Ensure required fields are present in JSON."""
    required_fields = ["title", "text"]
    missing_fields = [field for field in required_fields if field not in doc_data]

    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        logger.error(error_msg)
        raise click.BadParameter(error_msg)


def _extract_document_fields(doc_data: dict[str, Any]) -> dict[str, Any]:
    """Normalize JSON fields into model-compatible values."""
    result = {
        "title": doc_data["title"],
        "text": doc_data["text"],
    }

    if doc_type_val := doc_data.get("doc_type"):
        try:
            result["doc_type"] = DocumentType(doc_type_val)
        except ValueError:
            valid_types = ", ".join([t.value for t in DocumentType])
            error_msg = (
                f"Invalid document type: '{doc_type_val}'. Valid types: {valid_types}"
            )
            logger.error(error_msg)
            raise click.BadParameter(error_msg)
    else:
        result["doc_type"] = DocumentType.OTHER

    if date_str := doc_data.get("document_date"):
        result["document_date"] = _parse_document_date(date_str)
    else:
        result["document_date"] = datetime.now(UTC)

    return result


def _parse_document_date(date_str: str) -> datetime:
    """Parse date from string to datetime."""
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    error_msg = f"Invalid date format: '{date_str}'. Expected format: YYYY-MM-DD"
    logger.error(error_msg)
    raise click.BadParameter(error_msg)


class _get_db_session:
    """Context manager for database session with proper error handling."""

    def __init__(self):
        self.session = None

    async def __aenter__(self) -> AsyncSession:
        session_gen = get_session()
        self.session = await session_gen.__anext__()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"Database error: {exc_val}")
            await self.session.rollback()
            if not isinstance(exc_val, click.ClickException):
                raise click.ClickException(str(exc_val))
            return False
        return True


if __name__ == "__main__":
    add_document_cli()
