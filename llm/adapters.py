# llm/adapters.py
from __future__ import annotations

import json
from typing import Any

import httpx
from anthropic import AsyncAnthropic
from anthropic._exceptions import APIStatusError
from config import settings
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


class BaseLLMAdapter:
    async def parse_response(self, raw_response: dict) -> dict:
        raise NotImplementedError

    async def send(
        self,
        *,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class AnthropicAdapter(BaseLLMAdapter):
    """Anthropic adapter with tenacity-based retry handling."""

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = AsyncAnthropic(api_key=api_key or settings.anthropic_api_key)

    @staticmethod
    def parse_response(raw_response: dict) -> dict:
        try:
            text_json = raw_response["content"][0].get("text", "{}")
            return json.loads(text_json)
        except Exception:
            return {}

    # server-level retry
    @retry(
        wait=wait_exponential(multiplier=0.5, max=8),
        stop=stop_after_attempt(3),
        retry=retry_if_exception(
            lambda e: (
                # Retry on rate limiting (429)
                (isinstance(e, APIStatusError) and e.status_code == 429)
                # Retry on server errors (5xx)
                or (isinstance(e, APIStatusError) and 500 <= e.status_code < 600)
                # Retry on network timeouts
                or isinstance(e, TimeoutError)
                # Retry on connection errors
                or isinstance(
                    e,
                    (
                        ConnectionError,
                        httpx.ConnectError,
                        httpx.ReadTimeout,
                        httpx.WriteTimeout,
                    ),
                )
            )
        ),
    )
    async def send(
        self,
        *,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
    ) -> dict[str, Any]:
        resp = await self.client.messages.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=temperature if temperature is not None else self.temperature,
        )

        # Convert response to dict for consistent interface
        return resp.model_dump() if hasattr(resp, "model_dump") else resp.__dict__
