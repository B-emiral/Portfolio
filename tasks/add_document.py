# ./persistence/scripts/add_document.py
from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
from persistence.models.document import DocumentEntity, DocumentType
from persistence.repository.document_repo import DocumentRepository
from persistence.session import get_async_session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

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
        document, is_duplicate = asyncio.run(
            add_document_from_json(json_path, skip_duplicates=skip_duplicates)
        )
        _handle_success_response(document, is_duplicate, skip_duplicates)

    except IntegrityError as e:
        _handle_integrity_error_cli(e, skip_duplicates)

    except Exception as e:
        _handle_general_error(e)


def _handle_success_response(
    document: DocumentEntity, is_duplicate: bool, skip_duplicates: bool
) -> None:
    """Handle successful document processing response."""
    if is_duplicate:
        if skip_duplicates:
            click.secho(
                f"⚠️  Document already exists: ID={document.id}, "
                f"Title='{document.title}' (skipped)",
                fg="yellow",
            )
        else:
            click.secho(
                f"❌ Document already exists: ID={document.id}, "
                f"Title='{document.title}'",
                fg="red",
                err=True,
            )
            raise click.Abort()
    else:
        click.secho(
            f"✅ Document added successfully: ID={document.id}, "
            f"Title='{document.title}'",
            fg="green",
        )


def _handle_integrity_error_cli(error: IntegrityError, skip_duplicates: bool) -> None:
    """Handle database integrity errors in CLI context."""
    if "UNIQUE constraint failed: document.content_hash" in str(error):
        click.secho(
            "❌ Document with identical content already exists in database",
            fg="red",
            err=True,
        )
        if not skip_duplicates:
            click.secho("💡 Use --skip-duplicates flag to ignore duplicates", fg="blue")
    else:
        click.secho(f"❌ Database constraint error: {error}", fg="red", err=True)

    logger.debug("Database integrity error", exc_info=True)
    raise click.Abort()


def _handle_general_error(error: Exception) -> None:
    """Handle unexpected errors in CLI context."""
    click.secho(f"❌ Unexpected error: {error}", fg="red", err=True)
    logger.exception("Document import failed")
    raise click.Abort()


async def add_document_from_json(
    json_path: str,
    skip_duplicates: bool,
    session: AsyncSession | None = None,
) -> tuple[DocumentEntity, bool]:
    """Add a document from JSON file to database."""
    json_path_obj = Path(json_path)
    logger.info(f"Loading document from {json_path}")

    doc_data = _parse_document_json(json_path_obj)
    _validate_document_data(doc_data)
    doc_fields = _extract_document_fields(doc_data)

    content_hash = DocumentRepository.compute_hash(doc_fields["content"])
    doc_fields["content_hash"] = content_hash

    if session:
        return await _add_document_logic(doc_fields, skip_duplicates, session)

    try:
        async with get_async_session() as new_session:
            return await _add_document_logic(doc_fields, skip_duplicates, new_session)
    except IntegrityError as e:
        return await _handle_integrity_error(e, content_hash, skip_duplicates)


async def _handle_integrity_error(
    error: IntegrityError,
    content_hash: str,
    skip_duplicates: bool,
) -> tuple[DocumentEntity, bool]:
    if "UNIQUE constraint failed: document.content_hash" not in str(error):
        raise

    if not skip_duplicates:
        raise

    async with get_async_session() as session:
        result = await session.exec(
            select(DocumentEntity).where(DocumentEntity.content_hash == content_hash)
        )
        existing = result.scalar_one_or_none()
        return existing, True


async def _add_document_logic(
    doc_fields: dict[str, Any],
    skip_duplicates: bool,
    session: AsyncSession,
) -> tuple[DocumentEntity, bool]:
    """Core logic to insert or skip a document in the database."""
    content_hash = doc_fields["content_hash"]

    if skip_duplicates:
        existing = await _find_existing_document(content_hash, session)
        if existing:
            logger.info(f"Document already exists: ID={existing.id}")
            return existing, True

    document = DocumentEntity(**doc_fields)
    session.add(document)
    await session.flush()
    await session.refresh(document)

    return document, False


async def _find_existing_document(
    content_hash: str, session: AsyncSession
) -> DocumentEntity | None:
    result = await session.exec(
        select(DocumentEntity).where(DocumentEntity.content_hash == content_hash)
    )
    return result.scalar_one_or_none()


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
    required_fields = ["title", "content"]
    missing_fields = [field for field in required_fields if field not in doc_data]

    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        logger.error(error_msg)
        raise click.BadParameter(error_msg)


def _extract_document_fields(doc_data: dict[str, Any]) -> dict[str, Any]:
    """Normalize JSON fields into model-compatible values."""
    result = {
        "title": doc_data["title"],
        "content": doc_data["content"],
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


if __name__ == "__main__":
    add_document_cli()
