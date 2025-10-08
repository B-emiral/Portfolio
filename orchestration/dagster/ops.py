# ./orchestration/dagster/ops.py
import asyncio

from loguru import logger
from persistence.scripts.add_document import add_document_from_json
from tasks.sentiment_analysis import run_sentiment_analysis
from utils.get_unprocessed_documents import get_unprocessed_documents
from utils.split_sentences import split_sentences_regex

from dagster import Out, op


@op(out=Out(dict))
def ingest_add_document_op(_context, json_path):
    logger.info(f"Ingesting document from {json_path}")
    result = asyncio.run(add_document_from_json(json_path, skip_duplicates=True))
    return {"status": "success", "document": str(result)}


@op(out=Out(list))
def get_unprocessed_documents_op(_context):
    """Fetch unprocessed documents from DB."""
    logger.info("Fetching unprocessed documents from DB...")
    documents = asyncio.run(get_unprocessed_documents())
    logger.info(f"Found {len(documents)} unprocessed documents.")
    return documents


@op(out=Out(list))
def split_sentences_op(_context, documents):
    logger.info("Splitting sentences for unprocessed documents...")
    unprocessed_docs = [doc for doc in documents if not doc.get("processed_at")]
    for doc in unprocessed_docs:
        doc["sentences"] = asyncio.run(split_sentences_regex(doc["content"]))
    results = [
        {"doc_id": doc["id"], "sentences": doc["sentences"]} for doc in unprocessed_docs
    ]
    logger.info(f"Split {len(results)} documents into sentences.")
    return results


@op(out=Out(list))
def analyze_sentences_op(_context, sentences_batch):
    logger.info("Running sentiment analysis on new sentences...")
    analyzed = []
    for doc in sentences_batch:
        for sent in doc["sentences"]:
            result, status = asyncio.run(
                run_sentiment_analysis(sent, doc_id=doc["doc_id"])
            )
            analyzed.append(
                {
                    "doc_id": doc["doc_id"],
                    "text": sent,
                    "sentiment": result.sentiment,
                    "confidence": result.sentiment_confidence,
                    "status": status,
                }
            )
    logger.info(f"Analyzed {len(analyzed)} sentences.")
    return analyzed
