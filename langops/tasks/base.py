# ./tasks/base.py
"""Base class for LLM tasks with automatic persistence."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from loguru import logger

from langops.hooks.payload import LLMHookPayload
from langops.llm.client import LLMClient
from langops.llm.profiles import ProfileStore
from langops.persistence.models.base import BaseLLMResponseModel
from langops.persistence.repository.base_repo import BaseRepository

T_LLM_Output_Model = TypeVar("T_LLM_Output_Model", bound=BaseLLMResponseModel)
T_Entity = TypeVar("T_Entity")


class GenericLLMTask(Generic[T_LLM_Output_Model, T_Entity]):
    """
    Generic LLM task with automatic validation and persistence.

    Type Parameters:
        T_LLM_Output_Model: LLM output validation model
        T_Entity: Database entity
    """

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

    def _get_adapter(self, llm_provider: str, llm_model: str):
        """Get appropriate adapter based on provider."""
        from langops.llm.adapters import AnthropicAdapter

        if llm_provider.lower() == "anthropic":
            return AnthropicAdapter(model=llm_model)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

    def _load_profile(self, profile_name: str) -> dict[str, Any]:
        """Load profile configuration."""
        try:
            store = ProfileStore()
            return store.resolve(profile_name)
        except Exception as e:
            logger.warning(
                f"Could not load profile '{profile_name}': {e}, using fallback"
            )
            raise Exception("Profile loading failed")
            # return {
            #     "llm_provider": "anthropic",
            #     "llm_model": "claude-3-5-haiku-20241022",
            #     "hookset_before": [],
            #     "hookset_after": [],
            # }

    async def run_llm_request(
        self,
        user_role: str,
        prompt: str,
        temperature: float | None = None,
        text: str | None = None,
        ref_id: int | None = None,
        ref_field_name: str | None = None,
        repo: BaseRepository | None = None,
        persist_override: bool = False,
    ) -> LLMHookPayload | None:
        profile = self._load_profile(self.profile)

        adapter = self._get_adapter(
            llm_provider=profile["llm_provider"],
            llm_model=profile["llm_model"],
        )

        client = LLMClient(
            adapter=adapter,
            before_hooks=profile.get("hookset_before", []),
            after_hooks=profile.get("hookset_after", []),
        )

        payload = LLMHookPayload(
            prompt=prompt,
            messages=[{"role": user_role, "content": prompt}],
            temperature=temperature,
            operation_name=self.operation_name,
            llm_output_model=self.llm_output_model,
            db_entity_model=self.db_entity_model,
            repo=repo,
            text=text,
            ref_id=ref_id,
            ref_field_name=ref_field_name,
            persist_override=persist_override,
            mongo_coll_name=self.mongo_coll_name,
            llm_provider=profile["llm_provider"],
            llm_model=profile["llm_model"],
        )

        payload = await client.request_from_llm_with_hooks(payload)

        return payload
