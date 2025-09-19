# llm/hooks/langfuse.py
from __future__ import annotations

import json
from typing import Any

from config import settings
from langfuse import Langfuse
from loguru import logger

from .utils import extract_prompt, extract_text


async def langfuse_track(payload: dict[str, Any]) -> None:
    try:
        lf = Langfuse(
            host=settings.langfuse_host,
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
        )
        resp: dict[str, Any] = payload.get("response") or {}
        operation = payload.get("operation")
        input_text = extract_prompt(payload)
        output_text = extract_text(resp) or json.dumps(resp, ensure_ascii=False)
        model = payload.get("llm_model")
        provider = payload.get("llm_provider")
        trace_id = payload.get("trace_id")
        logger.debug(f"Langfuse trace_id: {trace_id}")
        lf.trace(
            trace_id=trace_id, name=f"{operation}", input=input_text, output=output_text
        )
        lf.generation(
            name=operation,
            model=model,
            provider=provider,
            input=input_text,
            output=output_text,
            tags=[
                f"provider:{provider}",
                f"model:{model}",
            ],
            trace_id=trace_id,
        )

        lf.flush()
    except Exception as e:
        logger.error("Langfuse tracking failed: {}", e)
