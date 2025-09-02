# tasks/sentiment.py
from __future__ import annotations

import json

import anyio
import typer
from data.sentence_w_sentiment import SentimentOut
from loguru import logger

from tasks.base import GenericLLMTask
from tasks.prompts.prompt_sentiment import build_sentiment_prompt

DEFAULT_PROFILE = "dev"


def make_task(
    *,
    profile: str = DEFAULT_PROFILE,
    temperature: float = 0.0,
) -> GenericLLMTask:
    return GenericLLMTask(
        output_model=SentimentOut,
        profile=profile,
        temperature=temperature,
    )


async def run_sentiment(
    text: str,
    *,
    profile: str | None = None,
    temperature: float | None = None,
    strategy: str = "basic",
) -> SentimentOut:
    profile = profile or DEFAULT_PROFILE
    task = make_task(
        profile=profile,
        temperature=temperature if temperature is not None else 0.0,
    )
    prompt = build_sentiment_prompt(text, strategy=strategy)
    logger.debug("Prompt:\n{}", prompt)
    try:
        result = await task.run(
            user_role="user",
            prompt=prompt,
            operation=run_sentiment.__name__,
            output_model=SentimentOut.__name__,
        )
        return result
    except Exception as e:
        logger.error("run_sentiment failed after retries for input={!r}: {}", text, e)
        return SentimentOut(sentiment="error", confidence=0.0)


app = typer.Typer(help="Run sentiment analysis from the command line.")


@app.command()
def run_cmd(
    text: str = typer.Argument(..., help="Text to analyze."),
    profile: str = typer.Option(DEFAULT_PROFILE, "--profile", "-p"),
    temperature: float = typer.Option(0.0, "--temp", "-t"),
    strategy: str = typer.Option("basic", "--strategy", "-s"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    if not (0.0 <= temperature <= 1.0):
        raise typer.BadParameter("temperature must be between 0.0 and 1.0")

    async def _main():
        result = await run_sentiment(
            text,
            profile=profile,
            temperature=temperature,
            strategy=strategy,
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
