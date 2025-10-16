# ./tasks/analyse_sentiment_sentence.py
from __future__ import annotations

import asyncio
import json

import typer
from loguru import logger as log
from persistence.models.sentence import (
    SentenceSentimentEntity,
    SentenceSentimentResponseModel,
)
from persistence.repository.sentence_sentiment_repo import SentenceSentimentRepository
from persistence.session import get_async_session

from tasks.base import GenericLLMTask
from tasks.prompts.prompt_sentiment import build_sentiment_prompt


async def run_sentiment_analysis(
    text: str,
    *,
    ### LLM Client Related
    profile: str | None = None,
    temperature: float | None = None,
    in_context_learning: str | None = None,
    ### Persist Related
    sentence_id: int | None = None,
    persist_override: bool = False,
) -> tuple[SentenceSentimentResponseModel, str]:
    async with get_async_session() as session:
        repo = SentenceSentimentRepository()
        existing = await repo.get_by_sentence_id_and_hash(session, sentence_id, text)

    # The part of the upsert logic outside the upsert() method prevents unnecessary LLM
    if existing and existing.sentiment is not None and not persist_override:
        log.info("Existing sentiment analysis found, skipping re-analysis")
        cached_model = SentenceSentimentResponseModel.model_validate(existing)
        return cached_model, "cached"

    prompt = build_sentiment_prompt(text, in_context_learning)
    log.debug("Prompt prepared")

    llm_task = GenericLLMTask(
        llm_output_model=SentenceSentimentResponseModel,
        db_entity_model=SentenceSentimentEntity,
        mongo_coll_name="llm_calls_sentiment",
        operation_name="sentiment_analysis",
        profile=profile,
    )

    payload = await llm_task.run_llm_request(
        user_role="user",
        prompt=prompt,
        temperature=temperature,
        text=text,
        ref_id=sentence_id,
        ref_field_name="sentence_id",
        repo=SentenceSentimentRepository,
        persist_override=persist_override,
    )

    created_model = SentenceSentimentResponseModel.model_validate(
        payload.response_llm_instance
    )

    return created_model, "created"


app = typer.Typer(help="Run sentiment analysis on text input.")


@app.command()
def analyze(
    text: str = typer.Argument(..., help="Text to analyze"),
    profile: str = typer.Option("dev", "--profile", "-p", help="LLM profile"),
    temperature: float = typer.Option(0.0, "--temp", "-t", help="Temperature"),
    in_context_learning: str = typer.Option(
        "zero-shot", "--icl", "-c", help="ICL mode"
    ),
    persist_override: bool = typer.Option(
        False, "--persist-override", help="Force re-analysis"
    ),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON"),
    sentence_id: int | None = typer.Option(None, "--sentence-id", help="Sentence ID"),
):
    response, status = asyncio.run(
        run_sentiment_analysis(
            text=text,
            profile=profile,
            temperature=temperature,
            in_context_learning=in_context_learning,
            persist_override=persist_override,
            sentence_id=sentence_id,
        )
    )

    log.success(f"Analysis completed with status: {status}")
    print(
        json.dumps(
            {**response.model_dump(), "status": status},
            indent=2 if pretty else None,
        )
    )


if __name__ == "__main__":
    app()
