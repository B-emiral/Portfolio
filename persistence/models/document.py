# ./persistence/models/document.py
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import ConfigDict
from sqlalchemy import Column, String
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field as SQLField

from persistence.models.base import BaseEntityModel


class DocumentType(str, Enum):
    REPORT = "report"
    NEWS_ARTICLE = "news_article"
    RESEARCH_PAPER = "research_paper"
    SENTENCE = "sentence"
    OTHER = "other"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class DocumentEntity(BaseEntityModel, table=True):
    __tablename__ = "documents"

    model_config = ConfigDict(arbitrary_types_allowed=True)

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
