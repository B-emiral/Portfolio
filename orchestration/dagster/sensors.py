# ./orchestration/dagster/sensors.py
import asyncio
import hashlib
import time
from pathlib import Path

from persistence.repository.sentence_repo import SentenceRepository
from persistence.repository.sentiment_analysis_repo import SentenceSentimentRepository
from persistence.session import get_async_session

from dagster import DefaultSensorStatus, RunRequest, SkipReason, sensor

from .jobs import (
    analyse_new_sentences_sentiment_job,
    ingest_new_documents_job,
    split_new_docs_into_sentences_and_persist_job,
)


@sensor(
    job=ingest_new_documents_job,
    required_resource_keys={"settings"},
    minimum_interval_seconds=10,
    default_status=DefaultSensorStatus.RUNNING,
)
def ingest_new_documents_sensor(context):
    settings = context.resources.settings
    watch_dirs = [Path(d) for d in settings["watch"]["dirs"]]
    pattern = settings["watch"]["glob"]

    last_mtime = float(context.cursor) if context.cursor else 0.0

    candidates = []
    for watch_dir in watch_dirs:
        for file in watch_dir.glob(pattern):
            try:
                mtime = file.stat().st_mtime
            except FileNotFoundError:
                continue
            if mtime > last_mtime:
                candidates.append((file, mtime))

    if not candidates:
        yield SkipReason("No new or updated files detected.")
        return

    candidates.sort(key=lambda x: x[1])
    max_mtime = last_mtime

    for file, mtime in candidates:
        max_mtime = max(max_mtime, mtime)
        run_key = f"{str(file)}::{int(mtime)}"
        yield RunRequest(
            run_key=run_key,
            run_config={
                "ops": {
                    "ingest_new_documents_graph": {
                        "ops": {
                            "ingest_add_document_op": {
                                "inputs": {"json_path": {"value": str(file)}}
                            }
                        }
                    }
                }
            },
        )

    context.update_cursor(str(max_mtime))


@sensor(
    job=split_new_docs_into_sentences_and_persist_job,
    minimum_interval_seconds=5,
    default_status=DefaultSensorStatus.RUNNING,
)
def split_new_docs_into_sentences_and_persist_sensor(context):
    async def fetch_unprocessed_ids():
        async with get_async_session() as session:
            docs = await SentenceRepository().get_unprocessed(session)
            return sorted(d.id for d in docs)

    unprocessed_ids = asyncio.run(fetch_unprocessed_ids())
    if not unprocessed_ids:
        yield SkipReason("No documents waiting for sentence split.")
        return

    fingerprint_src = ",".join(map(str, unprocessed_ids))
    fingerprint = hashlib.md5(fingerprint_src.encode("utf-8")).hexdigest()

    if context.cursor == fingerprint:
        yield SkipReason("No change in unprocessed document set.")
        return

    run_key = f"split_new_docs_{fingerprint[:12]}_{int(time.time())}"
    context.update_cursor(fingerprint)
    yield RunRequest(run_key=run_key)


@sensor(
    job=analyse_new_sentences_sentiment_job,
    minimum_interval_seconds=5,
    default_status=DefaultSensorStatus.RUNNING,
)
def analyse_new_sentences_sentiment_sensor(context):
    async def fetch_unprocessed_sentence_ids():
        async with get_async_session() as session:
            sentences = await SentenceSentimentRepository().get_unprocessed(session)
            return sorted(s.id for s in sentences)

    unprocessed_ids = asyncio.run(fetch_unprocessed_sentence_ids())
    if not unprocessed_ids:
        yield SkipReason("No new sentences awaiting sentiment analysis.")
        return

    fingerprint_src = ",".join(map(str, unprocessed_ids))
    fingerprint = hashlib.md5(fingerprint_src.encode("utf-8")).hexdigest()

    if context.cursor == fingerprint:
        yield SkipReason("No change in unprocessed sentence set.")
        return

    run_key = f"analyse_sentiments_{fingerprint[:12]}_{int(time.time())}"
    context.update_cursor(fingerprint)
    yield RunRequest(run_key=run_key)
