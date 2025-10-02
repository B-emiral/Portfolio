# ./persistence/models/sentence.py
"""Sentence models for sentiment analysis task."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from persistence.models.base import LLMOutputModel
from pydantic import Field
from sqlalchemy import Column, DateTime, Float, Index, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

if TYPE_CHECKING:
    pass


class SentimentLabel(str, Enum):
    """Sentiment classification labels."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


# 1️⃣ LLM Output Model (validation only)
class SentimentLLM(LLMOutputModel):
    """Output model from LLM for sentiment analysis."""

    sentiment: SentimentLabel
    sentiment_confidence: float = Field(ge=0.0, le=1.0)


# 2️⃣ Base Sentence Table (common fields)
class Sentence(SQLModel, table=False):
    """Base sentence table with common fields."""

    __tablename__ = "sentences_sentiment"
    __table_args__ = (
        Index("ix_sentences_doc_text", "doc_id", "text_hash", unique=True),
    )

    id: int | None = SQLField(default=None, primary_key=True)
    doc_id: int = SQLField(foreign_key="document.id", index=True, nullable=False)
    text: str = SQLField(sa_column=Column(String, nullable=False))
    text_hash: str = SQLField(sa_column=Column(String, nullable=False, index=True))

    created_at: datetime = SQLField(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = SQLField(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc),
    )


# 3️⃣ Task-Specific Persistable Entity
class SentimentAnalysisEntity(Sentence, table=True):
    """Persistable entity for sentiment analysis task."""

    persistable: bool = True

    # Task-specific fields for sentiment analysis
    sentiment: SentimentLabel | None = SQLField(
        sa_column=Column(SAEnum(SentimentLabel), nullable=True)
    )
    sentiment_confidence: float | None = SQLField(
        sa_column=Column(Float, nullable=True)
    )
    sentiment_calls: int = SQLField(default=0)

    @classmethod
    def from_llm_output(
        cls,
        llm_output: SentimentLLM,
        text: str,
        text_hash: str,
        doc_id: int,
        **extra_fields,
    ) -> SentimentAnalysisEntity:
        """Create entity from LLM output."""
        return cls(
            doc_id=1,
            text=text,
            text_hash=text_hash,
            sentiment=llm_output.sentiment,
            sentiment_confidence=llm_output.sentiment_confidence,
            sentiment_calls=1,
            **extra_fields,
        )

    def update_from_llm_output(self, llm_output: SentimentLLM) -> bool:
        """Update entity from new LLM output. Returns True if changed."""
        changed = False

        if self.sentiment != llm_output.sentiment:
            self.sentiment = llm_output.sentiment
            changed = True

        if (
            abs((self.sentiment_confidence or 0.0) - llm_output.sentiment_confidence)
            > 1e-6
        ):
            self.sentiment_confidence = llm_output.sentiment_confidence
            changed = True

        if changed:
            self.sentiment_calls = (self.sentiment_calls or 0) + 1
            self.updated_at = datetime.now(timezone.utc)

        return changed


# Add relationship AFTER class definition
SentimentAnalysisEntity.document = relationship("Document", back_populates="sentences")
