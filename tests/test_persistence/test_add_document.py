# tests/test_persistence/test_add_document.py
import json
from datetime import UTC, datetime

import pytest
from persistence.exceptions import DuplicateDocumentError
from persistence.models.document import DocumentType
from persistence.scripts.add_document import add_document_from_json


@pytest.mark.asyncio
async def test_add_document_success(tmp_path, test_session):
    doc_data = {
        "title": "Test Document",
        "text": "This is a test.",
        "doc_type": "report",
        "document_date": datetime.now(UTC).strftime("%Y-%m-%d"),
    }
    json_file = tmp_path / "doc.json"
    json_file.write_text(json.dumps(doc_data))

    document = await add_document_from_json(
        str(json_file), skip_duplicates=False, session=test_session
    )

    assert document.id is not None
    assert document.title == "Test Document"
    assert document.doc_type == DocumentType.REPORT


@pytest.mark.asyncio
async def test_add_document_duplicate(tmp_path, test_session):
    doc_data = {"title": "Duplicate Doc", "text": "Same content."}
    json_file = tmp_path / "doc.json"
    json_file.write_text(json.dumps(doc_data))

    # First insert
    await add_document_from_json(
        str(json_file), skip_duplicates=False, session=test_session
    )

    # Second insert should raise
    with pytest.raises(DuplicateDocumentError):
        await add_document_from_json(
            str(json_file), skip_duplicates=False, session=test_session
        )


@pytest.mark.asyncio
async def test_add_document_skip_duplicate(tmp_path, test_session):
    doc_data = {"title": "Duplicate Doc", "text": "Same content again."}
    json_file = tmp_path / "doc.json"
    json_file.write_text(json.dumps(doc_data))

    first_doc = await add_document_from_json(
        str(json_file), skip_duplicates=False, session=test_session
    )
    second_doc = await add_document_from_json(
        str(json_file), skip_duplicates=True, session=test_session
    )

    assert first_doc.id == second_doc.id
