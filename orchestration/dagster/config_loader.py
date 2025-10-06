# ./orchestration/dagster/config_loader.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_settings() -> dict[str, Any]:
    """Load Dagster runtime settings from config file in the same directory."""
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing Dagster config file: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)
