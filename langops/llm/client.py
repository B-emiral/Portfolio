# ./llm/client.py
from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable

import anyio
from loguru import logger

from langops.hooks.payload import LLMHookPayload

from .adapters import BaseLLMAdapter

Hook = Callable[[LLMHookPayload], Awaitable[None]]


class LLMClient:
    def __init__(
        self,
        adapter: BaseLLMAdapter,
        before_hooks: list[Hook] | None = None,
        after_hooks: list[Hook] | None = None,
    ) -> None:
        self.adapter = adapter
        self.before_hooks = before_hooks or []
        self.after_hooks = after_hooks or []

    async def _run_hook(self, hook: Hook, payload: LLMHookPayload) -> None:
        try:
            if inspect.iscoroutinefunction(hook):
                await hook(payload)
            else:
                # Handle synchronous hooks
                await anyio.to_thread.run_sync(hook, payload)
        except Exception as e:
            logger.error(
                f"Hook failure in "
                f"{hook.__name__ if hasattr(hook, '__name__') else str(hook)}: {e}"
            )
            logger.exception("Full hook error traceback:")
            raise

    async def _fire(self, hooks: list[Hook], payload: LLMHookPayload) -> None:
        # Run hooks sequentially to avoid race conditions
        for hook in hooks:
            await self._run_hook(hook, payload)

    # TODO: add @alru_cache(maxsize=128)
    async def request_from_llm_with_hooks(
        self,
        payload: LLMHookPayload,
    ) -> LLMHookPayload | None:
        if self.before_hooks:
            await self._fire(self.before_hooks, payload)

        response = await self.adapter.send(
            messages=payload.messages, temperature=payload.temperature
        )

        payload.response_llm = response
        payload.response_llm_parsed = self.adapter.parse_response(response)

        if payload.llm_output_model and payload.response_llm_parsed:
            try:
                payload.response_llm_instance = payload.llm_output_model(
                    **payload.response_llm_parsed
                )
                logger.success(
                    f"Instantiated {payload.llm_output_model.__name__} "
                    "from LLM response"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to instantiate {payload.llm_output_model.__name__}: {e}"
                )

        if self.after_hooks:
            await self._fire(self.after_hooks, payload)

        return payload
