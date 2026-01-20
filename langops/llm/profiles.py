# llm/profiles.py
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable

import tomllib as toml


class ProfileStore:
    def __init__(self, path: str | Path = "profiles.toml") -> None:
        self.path = Path(path)
        with self.path.open("rb") as f:
            self._cfg = toml.load(f)

    def _import_from_path(self, dotted: str) -> Callable:
        module_path, attr = dotted.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, attr)

    def _load_hooks(self, names: list[str]) -> list[Callable]:
        return [self._import_from_path(name) for name in (names or [])]

    def resolve(self, profile_key: str) -> dict[str, Any]:
        profile = self._cfg.get(profile_key)
        if profile is None:
            raise KeyError(f"Profile not found: {profile_key}")

        required_keys = ()

        missing = [k for k in required_keys if profile.get(k) in (None, "")]
        if missing:
            raise ValueError(
                f"Profile {profile_key} missing required fields: {', '.join(missing)}"
            )

        before_paths = profile.get("hookset_before", []) or []
        after_paths = profile.get("hookset_after", []) or []

        resolved: dict[str, Any] = dict(profile)
        resolved["hookset_before"] = self._load_hooks(before_paths)
        resolved["hookset_after"] = self._load_hooks(after_paths)

        return resolved

    @staticmethod
    def load_profile(
        profile_key: str, path: str | Path = "profiles.toml"
    ) -> dict[str, Any]:
        store = ProfileStore(path)
        return store.resolve(profile_key)
