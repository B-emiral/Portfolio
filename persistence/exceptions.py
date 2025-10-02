"""Custom exceptions for persistence layer."""


class DuplicateDocumentError(Exception):
    """Raised when attempting to insert a document with duplicate content_hash."""

    def __init__(self, content_hash: str, doc_id: int | None = None):
        self.content_hash = content_hash
        self.doc_id = doc_id
        message = f"Document with content_hash '{content_hash}' already exists"
        if doc_id:
            message += f" (ID: {doc_id})"
        super().__init__(message)
