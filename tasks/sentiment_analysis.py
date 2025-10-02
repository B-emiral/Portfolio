# tasks/sentiment_analysis.py
from __future__ import annotations

import json

import anyio
import typer
from loguru import logger
from persistence.models.sentence import SentimentOut

from tasks.base import GenericLLMTask
from tasks.prompts.prompt_sentiment import build_sentiment_prompt


async def run_sentiment(
    text: str,
    *,
    profile: str | None,
    temperature: float | None,
    in_context_learning: str | None,
) -> SentimentOut:
    profile = profile

    llm_task = GenericLLMTask(
        output_model=SentimentOut,
        mongo_coll_name="llm_calls_generic",
        sql_table_name="sentiment_generic",
        profile=profile,
        temperature=temperature,
    )

    prompt = build_sentiment_prompt(text, in_context_learning)
    logger.debug("Prompt:\n{}", prompt)
    try:
        result = await llm_task.run(
            user_role="user",
            prompt=prompt,
            operation_name=run_sentiment.__name__,
        )
        return result
    except Exception as e:
        logger.error("run_sentiment failed after retries for input={!r}: {}", text, e)
        return SentimentOut(sentiment="error", confidence=0.0)


app = typer.Typer(help="Run sentiment analysis from the command line.")


@app.command()
def run_cmd(
    text: str = typer.Argument(..., help="Text to analyze."),
    profile: str = typer.Option("dev", "--profile", "-p"),
    temperature: float = typer.Option(0.0, "--temp", "-t"),
    in_context_learning: str = typer.Option("zero-shot", "--in-context-learning", "-c"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """
    Run sentiment analysis on TEXT and print the JSON result.
    python3 tasks/sentiment_analysis.py run-cmd 'I love this!' --pretty
    """
    if not (0.0 <= temperature <= 1.0):
        raise typer.BadParameter("temperature must be between 0.0 and 1.0")
    if not text or not text.strip():
        raise typer.BadParameter("text must be a non-empty string")

    async def _main():
        result = await run_sentiment(
            text,
            profile=profile,
            temperature=temperature,
            in_context_learning=in_context_learning,
        )
        return result.model_dump()

    try:
        payload = anyio.run(_main)
    except Exception:
        logger.exception("Sentiment CLI run failed")
        raise typer.Exit(code=1)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None))


if __name__ == "__main__":
    app()
