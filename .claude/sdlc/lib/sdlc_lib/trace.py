"""トレーサビリティ（SRC → REQ → SPEC/NFR → TC → 自動テスト）の抽出・検査・影響範囲分析。

軽量版で必須にするのは「人の意思が入る振る舞い」の連鎖だけ（要求 → 仕様 → テスト項目）。
設計（DS）とコードへのトレースは任意（書けば影響範囲の分析に使われる）。

記法（言語非依存）:
  定義   … Markdown の見出し行  `### SPEC-001: タイトル`
  追跡元 … 定義ブロック内の行     `- 追跡元: REQ-001, REQ-002`
  種別   … TC の定義ブロック内    `- 種別: 手動 | 自動 | 両方`
  コード … 任意のコメント中の     `trace: TC-003, SPEC-001`
  除外   … 定義ブロック内の行     `- 対象外: 理由`（下流が無くても検査で指摘しない）
           任意の位置の行         `- 除外: SRC-005, SRC-006（理由）`（取り込み項目を要求の対象外にする）
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from pathlib import Path

from .config import under
from .gates import list_files

PREFIXES = ["SRC", "REQ", "NFR", "Q", "SPEC", "TC", "DS", "DEF", "CR"]
ID_PAT = r"(?:%s)-\d{3,}" % "|".join(PREFIXES)
ID_RE = re.compile(r"\b" + ID_PAT + r"\b")
DEF_RE = re.compile(r"^#{1,6}\s+(" + ID_PAT + r")(?=[\s:：]|$)")
REF_RE = re.compile(r"(?:追跡元|trace)\s*[:：]\s*(.*)", re.IGNORECASE)
EXEMPT_RE = re.compile(r"^\s*[-*]?\s*対象外\s*[:：]")
KIND_RE = re.compile(r"^\s*[-*]?\s*種別\s*[:：]\s*(\S+)")
EXCLUDE_RE = re.compile(r"^\s*[-*]?\s*除外\s*[:：]\s*(.*)")

# TC の種別
TC_KINDS = ("手動", "自動", "両方")
AUTO_KINDS = ("自動", "両方")
MANUAL_KINDS = ("手動", "両方")

# コードファイルの種別
KIND_LABEL = {"CODE": "実装コード", "TEST": "テストコード"}

# 根になる（追跡元を持たない）定義
ROOT_KINDS = ("SRC", "Q", "DEF", "CR")

# (親種別, 子として必要な種別, 検査を始める工程番号（0 始まり）, 説明)
RULES = [
    ("SRC", {"REQ"}, 0, "取り込み項目が要求に反映されていない"),
    ("REQ", {"SPEC", "NFR"}, 0, "要求が仕様・非機能要件に展開されていない"),
    ("SPEC", {"TC"}, 0, "仕様にテスト項目が無い"),
    ("NFR", {"TC"}, 0, "非機能要件にテスト項目が無い（確認しない場合は対象外の理由を書く）"),
]
# 自動テストで確認する TC にテストコードが必要になる工程（03 実装）
AUTO_TC_FROM = 2

TEXT_SUFFIX_DENY = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".xlsx", ".docx", ".pptx", ".zip",
                    ".jar", ".class", ".pyc", ".so", ".dll", ".exe", ".bin", ".ico"}


def kind_of(node: str) -> str:
    if node.startswith("file:"):
        return node.split(":", 2)[1]
    return node.split("-", 1)[0]


class Graph:
    def __init__(self):
        self.defs: dict[str, dict] = {}          # id → {file, line, title, exempt, kind}
        self.parents: dict[str, set] = defaultdict(set)
        self.children: dict[str, set] = defaultdict(set)
        self.dups: list[tuple[str, str]] = []
        self.excluded: dict[str, str] = {}       # id → 除外を宣言した場所
        self.dangling: list[tuple[str, str, int]] = []

    def link(self, parent: str, child: str):
        self.parents[child].add(parent)
        self.children[parent].add(child)


def _read(path: Path) -> str | None:
    if path.suffix.lower() in TEXT_SUFFIX_DENY:
        return None
    try:
        if path.stat().st_size > 2_000_000:
            return None
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def code_kind(rel: str, proj: dict | None) -> str | None:
    if proj is None:
        return None
    if under(rel, proj["test_dir"]):
        return "TEST"
    if under(rel, proj["src_dir"]):
        return "CODE"
    return None


def build(root, proj: dict | None) -> Graph:
    root = Path(root)
    g = Graph()
    refs = []  # (from_node, [ids], file, line)
    excludes = []  # (id, where)
    for rel in list_files(root):
        if rel.startswith("docs/") and rel.endswith(".md"):
            text = _read(root / rel)
            if text is None:
                continue
            cur = None
            for n, line in enumerate(text.splitlines(), 1):
                x = EXCLUDE_RE.match(line)
                if x:
                    excludes += [(i, f"{rel}:{n}") for i in ID_RE.findall(x.group(1))]
                    continue
                m = DEF_RE.match(line)
                if m:
                    cur = m.group(1)
                    if cur in g.defs:
                        g.dups.append((cur, f"{rel}:{n}"))
                        cur = None
                    else:
                        g.defs[cur] = {"file": rel, "line": n, "title": line.lstrip("#").strip(), "exempt": False,
                                       "kind": None}
                    continue
                if line.startswith("#"):
                    cur = None
                    continue
                if cur is None:
                    continue
                if EXEMPT_RE.match(line):
                    g.defs[cur]["exempt"] = True
                k = KIND_RE.match(line)
                if k and g.defs[cur]["kind"] is None:
                    g.defs[cur]["kind"] = k.group(1).strip()
                r = REF_RE.search(line)
                if r and re.match(r"^\s*[-*]?\s*(追跡元|trace)", line, re.IGNORECASE):
                    refs.append((cur, ID_RE.findall(r.group(1)), rel, n))
        else:
            ck = code_kind(rel, proj)
            if ck is None:
                continue
            text = _read(root / rel)
            if text is None:
                continue
            node = f"file:{ck}:{rel}"
            for n, line in enumerate(text.splitlines(), 1):
                r = REF_RE.search(line)
                if r:
                    refs.append((node, ID_RE.findall(r.group(1)), rel, n))
    for i, where in excludes:
        if i in g.defs:
            g.defs[i]["exempt"] = True
            g.excluded[i] = where
        else:
            g.dangling.append((i, *where.rsplit(":", 1)))
    for child, ids, rel, n in refs:
        for pid in ids:
            if pid not in g.defs:
                g.dangling.append((pid, rel, n))
            else:
                g.link(pid, child)
    return g


def tc_kind(g: Graph, tc: str) -> str | None:
    return (g.defs.get(tc) or {}).get("kind")


def automated(g: Graph, tc: str) -> list[str]:
    """TC を参照しているテストコードのファイル。"""
    return sorted(c.split(":", 2)[2] for c in g.children.get(tc, ()) if kind_of(c) == "TEST")


def check(g: Graph, upto: int) -> list[str]:
    issues = []
    for i, where in g.dups:
        issues.append(f"[重複定義] {i}（{where}、既存: {g.defs[i]['file']}:{g.defs[i]['line']}）")
    for i, rel, n in g.dangling:
        issues.append(f"[未定義の参照] {i}（{rel}:{n}）")
    for parent_kind, need, from_phase, msg in RULES:
        if upto < from_phase:
            continue
        for i, d in sorted(g.defs.items()):
            if kind_of(i) != parent_kind or d["exempt"]:
                continue
            if not any(kind_of(c) in need for c in g.children.get(i, ())):
                issues.append(f"[下流なし] {i}: {msg}（{d['file']}:{d['line']}）")
    for i, d in sorted(g.defs.items()):
        if kind_of(i) != "TC":
            continue
        if d["kind"] not in TC_KINDS:
            issues.append(f"[種別なし] {i}: `- 種別: 手動 | 自動 | 両方` を書く（{d['file']}:{d['line']}）")
        elif upto >= AUTO_TC_FROM and d["kind"] in AUTO_KINDS and not d["exempt"] and not automated(g, i):
            issues.append(f"[自動テストなし] {i}: 種別 {d['kind']} の TC にテストコード（`trace: {i}`）が無い"
                          f"（{d['file']}:{d['line']}）")
    # 上流参照の欠落（根以外の定義は追跡元を持つべき）
    for i, d in sorted(g.defs.items()):
        if kind_of(i) in ROOT_KINDS or d["exempt"]:
            continue
        if not g.parents.get(i):
            issues.append(f"[追跡元なし] {i}（{d['file']}:{d['line']}）")
    return issues


def _bfs(start: list[str], edges: dict) -> list[str]:
    seen, out = set(start), []
    q = deque(start)
    while q:
        n = q.popleft()
        for m in sorted(edges.get(n, ())):
            if m not in seen:
                seen.add(m)
                out.append(m)
                q.append(m)
    return out


def downstream(g: Graph, ids: list[str]) -> list[str]:
    return _bfs(ids, g.children)


def upstream(g: Graph, ids: list[str]) -> list[str]:
    return _bfs(ids, g.parents)


def node_file(g: Graph, node: str) -> str | None:
    if node.startswith("file:"):
        return node.split(":", 2)[2]
    d = g.defs.get(node)
    return d["file"] if d else None


def impact(g: Graph, ids: list[str]) -> dict:
    nodes = list(ids) + downstream(g, ids)
    out_ids = [n for n in nodes if not n.startswith("file:")]
    files = sorted({f for f in (node_file(g, n) for n in nodes) if f})
    return {"ids": out_ids, "files": files, "tcs": [n for n in out_ids if kind_of(n) == "TC"]}


def matrix(g: Graph, results: dict | None = None) -> str:
    """REQ ごとの SPEC/NFR → TC → 自動テスト・手動確認結果の表。"""
    results = results or {}
    lines = ["| REQ | SPEC / NFR | TC | 自動テスト | 手動確認 |", "|---|---|---|---|---|"]
    for r in sorted(i for i in g.defs if kind_of(i) == "REQ"):
        desc = downstream(g, [r])
        specs = sorted(n for n in desc if kind_of(n) in ("SPEC", "NFR"))
        tcs = sorted(n for n in desc if kind_of(n) == "TC")
        auto = sorted({f for t in tcs for f in automated(g, t)})
        man = [f"{t}: {results.get(t, {}).get('result', '未実施')}" for t in tcs if tc_kind(g, t) in MANUAL_KINDS]
        cells = ["<br>".join(x) or "—" for x in (specs, tcs, auto, man)]
        lines.append(f"| {r} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
