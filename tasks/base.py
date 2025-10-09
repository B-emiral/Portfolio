# ./tasks/base.py
"""Base class for LLM tasks with automatic persistence."""

from __future__ import annotations

import hashlib
from typing import Any, Generic, TypeVar

from loguru import logger
from persistence.models.base import (
    LLMOutputModel,
    Persistable,
)  # REFACTOR: Remove persistable

# CHECK
T_LLM_Output_Model = TypeVar("T_LLM_Output_Model", bound=LLMOutputModel)
T_Entity = TypeVar("T_Entity", bound=Persistable)


class GenericLLMTask(Generic[T_LLM_Output_Model, T_Entity]):
    """
    Generic LLM task with automatic validation and persistence.

    Type Parameters:
        T_LLM_Output_Model: LLM output validation model
        T_Entity: Persistable database entity
    """

    def __init__(
        self,
        llm_output_model: type[T_LLM_Output_Model],
        db_entity_model: type[T_Entity] | None = None,
        mongo_coll_name: str | None = None,
        profile: str | None = None,
        temperature: float | None = None,
    ):
        self.llm_output_model = llm_output_model
        self.db_entity_model = db_entity_model
        self.mongo_coll_name = mongo_coll_name
        self.profile = profile
        self.temperature = temperature

    @staticmethod
    # REVIEW: is this needed here or repo?
    def _compute_hash(text: str) -> str:
        """Compute MD5 hash of text."""
        return hashlib.md5(text.encode()).hexdigest()

    def _build_messages(self, user_role: str, content: str) -> list[dict[str, str]]:
        """Build messages for LLM request."""
        return [{"role": user_role, "content": content}]

    def _get_adapter(self, llm_provider: str, llm_model: str):
        """Get appropriate adapter based on provider."""
        from llm.adapters import AnthropicAdapter

        if llm_provider.lower() == "anthropic":
            return AnthropicAdapter(model=llm_model)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

    def _load_profile(self, profile_name: str) -> dict[str, Any]:
        """Load profile configuration."""
        try:
            # TODO:
            from llm.profiles import ProfileStore

            store = ProfileStore()
            return store.resolve(profile_name)
        except Exception as e:
            logger.warning(
                f"Could not load profile '{profile_name}': {e}, using fallback"
            )
            return {
                "llm_provider": "anthropic",
                "llm_model": "claude-3-5-haiku-20241022",
                "hookset_before": [],
                "hookset_after": [],
            }

    async def run(
        self,
        user_role: str,
        prompt: str,
        operation_name: str | None = None,
        text: str | None = None,
        doc_id: int | None = None,
        **metadata: Any,
    ) -> T_LLM_Output_Model:
        """
        Run LLM task with automatic validation and persistence setup.
        """
        from llm.client import LLMClient

        profile_name = self.profile or "dev"
        profile = self._load_profile(profile_name)

        adapter = self._get_adapter(
            llm_provider=profile["llm_provider"],
            llm_model=profile["llm_model"],
        )

        client = LLMClient(
            adapter=adapter,
            before_hooks=profile.get("hookset_before", []),
            after_hooks=profile.get("hookset_after", []),
        )

        messages = self._build_messages(user_role=user_role, content=prompt)

        result = await client.send(
            messages=messages,
            prompt=prompt,
            temperature=self.temperature,
            operation=operation_name,
            llm_output_model=self.llm_output_model,
            db_entity_model=self.db_entity_model,
            analyzed_text=text,
            doc_id=doc_id,
            mongo_coll_name=self.mongo_coll_name,
            output_model=self.llm_output_model.__name__,
            output_model_class=self.llm_output_model,
            llm_provider=profile["llm_provider"],
            llm_model=profile["llm_model"],
            **metadata,
        )

        response_text = result.get("content", [{}])[0].get("text", "")

        try:
            # CHECK
            import json

            parsed = json.loads(response_text)
            validated = self.llm_output_model(**parsed)
            logger.debug(f"Validation OK with {self.llm_output_model.__name__}")
            return validated
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise
