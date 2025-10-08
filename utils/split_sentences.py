# ./tasks/split_sentences.py
from __future__ import annotations

import asyncio
import re
from typing import List


async def split_sentences_regex(text: str) -> List[str]:
    """Asynchronously split text into sentences using regex in a background thread."""

    def _split():
        parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
        return [p.strip() for p in parts if p and not p.isspace()]

    # Run regex split in a background thread to avoid blocking the event loop
    return await asyncio.to_thread(_split)
