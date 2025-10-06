# ./orchestration/dagster/ops.py
import asyncio

from loguru import logger
from persistence.scripts.add_document import add_document_from_json

from dagster import Out, op


@op(out=Out(dict))
def ingest_add_document_op(_context, json_path):
    logger.info(f"Ingesting document from {json_path}")
    result = asyncio.run(add_document_from_json(json_path, skip_duplicates=True))
    return {"status": "success", "document": str(result)}


@op(out=Out(list))
def split_sentences_op(_context, documents):
    logger.info("Splitting sentences for unprocessed documents...")
    unprocessed_docs = [doc for doc in documents if not doc.get("processed_at")]
    results = [
        {"doc_id": doc["id"], "sentences": ["Example sentence."]}
        for doc in unprocessed_docs
    ]
    logger.info(f"Split {len(results)} documents into sentences.")
    return results


@op(out=Out(list))
def analyze_sentences_op(_context, sentences_batch):
    logger.info("Running sentiment analysis on new sentences...")
    analyzed = []
    for doc in sentences_batch:
        for sent in doc["sentences"]:
            analyzed.append({"text": sent, "sentiment": "positive", "confidence": 0.95})
    logger.info(f"Analyzed {len(analyzed)} sentences.")
    return analyzed
