# llm/hooks/mongo.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from anyio import to_thread
from llm.db import insert_call_mongo
from loguru import logger

from .utils import extract_prompt


async def mongo_insert(payload: dict[str, Any]) -> None:
    resp = payload.get("response")
    now = datetime.now(timezone.utc)
    record = {
        "trace_id": payload.get("trace_id"),
        "operation": payload.get("operation"),
        "output_model": payload.get("output_model"),
        "llm_provider": payload.get("llm_provider"),
        "llm_model": payload.get("llm_model"),
        "mongo_coll_name": payload.get("mongo_coll_name"),
        "prompt": extract_prompt(payload),
        "response": resp,
        "created_at": now,
    }
    try:
        # Offload sync DB call to a worker thread to avoid blocking the event loop
        inserted_id = await to_thread.run_sync(insert_call_mongo, record)
        logger.info(
            "Mongo insert OK | trace_id={} | _id={} | collection name={}",
            record["trace_id"],
            inserted_id,
            record["mongo_coll_name"],
        )
    except Exception as e:
        logger.error("Mongo insert failed: {}", e)
