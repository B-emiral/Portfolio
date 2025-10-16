# ./tasks/doc_sentence_splitter.py
from __future__ import annotations

import asyncio
import re


def _split_regex(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p and not p.isspace()]


async def split_sentences_regex(text: str) -> list[str]:
    """Asynchronously split text into sentences using regex in a background thread."""

    # Run regex split in a background thread to avoid blocking the event loop
    return await asyncio.to_thread(_split_regex, text)
