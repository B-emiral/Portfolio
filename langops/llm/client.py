# ./llm/client.py
from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from langops.hooks.payload import LLMHookPayload

from .adapters import BaseLLMAdapter

Hook = Callable[[LLMHookPayload], Awaitable[None]]


class LLMError(RuntimeError):
    pass


class LLMResponseNotJSON(LLMError):
    pass


class LLMResponseValidationError(LLMError):
    pass


class LLMClient:
    def __init__(self, adapter: BaseLLMAdapter) -> None:
        self.adapter = adapter

    def _extract_json_dict(self, content: Any) -> dict[str, Any]:
        if isinstance(content, dict):
            return content
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except Exception as e:
                raise LLMResponseNotJSON(f"Response is not valid JSON: {e}") from e
            if not isinstance(parsed, dict):
                raise LLMResponseNotJSON("JSON root is not an object")
            return parsed
        raise LLMResponseNotJSON(f"Unsupported content type: {type(content).__name__}")

    # TODO: add @alru_cache(maxsize=128)
    async def request(self, payload: LLMHookPayload) -> LLMHookPayload:
        if payload.llm_output_model is None:
            raise LLMResponseValidationError("llm_output_model is required")

        response = await self.adapter.send(
            messages=payload.messages,
            temperature=payload.temperature,
            response_model=payload.llm_output_model,
        )

        payload.response_llm = response
        payload.llm_model = response.get("model")

        content = response.get("content")
        parsed = self._extract_json_dict(content)

        payload.response_llm_parsed = parsed
        payload.response_llm_instance = payload.llm_output_model(**parsed)

        return payload
