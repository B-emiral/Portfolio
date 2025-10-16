# ./hooks/langfuse.py
from __future__ import annotations

import json

from config import settings
from langfuse import Langfuse
from loguru import logger

from hooks.payload import LLMHookPayload


async def langfuse_track(payload: LLMHookPayload) -> None:
    try:
        lf = Langfuse(
            host=settings.langfuse_host,
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
        )

        # Extract data from payload
        resp = payload.response_llm or {}
        operation = payload.operation_name
        input_text = payload.prompt

        # Extract text from response
        output_text = None
        if resp and "content" in resp:
            content = resp.get("content")
            if isinstance(content, list) and content:
                output_text = content[0].get("text")
            elif isinstance(content, str):
                output_text = content

        if not output_text:
            output_text = json.dumps(resp, ensure_ascii=False)

        model = payload.llm_model
        provider = payload.llm_provider

        # Use operation name as trace ID if not provided
        trace_id = getattr(payload, "trace_id", None) or operation

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
        logger.error(f"Langfuse tracking failed: {e}")
