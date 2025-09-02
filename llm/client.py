# llm/client.py
from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, Dict

import anyio
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
                await anyio.to_thread.run_sync(hook, payload)
        except Exception as e:
            logger.error("Hook failure: {}", e)

    async def _fire(self, hooks: list[Hook], payload: dict[str, Any]) -> None:
        async with anyio.create_task_group() as tg:
            for h in hooks:
                tg.start_soon(self._run_hook, h, payload)

    async def send(
        self,
        messages: list[dict[str, Any]],
        prompt: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "messages": messages,
            "prompt": prompt or "",
        }

        if self.before_hooks:
            await self._fire(self.before_hooks, payload)

        resp = await self.adapter.send(messages=messages, temperature=temperature)
        payload["response"] = resp

        if self.after_hooks:
            await self._fire(self.after_hooks, payload)

        return resp
