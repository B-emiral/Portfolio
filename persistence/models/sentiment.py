from typing import Literal

from pydantic import BaseModel, Field


class SentimentIn(BaseModel):
    sentence: str


class SentimentOut(BaseModel):
    sentiment: Literal["positive", "neutral", "negative"]
    confidence: float = Field(ge=0.0, le=1.0)
