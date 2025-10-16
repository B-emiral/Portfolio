# ./orchestration/dagster/ops.py
import asyncio

from loguru import logger
from persistence.models.sentence import SentenceType
from persistence.repository.sentence_repo import SentenceRepository
from persistence.repository.sentiment_analysis_repo import SentenceSentimentRepository
from persistence.session import get_async_session
from tasks.add_document import add_document_from_json
from tasks.analyse_sentiment_sentence import run_sentiment_analysis
from tasks.split_sentences import split_sentences_regex

from dagster import Out, op


@op(out=Out(dict))
def ingest_add_document_op(_context, json_path):
    logger.info(f"Ingesting document from {json_path}")
    result = asyncio.run(add_document_from_json(json_path, skip_duplicates=True))
    return {"status": "success", "document": str(result)}


@op(out=Out(None))
async def split_sentences_and_persist_op(_context):
    logger.info("Splitting sentences for unprocessed documents...")

    unprocessed_docs = None
    async with get_async_session() as session:
        unprocessed_docs = await SentenceRepository().get_unprocessed(session)
        for doc in unprocessed_docs:
            sentences = await split_sentences_regex(doc.content)

            repo = SentenceRepository()
            for sent in sentences:
                entity = repo.entity(
                    sentence_type=SentenceType.OTHER,
                    text=sent,
                    text_hash=repo.compute_hash(sent),
                    **{repo.fk_field: doc.id},
                )
                await repo.create(session, entity)

        logger.info(f"Split {len(unprocessed_docs)} documents into sentences.")


@op(out=Out(list))
async def analyse_new_sentences_sentiment_and_persist_op(_context):
    logger.info("Running sentiment analysis on new sentences...")
    analyzed = []
    unprocessed_sentences = None
    async with get_async_session() as session:
        unprocessed_sentences = await SentenceSentimentRepository.get_unprocessed(
            session
        )
        for sentence in unprocessed_sentences:
            model, status = await run_sentiment_analysis(
                text=sentence.text, sentence_id=sentence.id, persist_override=False
            )
            logger.info(f"Analyzed {model.__class__.__name__} with status {status}")
    return analyzed
