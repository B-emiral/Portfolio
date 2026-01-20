# ./tasks/base.py
from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar

import anyio

from langops.hooks.payload import LLMHookPayload
from langops.llm.adapters import AnthropicAdapter, AnthropicAdapter2, VertexAIAdapter
from langops.llm.client import LLMClient
from langops.llm.profiles import ProfileStore
from langops.persistence.models.base import BaseLLMResponseModel
from langops.persistence.repository.base_repo import BaseRepository

T_LLM_Output_Model = TypeVar("T_LLM_Output_Model", bound=BaseLLMResponseModel)
T_Entity = TypeVar("T_Entity")
Hook = Callable[[LLMHookPayload], Awaitable[None]]


class GenericLLMTask(Generic[T_LLM_Output_Model, T_Entity]):
    def __init__(
        self,
        llm_output_model: type[T_LLM_Output_Model],
        db_entity_model: type[T_Entity] | None = None,
        mongo_coll_name: str | None = None,
        operation_name: str | None = None,
        profile: str = "dev",
    ):
        self.llm_output_model = llm_output_model
        self.db_entity_model = db_entity_model
        self.mongo_coll_name = mongo_coll_name
        self.operation_name = operation_name
        self.profile = profile

    def _load_profile(self, profile_name: str) -> dict[str, Any]:
        store = ProfileStore()
        return store.resolve(profile_name)

    def _get_adapter(self, llm_provider: str, llm_model: str):
        p = llm_provider.lower().strip()
        m = llm_model.lower().strip()

        if p == "anthropic":
            if m.startswith("claude-3"):
                return AnthropicAdapter(model=llm_model)
            return AnthropicAdapter2(model=llm_model)

        if p in {"vertex", "vertexai", "google", "gcp"}:
            return VertexAIAdapter(model=llm_model)

        raise ValueError(f"Unsupported LLM provider: {llm_provider}")

    async def _run_hook(self, hook: Hook, payload: LLMHookPayload) -> None:
        if inspect.iscoroutinefunction(hook):
            await hook(payload)
        else:
            await anyio.to_thread.run_sync(hook, payload)

    async def _fire(self, hooks: list[Hook], payload: LLMHookPayload) -> None:
        for hook in hooks:
            await self._run_hook(hook, payload)

    async def run(
        self,
        user_role: str,
        prompt: str,
        text: str | None = None,
        ref_id: int | None = None,
        ref_field_name: str | None = None,
        repo: BaseRepository | None = None,
        persist_override: bool = False,
    ) -> LLMHookPayload | None:
        profile = self._load_profile(self.profile)

        adapter = self._get_adapter(
            llm_provider=profile["llm_provider_detection"],
            llm_model=profile["llm_model_detection"],
        )

        client = LLMClient(adapter=adapter)

        payload = LLMHookPayload(
            prompt=prompt,
            messages=[{"role": user_role, "content": prompt}],
            llm_provider=profile["llm_provider_detection"],
            llm_model=profile["llm_model_detection"],
            temperature=profile["temperature_detection"],
            operation_name=self.operation_name,
            llm_output_model=self.llm_output_model,
            db_entity_model=self.db_entity_model,
            repo=repo,
            text=text,
            ref_id=ref_id,
            ref_field_name=ref_field_name,
            persist_override=persist_override,
            mongo_coll_name=self.mongo_coll_name,
        )

        before_hooks = profile.get("hookset_before", [])
        after_hooks = profile.get("hookset_after", [])

        try:
            if before_hooks:
                await self._fire(before_hooks, payload)

            payload = await client.request(payload)

            if after_hooks:
                await self._fire(after_hooks, payload)

            return payload
        finally:
            if hasattr(adapter, "aclose") and callable(getattr(adapter, "aclose")):
                await adapter.aclose()
