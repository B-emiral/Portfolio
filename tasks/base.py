# tasks/base.py
from __future__ import annotations

import json

from llm.adapters import AnthropicAdapter
from llm.profiles import ProfileStore
from llm.runner import LLMClient
from loguru import logger
from pydantic import BaseModel, ValidationError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


def _extract_json(text: str) -> str:
    """Extract the first JSON object from a possibly noisy string."""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


class GenericLLMTask:
    """
    Generic task runner: sends a prompt, validates with Pydantic.
    Designed to be subclassed for specific task types.
    """

    def __init__(
        self,
        *,
        output_model: type[BaseModel],
        profile: str,
        temperature: float = 0.0,
        sql_persistable: bool = False,
    ) -> None:
        self.output_model = output_model
        self.profile_key = profile
        self.temperature = temperature
        self.sql_persistable = sql_persistable

        # Resolve profile config
        store = ProfileStore()
        resolved = store.resolve(self.profile_key)

        # Create adapter based on provider
        provider = resolved["provider"]  # Dict access with []
        model = resolved["model"]

        if provider == "anthropic":
            adapter = AnthropicAdapter(model=model)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        # Create client with adapter and hooks
        self.client = LLMClient(
            adapter=adapter,
            before_hooks=resolved["before_hooks"],
            after_hooks=resolved["after_hooks"],
        )
        self.provider = provider
        self.model = model

    async def _parse_and_validate(self, text_out: str) -> BaseModel:
        candidate = _extract_json(text_out).strip()
        data = json.loads(candidate)
        obj = self.output_model(**data)
        logger.debug("Validation OK with {}", self.output_model.__name__)
        return obj

    @retry(
        wait=wait_exponential(multiplier=0.3, max=5),
        stop=stop_after_attempt(2),
        retry=retry_if_exception(
            lambda e: (
                isinstance(
                    e,
                    (
                        ValidationError,
                        json.JSONDecodeError,
                        KeyError,
                        ValueError,
                        TypeError,
                    ),
                )
            )
        ),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True,
    )
    async def run(
        self, *, user_role: str, prompt: str, operation: str, output_model: str
    ) -> BaseModel:
        """Single network call; only parsing/validation is retried."""
        messages = [{"role": user_role, "content": prompt}]

        resp = await self.client.send(
            messages,
            operation=operation,
            prompt=prompt,
            temperature=self.temperature,
            provider=self.provider,
            model=self.model,
            output_model=output_model,
        )

        # Extract text from response
        content = resp.get("content")
        if isinstance(content, list) and content:
            text_out = content[0].get("text") or ""
        elif isinstance(content, str):
            text_out = content
        else:
            text_out = json.dumps(resp, ensure_ascii=False)

        # Retry only this step on validation/JSON errors
        return await self._parse_and_validate(text_out)
