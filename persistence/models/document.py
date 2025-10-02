"""Document model for storing documents and their metadata."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import ConfigDict
from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped


class DocumentType(str, Enum):
    """Document type enumeration."""

    REPORT = "report"
    NEWS_ARTICLE = "news_article"
    RESEARCH_PAPER = "research_paper"
    SENTENCE = "sentence"
    OTHER = "other"


def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(UTC)


class Document(SQLModel, table=True):
    """Document model for storing document content and metadata."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int | None = Field(default=None, primary_key=True)
    title: str
    content: str

    doc_type: DocumentType = Field(
        sa_column=Column(
            SAEnum(DocumentType, name="document_type"),
            nullable=False,
            default=DocumentType.OTHER,
        )
    )

    content_hash: str | None = Field(default=None, index=True, unique=True)
    added_at: datetime = Field(default_factory=_utcnow)
    document_date: datetime | None = Field(default=None)


# Import Sentence to register it in SQLAlchemy registry before adding relationship
from persistence.models.sentence import SentimentAnalysisEntity  # noqa: E402

# Add relationship after both classes are defined
Document.sentences = relationship("SentimentAnalysisEntity", back_populates="document")

if TYPE_CHECKING:
    Document.sentences: Mapped[list[SentimentAnalysisEntity]]  # pyright: ignore[reportInvalidTypeForm]
