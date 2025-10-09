# ./persistence/models/document.py
from __future__ import annotations

from datetime import UTC, datetime, timezone
from enum import Enum

from pydantic import ConfigDict
from sqlalchemy import Column, DateTime, String
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


class DocumentType(str, Enum):
    REPORT = "report"
    NEWS_ARTICLE = "news_article"
    RESEARCH_PAPER = "research_paper"
    SENTENCE = "sentence"
    OTHER = "other"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Document(SQLModel, table=True):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int | None = SQLField(default=None, primary_key=True)
    title: str
    content: str
    doc_type: DocumentType = SQLField(
        sa_column=Column(
            SAEnum(DocumentType, name="document_type"),
            nullable=False,
            default=DocumentType.OTHER,
        )
    )
    content_hash: str | None = SQLField(
        default=None,
        sa_column=Column(String, unique=True, index=True, nullable=True),
    )
    document_date: datetime | None = SQLField(default=None)

    created_at: datetime = SQLField(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = SQLField(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc),
    )
    processed_at: datetime = SQLField(
        sa_column=Column(DateTime(timezone=True), nullable=True),
        default=None,
    )
