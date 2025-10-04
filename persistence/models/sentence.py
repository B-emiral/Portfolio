# ./persistence/models/sentence.py
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from pydantic import Field as PydField
from sqlalchemy import Column, DateTime, Float, Index, String
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from persistence.models.base import LLMOutputModel

if TYPE_CHECKING:
    from persistence.models.document import Document  # noqa: F401


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class SentimentLLM(LLMOutputModel):
    sentiment: SentimentLabel
    sentiment_confidence: float = PydField(ge=0.0, le=1.0)


class SentenceBase(SQLModel, table=False):
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
    processed_at: datetime = SQLField(
        sa_column=Column(DateTime(timezone=True), nullable=True),
        default=None,
    )


class SentimentAnalysisEntity(SentenceBase, table=True):
    __tablename__ = "sentences_sentiment"
    __table_args__ = (
        Index("ix_sentences_doc_text", "doc_id", "text_hash", unique=True),
    )

    persistable: ClassVar[bool] = True

    sentiment: SentimentLabel | None = SQLField(
        sa_column=Column(
            SAEnum(SentimentLabel, name="sentiment_label_enum"), nullable=True
        )
    )
    sentiment_confidence: float | None = SQLField(
        sa_column=Column(Float, nullable=True)
    )
    sentiment_calls: int = SQLField(default=0, nullable=False)

    @classmethod
    def from_llm_output(
        cls,
        llm_output: SentimentLLM,
        text: str,
        text_hash: str,
        doc_id: int,
        **extra_fields,
    ) -> SentimentAnalysisEntity:
        return cls(
            doc_id=doc_id,
            text=text,
            text_hash=text_hash,
            sentiment=llm_output.sentiment,
            sentiment_confidence=llm_output.sentiment_confidence,
            sentiment_calls=1,
            **extra_fields,
        )

    def update_from_llm_output(self, llm_output: SentimentLLM) -> bool:
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
