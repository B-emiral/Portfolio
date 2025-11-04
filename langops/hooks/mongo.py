# ./llm/hooks/mongo.py
from __future__ import annotations

from datetime import datetime
from functools import lru_cache

from config import settings
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import WriteConcern

from langops.hooks.payload import LLMHookPayload


@lru_cache
def get_mongo_client() -> AsyncIOMotorClient:
    connection_string = settings.mongo_uri or "mongodb://localhost:27017"

    client = AsyncIOMotorClient(
        connection_string,
        maxPoolSize=10,
        minPoolSize=1,
        serverSelectionTimeoutMS=5000,
    )

    return client


def get_db(database_name: str | None = None) -> AsyncIOMotorDatabase:
    db_name = database_name or settings.mongo_db or "llm_logs"
    client = get_mongo_client()
    return client[db_name]


async def mongo_insert(payload: LLMHookPayload) -> None:
    if not payload.mongo_coll_name or not payload.response_llm:
        logger.debug("MongoDB hook skipped: missing collection name or response")
        return

    try:
        db = get_db()
        collection = db.get_collection(
            payload.mongo_coll_name, write_concern=WriteConcern(w=1)
        )

        doc = {
            "timestamp": datetime.utcnow(),
            "prompt": payload.prompt,
            "messages": payload.messages,
            "temperature": payload.temperature,
            "response": payload.response_llm,
            "operation": payload.operation_name,
            "llm_provider": payload.llm_provider,
            "llm_model": payload.llm_model,
        }

        if payload.text:
            doc["original_text"] = payload.text

        if payload.ref_id:
            doc["ref_id"] = payload.ref_id

        await collection.insert_one(doc)
        logger.debug(f"MongoDB: logged to {payload.mongo_coll_name}")

    except Exception as e:
        logger.error(f"MongoDB hook error: {e}")
