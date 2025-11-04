# ./hooks/payload.py

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from langops.persistence.models.base import BaseEntityModel, BaseLLMResponseModel
from langops.persistence.repository.base_repo import BaseRepository


class LLMHookPayload(BaseModel):
    prompt: str
    messages: list[dict[str, str]]
    temperature: float | None = None
    operation_name: str | None = None

    llm_output_model: type[BaseLLMResponseModel] | None = None
    db_entity_model: type[BaseEntityModel] | None = None
    repo: type[BaseRepository] | None = None

    text: str | None = None
    ref_id: int | None = None
    ref_field_name: str | None = None
    persist_override: bool = Field(default=False)
    mongo_coll_name: str | None = None

    llm_provider: str | None = None
    llm_model: str | None = None

    response_llm: dict[str, Any] | None = None
    response_llm_parsed: dict[str, Any] | None = None
    response_llm_instance: BaseLLMResponseModel | None = None

    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True
