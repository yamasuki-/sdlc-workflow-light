"""Markdown: 出典 = 見出し階層＋行番号。段落・箇条書き項目・表行を 1 断片とする。"""
from __future__ import annotations

import re
from pathlib import Path

from .base import HIGH, Fragment

HEAD = re.compile(r"^(#{1,6})\s+(.*)")
ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}")


def convert(path: Path, assets_dir: Path, rel_assets: str) -> list[Fragment]:
    lines = path.read_text(encoding="utf-8").splitlines()
    heads: list[str] = []
    out: list[Fragment] = []
    buf: list[tuple[int, str]] = []
    kind = "段落"
    header: list[str] | None = None
    in_code = False

    def where(a, b):
        h = " > ".join(heads) or "（見出しなし）"
        return f"{h} / L{a}" + (f"-{b}" if b != a else "")

    def flush():
        nonlocal buf
        if buf:
            text = "\n".join(s for _, s in buf).strip()
            if text:
                out.append(Fragment(where(buf[0][0], buf[-1][0]), kind, text, HIGH))
        buf = []

    for n, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            if not in_code:
                flush()
                kind = "コード"
            in_code = not in_code
            buf.append((n, line))
            if not in_code:
                flush()
            continue
        if in_code:
            buf.append((n, line))
            continue
        m = HEAD.match(line)
        if m:
            flush()
            level = len(m.group(1))
            heads[:] = heads[: level - 1] + [m.group(2).strip()]
            header = None
            continue
        if line.strip().startswith("|"):
            flush()
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if TABLE_SEP.match(line):
                continue
            if header is None:
                header = cells
                continue
            text = "\n".join(f"{h}: {v}" for h, v in zip(header, cells) if v)
            out.append(Fragment(where(n, n), "表行", text, HIGH))
            continue
        header = None
        if not line.strip():
            flush()
            continue
        if ITEM.match(line):
            flush()
            kind = "箇条書き"
        elif not buf:
            kind = "段落"
        buf.append((n, line))
    flush()
    return out
