# ./persistence/models/base.py
"""Base models and protocols for task entities."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel
from sqlmodel import SQLModel


class LLMOutputModel(BaseModel):
    """Base class for LLM output validation models."""

    pass


@runtime_checkable
class Persistable(Protocol):
    """Protocol for persistable entities."""

    persistable: bool = True

    @classmethod
    def from_llm_output(cls, llm_output: LLMOutputModel, **extra_fields) -> Persistable:
        """Create entity from LLM output and extra fields."""
        ...

    def update_from_llm_output(self, llm_output: LLMOutputModel) -> bool:
        """Update entity from new LLM output. Returns True if changed."""
        ...


T = TypeVar("T", bound=SQLModel)
