# llm/hooks/log.py
from __future__ import annotations

from loguru import logger

from langops.hooks.payload import LLMHookPayload


async def log_request(payload: LLMHookPayload) -> None:
    """Log LLM request and response."""
    if not payload.response_llm:
        # For before hooks, log the request
        logger.debug(
            f"LLM Request: operation={payload.operation_name or 'unknown'}, "
            f"model={payload.llm_model or 'unknown'}"
        )
        return

    # For after hooks, log the response
    logger.info(
        f"LLM Response: operation={payload.operation_name or 'unknown'}, "
        f"model={payload.llm_model or 'unknown'}, "
        f"prompt_chars={len(payload.prompt)}, "
        f"response_chars={len(str(payload.response_llm))}"
    )
