# llm/hooks/log.py
from __future__ import annotations

from typing import Any

from loguru import logger


async def log_request(payload: dict[str, Any]) -> None:
    logger.info(
        "LLM request prompt_preview={}",
        (payload.get("prompt") or "")[:200],
        "LLM response prompt_preview={}",
        (payload.get("response") or "")[:200],
    )
