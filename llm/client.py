# ./llm/client.py
from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, Dict

from loguru import logger

from .adapters import LLMAdapter

Hook = Callable[[Dict[str, Any]], Awaitable[None]]


class LLMClient:
    """Thin runner that executes adapter + optional before/after hooks."""

    def __init__(
        self,
        adapter: LLMAdapter,
        before_hooks: list[Hook] | None = None,
        after_hooks: list[Hook] | None = None,
    ) -> None:
        self.adapter = adapter
        self.before_hooks = before_hooks or []
        self.after_hooks = after_hooks or []

    async def _run_hook(self, hook: Hook, payload: dict[str, Any]) -> None:
        try:
            if inspect.iscoroutinefunction(hook):
                await hook(payload)
            else:
                # if someone provided a sync function
                import anyio

                await anyio.to_thread.run_sync(hook, payload)
        except Exception as e:
            logger.error(
                f"Hook failure in "
                f"{hook.__name__ if hasattr(hook, '__name__') else str(hook)}: {e}"
            )
            logger.exception("Full hook error traceback:")
            # Re-raise to prevent silent failures
            raise

    async def _fire(self, hooks: list[Hook], payload: dict[str, Any]) -> None:
        # Run hooks sequentially instead of parallel to avoid race conditions
        for hook in hooks:
            await self._run_hook(hook, payload)

    async def send(
        self,
        messages: list[dict[str, Any]],
        prompt: str | None = None,
        temperature: float | None = None,
        **metadata: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "messages": messages,
            "prompt": prompt or "",
            **metadata,
        }

        if self.before_hooks:
            await self._fire(self.before_hooks, payload)

        resp = await self.adapter.send(messages=messages, temperature=temperature)
        payload["response"] = resp

        if self.after_hooks:
            await self._fire(self.after_hooks, payload)

        return resp
