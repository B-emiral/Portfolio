# ./persistence/models/document.py

from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlmodel import Field, Relationship, SQLModel

from .sentence import Sentence


class DocumentType(str, PyEnum):
    """Enum for document types to ensure data consistency."""

    REPORT = "report"
    NEWS_ARTICLE = "news_article"
    RESEARCH_PAPER = "research_paper"
    OTHER = "other"


class Document(SQLModel, table=True):
    """

    Represents a source document in the database.
    This is the 'one' side of a one-to-many relationship with Sentence.
    Each Document can have multiple associated Sentences.
    """

    __tablename__ = "document"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True, description="The title of the document.")
    context: str = Field(description="The full text content of the document.")
    doc_type: DocumentType = Field(description="The category of the document.")
    document_date: datetime = Field(
        index=True, description="The original publication date of the document."
    )
    added_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        description="Timestamp when the document was added to the database.",
    )

    # --- Relationship Attribute ---
    # This attribute defines the one-to-many relationship.
    # It allows you to access all related sentences from a document instance
    # (e.g., my_document.sentences).
    # 'back_populates' links this to the 'document' attribute in the Sentence model,
    # making the relationship bidirectional and managed by the ORM.
    sentences: list[Sentence] = Relationship(back_populates="document")
