# ./tasks/sentiment_analysis.py
"""Sentiment analysis task using generic framework."""

from __future__ import annotations

import asyncio

import typer
from loguru import logger

from persistence.models.sentence import SentimentAnalysisEntity, SentimentLLM
from tasks.base import GenericLLMTask
from tasks.prompts.prompt_sentiment import build_sentiment_prompt


async def run_sentiment(
    text: str,
    *,
    profile: str | None = None,
    temperature: float | None = None,
    in_context_learning: str | None = None,
) -> SentimentLLM:
    """Run sentiment analysis on text."""

    llm_task = GenericLLMTask(
        llm_output_model=SentimentLLM,
        db_entity_model=SentimentAnalysisEntity,
        mongo_coll_name="llm_calls_sentiment",
        profile=profile,
        temperature=temperature,
    )

    prompt = build_sentiment_prompt(text, in_context_learning)
    logger.debug(f"Prompt:\n{prompt}")

    try:
        result = await llm_task.run(
            user_role="user",
            prompt=prompt,
            operation_name="sentiment_analysis",
            text=text,
        )
        return result
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        raise


app = typer.Typer(help="Run sentiment analysis from the command line.")


@app.command()
def run_cmd(
    text: str = typer.Argument(..., help="Text to analyze."),
    profile: str = typer.Option("dev", "--profile", "-p"),
    temperature: float = typer.Option(0.0, "--temp", "-t"),
    in_context_learning: str = typer.Option("zero-shot", "--in-context-learning", "-c"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Run sentiment analysis from CLI."""
    import json

    result = asyncio.run(
        run_sentiment(
            text,
            profile=profile,
            temperature=temperature,
            in_context_learning=in_context_learning,
        )
    )

    if pretty:
        print(json.dumps(result.model_dump(), indent=2))
    else:
        print(result.model_dump_json())


if __name__ == "__main__":
    app()
