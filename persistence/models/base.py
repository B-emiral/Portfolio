# ./persistence/models/base.py
from __future__ import annotations

from typing import ClassVar, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel
from sqlmodel import SQLModel


class LLMOutputModel(BaseModel):
    pass


@runtime_checkable
class Persistable(Protocol):
    persistable: ClassVar[bool]

    @classmethod
    def from_llm_output(
        cls, llm_output: LLMOutputModel, **extra_fields
    ) -> "Persistable": ...

    def update_from_llm_output(self, llm_output: LLMOutputModel) -> bool: ...


T = TypeVar("T", bound=SQLModel)
