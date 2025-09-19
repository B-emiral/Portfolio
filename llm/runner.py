# llm/runner.py
from __future__ import annotations

import inspect
import uuid
from typing import Any, Awaitable, Callable, Dict

import anyio
from loguru import logger

from llm.adapters import LLMAdapter

Hook = Callable[[Dict[str, Any]], Awaitable[None]]


class LLMClient:
    """Thin runner that executes adapter + optional before/after hooks."""

    def __init__(
        self,
        adapter: LLMAdapter,
        mongo_coll_name: str | None = None,
        sql_table_name: str | None = None,
        before_hooks: list[Hook] | None = None,
        after_hooks: list[Hook] | None = None,
        output_model_name: str | None = None,
    ) -> None:
        self.adapter = adapter
        self.mongo_coll_name = mongo_coll_name
        self.sql_table_name = sql_table_name
        self.before_hooks = before_hooks
        self.after_hooks = after_hooks
        self.output_model_name = output_model_name

    async def _run_hook(self, hook: Hook, payload: dict[str, Any]) -> None:
        try:
            if inspect.iscoroutinefunction(hook):
                await hook(payload)
            else:
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
        llm_provider: str | None = None,
        llm_model: str | None = None,
        operation: str | None = None,
        **metadata: Any,
    ) -> dict[str, Any]:
        trace_id = str(uuid.uuid4())
        payload: dict[str, Any] = {
            "messages": messages,
            "operation": operation,
            "prompt": prompt,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "trace_id": trace_id,
            "mongo_coll_name": self.mongo_coll_name,
            "sql_table_name": self.sql_table_name,
            "output_model": self.output_model_name,
            **metadata,
        }

        if self.before_hooks:
            await self._fire(self.before_hooks, payload)

        resp = await self.adapter.send(messages=messages, temperature=temperature)
        payload["response"] = resp

        if self.after_hooks:
            await self._fire(self.after_hooks, payload)

        return resp
