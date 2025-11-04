# llm/hooks/guard.py
from __future__ import annotations

import json
from typing import Any

from guardrails import Guard
from loguru import logger
from pydantic import BaseModel

from langops.hooks.payload import LLMHookPayload


# TODO: Make this adaptor agnostic!
def _extract_text(response: dict[str, Any]) -> tuple[str | None, str]:
    content = response.get("content")
    if isinstance(content, list) and content:
        text = content[0].get("text")
        return (text if isinstance(text, str) else None), "list"
    if isinstance(content, str):
        return content, "str"
    return None, "unknown"


# CHECK: Adaptor agnostic?
def _set_text(response: dict[str, Any], text: str, kind: str) -> None:
    """Set text content in LLM response."""
    if kind == "list":
        if isinstance(response.get("content"), list) and response["content"]:
            response["content"][0]["text"] = text
    elif kind == "str":
        response["content"] = text


async def guard_output(payload: LLMHookPayload) -> None:
    if not payload.response_llm:
        return

    response = payload.response_llm
    raw_text, kind = _extract_text(response)
    if not raw_text:
        return

    output_model = payload.llm_output_model

    if (
        output_model
        and isinstance(output_model, type)
        and issubclass(output_model, BaseModel)
    ):
        # 1) Try JSON parse + Pydantic validation first
        try:
            data = json.loads(raw_text)
            obj = output_model(**data)  # validate against schema
            repaired = obj.model_dump_json()
            _set_text(response, repaired, kind)
            logger.info("Pydantic validation succeeded")
            return
        except Exception:
            pass

        # 2) Use Guardrails to repair to the model schema
        guard = Guard.for_pydantic(output_model)
        result = guard.parse(raw_text, reask_on_fail=False)
        validated = result.validated_output

        if isinstance(validated, BaseModel):
            repaired = validated.model_dump_json()
        elif isinstance(validated, (dict, list)):
            repaired = json.dumps(validated, ensure_ascii=False)
        elif isinstance(validated, str) and validated.strip().startswith("{"):
            repaired = validated
        else:
            logger.warning("Guardrails returned non-JSON; leaving original text")
            return

        _set_text(response, repaired, kind)
        logger.info("Guardrails repair applied")
        return

    # No model provided: only normalize valid JSON
    try:
        data = json.loads(raw_text)
        _set_text(response, json.dumps(data, ensure_ascii=False), kind)
        logger.info("Response normalized to JSON")
    except Exception:
        return
