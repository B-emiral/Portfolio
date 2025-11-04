# ./persistence/models/sentence.py
from __future__ import annotations

from enum import Enum

from pydantic import Field as PydField
from sqlalchemy import Column, Float, Index, String
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field as SQLField
from sqlmodel import Relationship

from langops.persistence.models.base import BaseEntityModel, BaseLLMResponseModel


class SentenceType(str, Enum):
    CLOSED_CAPTION = "CLOSED_CAPTION"
    INFORMATION = "INFORMATION"
    LITERARY = "LITERARY"
    OTHER = "OTHER"


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class SentenceSentimentResponseModel(BaseLLMResponseModel):
    sentiment: SentimentLabel
    sentiment_confidence: float = PydField(ge=0.0, le=1.0)


class SentenceEntity(BaseEntityModel, table=True):
    __tablename__ = "sentences"
    id: int | None = SQLField(default=None, primary_key=True)

    doc_id: int = SQLField(foreign_key="documents.id", index=True, nullable=True)
    sentence_type: SentenceType | None = SQLField(
        sa_column=Column(SAEnum(SentenceType, name="sentence_type_enum"), nullable=True)
    )
    text: str = SQLField(sa_column=Column(String, nullable=False))
    text_hash: str = SQLField(sa_column=Column(String, nullable=False, index=True))

    # Orbit Relations
    sentiment_analysis: SentenceSentimentEntity = Relationship(
        back_populates="sentence",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "uselist": False},
    )


class SentenceSentimentEntity(BaseEntityModel, table=True):
    __tablename__ = "sentences_sentiment"
    id: int | None = SQLField(default=None, primary_key=True)
    # ix_<table>_<column>
    __table_args__ = (Index("ix_sentences_doc_text", "sentence_id", unique=True),)

    sentence_id: int = SQLField(foreign_key="sentences.id", index=True, nullable=False)

    sentiment: SentimentLabel | None = SQLField(
        sa_column=Column(
            SAEnum(SentimentLabel, name="sentiment_label_enum"), nullable=True
        )
    )
    sentiment_confidence: float | None = SQLField(
        sa_column=Column(Float, nullable=True)
    )
    sentiment_calls: int = SQLField(default=0, nullable=False)

    # Orbit Relations
    sentence: SentenceEntity = Relationship(back_populates="sentiment_analysis")

    @classmethod
    def from_llm_output(
        cls,
        llm_output: SentenceSentimentResponseModel,
        sentence_id: int,
    ) -> SentenceSentimentEntity:
        return cls(
            sentence_id=sentence_id,
            sentiment=llm_output.sentiment,
            sentiment_confidence=llm_output.sentiment_confidence,
            sentiment_calls=1,
        )
