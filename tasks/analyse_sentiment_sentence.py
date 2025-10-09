# ./tasks/sentiment_analysis.py
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import typer
from loguru import logger
from persistence.models.sentence import SentimentAnalysisEntity, SentimentLLM
from persistence.session import get_async_session

from tasks.base import GenericLLMTask
from tasks.prompts.prompt_sentiment import build_sentiment_prompt


async def _find_existing_sentiment(text: str) -> SentimentAnalysisEntity | None:
    text_hash = GenericLLMTask._compute_hash(text)
    from persistence.repository.sentiment_analysis_repo import (
        SentimentAnalysisRepository,
    )

    async with get_async_session() as session:
        repo = SentimentAnalysisRepository(session)
        return await repo.get_by_text_hash(text_hash)


async def run_sentiment_analysis(
    text: str,
    *,
    profile: str | None = None,
    temperature: float | None = None,
    in_context_learning: str | None = None,
    override: bool = False,
    doc_id: int = 1,
) -> tuple[SentimentLLM, str]:
    existing = await _find_existing_sentiment(text)

    if existing is None:
        logger.info(
            "No existing sentiment analysis found, proceeding with new analysis."
        )
        from persistence.models.sentence import SentimentAnalysisEntity, SentimentLLM

        llm_task = GenericLLMTask(
            llm_output_model=SentimentLLM,
            db_entity_model=SentimentAnalysisEntity,
            mongo_coll_name="llm_calls_sentiment",
            profile=profile,
            temperature=temperature,
        )

        prompt = build_sentiment_prompt(text, in_context_learning)
        logger.debug("Prompt prepared")

        result = await llm_task.run(
            user_role="user",
            prompt=prompt,
            operation_name="sentiment_analysis",
            text=text,
            doc_id=doc_id,
        )

    if existing and existing.sentiment is not None and not override:
        logger.info(
            "Existing sentiment analysis found, skipping re-analysis (override=False)"
        )
        from persistence.models.sentence import SentimentLLM

        cached_result = SentimentLLM(
            sentiment=existing.sentiment,
            sentiment_confidence=existing.sentiment_confidence,
        )
        logger.info(f"Using cached sentiment id={existing.id}")
        return cached_result, "cached"

    if existing and override:
        logger.info("Existing sentiment analysis found, re-analyzing (override=True)")
        from persistence.repository.sentiment_analysis_repo import (
            SentimentAnalysisRepository,
        )

        async with get_async_session() as session:
            repo = SentimentAnalysisRepository(session)
            text_hash = GenericLLMTask._compute_hash(text)
            existing_in_session = await repo.get_by_text_hash(text_hash)

            if existing_in_session:
                existing_in_session.sentiment = result.sentiment
                existing_in_session.sentiment_confidence = result.sentiment_confidence
                existing_in_session.sentiment_calls += 1
                existing_in_session.updated_at = datetime.now(timezone.utc)
                await repo.update(existing_in_session)
                await session.commit()
                logger.info(f"Updated sentiment id={existing_in_session.id}")
                return result, "updated"

    return result, "created"


app = typer.Typer(help="Sentiment analysis CLI")


@app.command()
def analyze(
    text: str = typer.Argument(..., help="Text to analyze"),
    profile: str = typer.Option("dev", "--profile", "-p", help="LLM profile"),
    temperature: float = typer.Option(0.0, "--temp", "-t", help="Temperature"),
    in_context_learning: str = typer.Option("zero-shot", "--icl", "-c", help="ICL"),
    override: bool = typer.Option(False, "--override", help="Force re-analysis"),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty JSON output"),
    doc_id: int = typer.Option(1, "--doc-id", help="Document ID"),
):
    async def main():
        result, status = await run_sentiment_analysis(
            text,
            profile=profile,
            temperature=temperature,
            in_context_learning=in_context_learning,
            override=override,
            doc_id=doc_id,
        )

        logger.success(f"Analysis completed with status: {status}")
        return result, status

    result, status = asyncio.run(main())

    output_data = result.model_dump()
    output_data["status"] = status

    output = json.dumps(output_data, indent=2 if pretty else None)
    print(output)


if __name__ == "__main__":
    app()
