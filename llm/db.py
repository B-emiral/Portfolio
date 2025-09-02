# llm/db.py
from __future__ import annotations

import json
from typing import Any

from config import settings
from loguru import logger
from pymongo import MongoClient

from llm.schemas import LLMCall

client = MongoClient(settings.mongo_uri)
db = client[settings.mongo_db]
coll = db[settings.mongo_collection]


def _json_default(o: Any) -> Any:
    if hasattr(o, "model_dump"):
        try:
            return o.model_dump()
        except Exception:
            pass
    if hasattr(o, "__dict__"):
        try:
            return o.__dict__
        except Exception:
            pass
    return str(o)


def insert_call_mongo(data: dict):
    response = data.get("response")

    # Keep both dict and raw string for auditability
    if isinstance(response, dict):
        data["response_raw"] = json.dumps(
            response, ensure_ascii=False, default=_json_default
        )
    elif isinstance(response, str):
        data["response_raw"] = response
        try:
            data["response"] = json.loads(response)
        except json.JSONDecodeError:
            data["response"] = {"raw": response}
    else:
        data["response_raw"] = json.dumps(
            response, ensure_ascii=False, default=_json_default
        )
        try:
            data["response"] = json.loads(data["response_raw"])
        except Exception:
            data["response"] = {"raw": data["response_raw"]}

    validated = LLMCall(**data)
    result = coll.insert_one(validated.model_dump())
    logger.debug(f"Inserted into Mongo _id={result.inserted_id}")
    return result.inserted_id
