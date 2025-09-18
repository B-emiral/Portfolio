from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, Index, String
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class SentimentOut(BaseModel):
    sentiment: SentimentLabel
    confidence: float = Field(ge=0.0, le=1.0)


class Sentence(SQLModel, table=True):
    __tablename__ = "sentences_sentiment"
    __table_args__ = (Index("ix_sentences_doc_text", "doc_id", "text", unique=True),)

    id: int | None = SQLField(default=None, primary_key=True)
    doc_id: int = SQLField(foreign_key="document.id", index=True, nullable=False)

    text: str = SQLField(sa_column=Column(String, nullable=False))

    sentiment_label: SentimentLabel | None = SQLField(
        default=None,
        sa_column=Column(
            SAEnum(SentimentLabel, name="sentiment_label_enum", native_enum=False),
            nullable=True,
            index=True,  # single-column index defined here
        ),
    )
    sentiment_score: float | None = SQLField(
        default=None,
        sa_column=Column(Float, nullable=True),
    )

    sentiment_calls: int = SQLField(default=0, nullable=False)

    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime | None = SQLField(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    def apply_sentiment(self, out: SentimentOut, now: datetime | None = None) -> bool:
        """
        Apply SentimentOut to this Sentence in-memory.
        Returns True if a change was made (so repo can commit/refresh).
        """
        now = now or datetime.now(timezone.utc)
        changed = False

        # Normalize label to Enum safely
        label = (
            out.sentiment
            if isinstance(out.sentiment, SentimentLabel)
            else SentimentLabel(out.sentiment)
        )

        if (self.sentiment_label is None) or (self.sentiment_label != label):
            self.sentiment_label = label
            changed = True

        score = float(out.confidence)
        if (self.sentiment_score is None) or (
            abs((self.sentiment_score or 0.0) - score) > 1e-6
        ):
            self.sentiment_score = score
            changed = True

        if changed:
            self.sentiment_calls = (self.sentiment_calls or 0) + 1
            self.updated_at = now

        return changed
