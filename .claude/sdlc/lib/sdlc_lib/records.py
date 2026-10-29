"""全工程共通の決定事項ログ（state/decisions.md）と未解決事項ログ（state/open-questions.md）。

並行実行中のサブエージェントは書き込まず、結果報告の「決定事項」「未解決事項」で返す。
追記はオーケストレータ（メインセッション）が `scripts/sdlc decision|question` で一元的に行う。
"""
from __future__ import annotations

import re
from pathlib import Path

from .state import now

PRIORITIES = ["高", "中", "低"]
DEC_HEAD = re.compile(r"^### (DEC-\d+)", re.MULTILINE)
OQ_HEAD = re.compile(r"^### (OQ-\d+) \[(open|answered|closed)\] 優先度:(\S+)(?: 工程:(\S+))?", re.MULTILINE)


def decisions_path(root) -> Path:
    return Path(root) / "state" / "decisions.md"


def questions_path(root) -> Path:
    return Path(root) / "state" / "open-questions.md"


def _read(p: Path, title: str) -> str:
    if p.exists():
        return p.read_text(encoding="utf-8")
    return f"# {title}\n"


def _next(text: str, pat: re.Pattern, prefix: str) -> str:
    nums = [int(m.group(1).split("-")[1]) for m in pat.finditer(text)]
    return f"{prefix}-{(max(nums) + 1 if nums else 1):03d}"


def add_decision(root, text: str, phase: str | None = None, source: str | None = None) -> str:
    p = decisions_path(root)
    body = _read(p, "決定事項ログ")
    did = _next(body, DEC_HEAD, "DEC")
    meta = " / ".join(x for x in (now(), phase or "", f"出典: {source}" if source else "") if x)
    body = body.rstrip("\n") + f"\n\n### {did}\n\n- {meta}\n\n{text.strip()}\n"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return did


def add_question(root, text: str, priority: str = "中", phase: str | None = None, source: str | None = None) -> str:
    if priority not in PRIORITIES:
        raise ValueError(f"優先度は {PRIORITIES} のいずれか")
    p = questions_path(root)
    body = _read(p, "未解決事項ログ")
    qid = _next(body, OQ_HEAD, "OQ")
    head = f"### {qid} [open] 優先度:{priority}" + (f" 工程:{phase}" if phase else "")
    src = f"\n- 出典: {source}" if source else ""
    body = body.rstrip("\n") + f"\n\n{head}\n\n- 起票: {now()}{src}\n- 質問: {text.strip()}\n- 回答: \n"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return qid


def answer_question(root, qid: str, answer: str, close: bool = True) -> None:
    p = questions_path(root)
    body = _read(p, "未解決事項ログ")
    m = re.search(rf"^### {re.escape(qid)} \[(open|answered|closed)\](.*)$", body, re.MULTILINE)
    if not m:
        raise KeyError(f"未解決事項がありません: {qid}")
    status = "closed" if close else "answered"
    start = m.start()
    nxt = re.search(r"^### ", body[m.end():], re.MULTILINE)
    end = m.end() + nxt.start() if nxt else len(body)
    block = body[start:end]
    block = block.replace(f"[{m.group(1)}]", f"[{status}]", 1)
    block = re.sub(r"^- 回答: .*$", f"- 回答: {answer.strip()}（{now()}）", block, count=1, flags=re.MULTILINE)
    p.write_text(body[:start] + block + body[end:], encoding="utf-8")


def questions(root, only_open: bool = False) -> list[dict]:
    body = _read(questions_path(root), "")
    out = []
    for m in OQ_HEAD.finditer(body):
        q = {"id": m.group(1), "status": m.group(2), "priority": m.group(3), "phase": m.group(4)}
        nxt = re.search(r"^### ", body[m.end():], re.MULTILINE)
        block = body[m.end(): m.end() + nxt.start() if nxt else len(body)]
        qm = re.search(r"^- 質問: (.*)$", block, re.MULTILINE)
        q["text"] = qm.group(1) if qm else ""
        if not only_open or q["status"] == "open":
            out.append(q)
    return out
