# llm/hooks/utils.py
from __future__ import annotations

from typing import Any


def extract_prompt(payload: dict[str, Any]) -> str:
    if payload.get("prompt"):
        return str(payload["prompt"])
    msgs: list[dict[str, Any]] = payload.get("messages") or []
    out_lines: list[str] = []
    for m in msgs:
        role = m.get("role")
        content = m.get("content")
        if isinstance(content, list):
            text_parts = [b.get("text", "") for b in content if isinstance(b, dict)]
            content = "\n".join([p for p in text_parts if p])
        out_lines.append(f"{role}: {content}")
    return "\n".join(out_lines)


def extract_text(resp: dict[str, Any]) -> str | None:
    content = resp.get("content") if isinstance(resp, dict) else None
    if isinstance(content, list) and content:
        txt = content[0].get("text")
        return txt if isinstance(txt, str) else None
    if isinstance(content, str):
        return content
    return None
