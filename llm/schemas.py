# llm/schemas.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class LLMCall(BaseModel):
    operation: str
    output_model: str
    provider: str
    model: str
    prompt: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    response_raw: str
    response: dict[str, Any]
