# ./llm/adapters.py
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import anthropic
import httpx
from anthropic import AsyncAnthropic
from anthropic._exceptions import APIStatusError
from config import settings
from google import genai
from google.genai import types
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


class LLMError(RuntimeError):
    pass


class LLMResponseValidationError(LLMError):
    pass


class LLMStructuredOutputRequired(LLMError):
    pass


class BaseLLMAdapter(ABC):
    provider_name: str

    @abstractmethod
    async def send(
        self,
        *,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        raise NotImplementedError


class AnthropicAdapter(BaseLLMAdapter):
    provider_name = "anthropic.3x"

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
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


class AnthropicAdapter2(BaseLLMAdapter):
    provider_name = "anthropic.4x"

    def __init__(self, model: str, api_key: str | None = None):
        self.model = model
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key or settings.anthropic_api_key
        )

    async def send(
        self,
        messages: list[dict],
        temperature: float | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs,
    ):
        request_params = {
            "model": self.model,
            "messages": messages,
            # TODO: remove hardcoded max tokens
            "max_tokens": kwargs.get("max_tokens", 8000),
        }

        if temperature is not None:
            request_params["temperature"] = temperature

        if response_model:
            tool_name = response_model.__name__
            request_params["tools"] = [
                {
                    "name": tool_name,
                    "description": f"Extract structured data as {tool_name}",
                    "input_schema": response_model.model_json_schema(),
                }
            ]
            request_params["tool_choice"] = {"type": "tool", "name": tool_name}

        response = await self.client.messages.create(**request_params)

        # Tool use response handling
        if response_model and response.stop_reason == "tool_use":
            for content_block in response.content:
                if content_block.type == "tool_use":
                    return {
                        "content": content_block.input,  # ✅ Dict directly
                        "model": response.model,
                        "usage": {
                            "input_tokens": response.usage.input_tokens,
                            "output_tokens": response.usage.output_tokens,
                        },
                    }

        # Fallback: text response (shouldn't happen with tool_choice)
        if response.content and len(response.content) > 0:
            first_block = response.content[0]
            if hasattr(first_block, "text"):
                content = first_block.text
            elif hasattr(first_block, "input"):
                content = first_block.input
            else:
                content = "{}"
        else:
            content = "{}"

        return {
            "content": content,
            "model": response.model,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }


class VertexAIAdapter(BaseLLMAdapter):
    provider_name = "vertexai"

    def __init__(self, model) -> None:
        self.model = model
        project_id = settings.vertexai_project
        region = settings.vertexai_location
        sa_file = settings.vertexai_service_account_path
        api_version = settings.vertexai_genai_api_version
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]

        if not project_id:
            raise RuntimeError("Missing Vertex AI project in settings")

        credentials = None
        if sa_file:
            credentials = ServiceAccountCredentials.from_service_account_file(
                sa_file,
                scopes=scopes,
            )

        http_options = (
            types.HttpOptions(api_version=api_version) if api_version else None
        )

        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location=region,
            credentials=credentials,
            http_options=http_options,
        ).aio

    async def aclose(self) -> None:
        if hasattr(self.client, "aclose"):
            await self.client.aclose()

    async def send(
        self,
        *,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if response_model is None:
            raise LLMStructuredOutputRequired(
                "VertexAI requires response_model for structured output"
            )

        system_text = "\n".join(
            (m.get("content") or "").strip()
            for m in messages
            if (m.get("role") or "").lower() == "system"
        ).strip()

        contents: list[types.Content] = []
        for m in messages:
            role = (m.get("role") or "user").lower()
            if role == "system":
                continue
            text = (m.get("content") or "").strip()
            if not text:
                continue
            part = types.Part.from_text(text=text)
            if role == "assistant":
                contents.append(types.Content(role="model", parts=[part]))
            else:
                contents.append(types.Content(role="user", parts=[part]))

        cfg: dict[str, Any] = {"max_output_tokens": kwargs.get("max_tokens", 8000)}
        if system_text:
            cfg["system_instruction"] = system_text
        if temperature is not None:
            cfg["temperature"] = temperature

        cfg["response_mime_type"] = "application/json"
        cfg["response_schema"] = response_model

        resp = await self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(**cfg),
        )

        parsed = getattr(resp, "parsed", None)
        if parsed is None:
            raise LLMStructuredOutputRequired("VertexAI did not return parsed output")

        if isinstance(parsed, BaseModel):
            content: Any = parsed.model_dump()
        elif isinstance(parsed, dict):
            content = parsed
        else:
            raise LLMStructuredOutputRequired(
                f"VertexAI parsed output is {type(parsed).__name__}, expected dict"
            )

        um = getattr(resp, "usage_metadata", None)
        usage = {
            "input_tokens": getattr(um, "prompt_token_count", None) if um else None,
            "output_tokens": getattr(um, "candidates_token_count", None)
            if um
            else None,
        }

        return {
            "content": content,
            "model": getattr(resp, "model", None) or self.model,
            "usage": usage,
        }
