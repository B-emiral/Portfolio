# ./tasks/split_sentences.py
from __future__ import annotations

import re
from typing import List


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p and not p.isspace()]
