"""Custom exceptions for persistence layer."""


class DuplicateDocumentError(Exception):
    """Raised when attempting to insert a document with duplicate content_hash."""

    def __init__(self, content_hash: str, document_id: int | None = None):
        self.content_hash = content_hash
        self.document_id = document_id
        message = f"Document with content_hash '{content_hash}' already exists"
        if document_id:
            message += f" (ID: {document_id})"
        super().__init__(message)
