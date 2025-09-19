# llm/profiles.py
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable

import tomllib as toml  # Py3.11+


class ProfileStore:
    """Resolve llm_provider/llm_model and hook callables from profiles.toml."""

    def __init__(self, path: str | Path = "profiles.toml") -> None:
        self.path = Path(path)
        with self.path.open("rb") as f:
            self._cfg = toml.load(f)

    def _import_from_path(self, dotted: str) -> Callable:
        """Import a function given its dotted path (module.attr)."""
        module_path, attr = dotted.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, attr)

    def _load_hooks(self, names: list[str]) -> list[Callable]:
        """Import hook callables from dotted paths."""
        return [self._import_from_path(name) for name in (names or [])]

    def resolve(self, profile_key: str) -> dict[str, Any]:
        """Resolve profile and hook information for a given profile key."""
        profile = self._cfg.get(profile_key)
        if profile is None:
            raise KeyError(f"Profile not found: {profile_key}")

        # Extract model configuration
        llm_provider = profile.get("llm_provider")
        llm_model = profile.get("llm_model")

        if not llm_provider or not llm_model:
            raise ValueError(
                f"Profile {profile_key} missing required fields: llm_provider, llm_model"
            )

        # Extract hook paths
        before_paths = profile.get("hookset_before", []) or []
        after_paths = profile.get("hookset_after", []) or []

        # Load hook functions
        hookset_before = self._load_hooks(before_paths)
        hookset_after = self._load_hooks(after_paths)

        return {
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "hookset_before": hookset_before,
            "hookset_after": hookset_after,
        }
