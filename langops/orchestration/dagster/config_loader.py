# ./langops/orchestration/dagster/config_loader.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(__file__).parent / "config.json"


def load_settings() -> dict[str, Any]:
    """Load Dagster runtime settings from config file in the same directory."""
    if not CONFIG_DIR.exists():
        raise FileNotFoundError(f"Missing Dagster config file: {CONFIG_DIR}")
    with open(CONFIG_DIR, encoding="utf-8") as f:
        return json.load(f)
