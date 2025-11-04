# ./hooks/langfuse.py
from __future__ import annotations

import json
import time

from config import settings
from langfuse import Langfuse
from loguru import logger

from langops.hooks.payload import LLMHookPayload


async def langfuse_track(payload: LLMHookPayload) -> None:
    try:
        start_time = time.time()

        lf = Langfuse(
            host=settings.langfuse_host,
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
        )

        input_text = payload.prompt
        operation_name = payload.operation_name
        response = payload.response_llm or {}

        # Output text extraction
        output_text = None
        if isinstance(response, dict) and "content" in response:
            content = response.get("content")
            if isinstance(content, list) and content:
                output_text = content[0].get("text")
            elif isinstance(content, str):
                output_text = content
        if not output_text:
            output_text = json.dumps(response, ensure_ascii=False)

        # Token usage
        usage = response.get("usage", {}) if isinstance(response, dict) else {}
        logger.debug(f"LLM usage data: {usage}")
        input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        output_tokens = (
            usage.get("output_tokens") or usage.get("completion_tokens") or 0
        )

        # Metadata
        end_time = time.time()
        metadata = {
            "provider": payload.llm_provider,
            "model": payload.llm_model,
            "latency_seconds": end_time - start_time,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        }

        model = (payload.llm_model or "").strip().lower()

        trace_id = response["id"]
        logger.debug(f"Langfuse trace_id: {trace_id}")

        # Create or link trace
        lf.trace(
            trace_id=trace_id,
            name=operation_name,
            input=input_text,
            output=output_text,
            usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
            metadata=metadata,
        )

        # Create generation
        lf.generation(
            trace_id=trace_id,
            name=operation_name,
            model=model,
            input=input_text,
            output=output_text,
            usage_details={
                "input": input_tokens,
                "output": output_tokens,
            },
            status_message=response.get("stop_reason"),
            start_time=start_time,
            end_time=end_time,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        lf.flush()

    except Exception as e:
        logger.error(f"Langfuse tracking failed: {e}")
