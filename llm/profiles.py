# llm/profiles.py
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import tomllib as toml  # Py3.11+


class ProfileStore:
    """Resolve provider/model and hook callables from profiles.toml env key."""

    def __init__(self, path: str | Path = "profiles.toml") -> None:
        self.path = Path(path)
        with self.path.open("rb") as f:
            self._cfg = toml.load(f)

    def _import_from_path(self, dotted: str):
        """Import a function given its dotted path (module.attr)."""
        module_path, attr = dotted.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, attr)

    def _load_hooks(self, names: list[str]) -> list[Any]:
        """Import hook callables from dotted paths."""
        return [self._import_from_path(name) for name in (names or [])]

    def resolve(self, env_key: str) -> dict[str, Any]:
        """Resolve profile and hook information for a given environment key."""
        env = self._cfg.get(env_key)
        if env is None:
            raise KeyError(f"Env key not found: {env_key}")

        profile_key: str = env["profiles"]
        hookset_key: str = env.get("hooksets", "")

        prof = self._cfg["profiles"][profile_key]
        provider = prof["provider"]
        model = prof["model"]

        before_paths: list[str] = []
        after_paths: list[str] = []
        if hookset_key:
            hookset = self._cfg.get("hooksets", {}).get(hookset_key, {})
            before_paths = hookset.get("before", []) or []
            after_paths = hookset.get("after", []) or []

        before_hooks = self._load_hooks(before_paths)
        after_hooks = self._load_hooks(after_paths)

        return {
            "provider": provider,
            "model": model,
            "before_hooks": before_hooks,
            "after_hooks": after_hooks,
        }
