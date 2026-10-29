"""YAML front matter 付き Markdown の読み書き。"""
from __future__ import annotations

from pathlib import Path

from .config import require_yaml


def read(path) -> tuple[dict, str]:
    text = Path(path).read_text(encoding="utf-8")
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            meta = require_yaml().safe_load(text[4:end]) or {}
            return meta, text[end + 5:]
    return {}, text


def dump(meta: dict, body: str) -> str:
    y = require_yaml().safe_dump(meta, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{y}---\n{body}"


def write(path, meta: dict, body: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(dump(meta, body), encoding="utf-8")
