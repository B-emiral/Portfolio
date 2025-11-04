# ./hooks/persist.py

from __future__ import annotations

from loguru import logger

from langops.hooks.payload import LLMHookPayload
from langops.persistence.session import get_async_session


async def persist_sql(payload: LLMHookPayload) -> None:
    if not payload.repo or not payload.text or not payload.response_llm:
        logger.debug("Persist hook skipped: missing required data")
        return

    try:
        async with get_async_session() as session:
            await session.begin()

            repo = payload.repo()

            if payload.llm_output_model and repo:
                await repo.upsert(
                    session=session,
                    sentence_id=payload.ref_id,
                    text=payload.text,
                    response_llm_instance=payload.response_llm_instance,
                    persist_override=payload.persist_override,
                )

            await session.commit()
    except Exception as e:
        logger.exception(f"Error in persist hook: {e}")
        raise
