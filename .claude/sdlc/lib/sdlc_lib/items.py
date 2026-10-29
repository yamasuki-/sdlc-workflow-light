"""割り込み票: 不具合票（state/defects/DEF-xxx.md）と変更要求票（state/changes/CR-xxx.md）。

軽量版の考え方:
- 不具合（/defect）… 仕様どおりに作れていない。設計（02）か実装（03）からやり直す。人の承認は要らない
  （ただし project.yaml でゲートを追加した工程をやり直す場合は、その工程の再承認が要る）。
  仕様そのものが誤っていた場合は /change で扱う。
- 変更要求（/change）… 振る舞い（要件・仕様）を変える。01 からやり直し、01 の再承認（唯一の人間ゲート）で合意する。
どちらも、やり直しが終わったら再確認する TC（retest）を結果シートで未実施に戻し、人が確認する。
"""
from __future__ import annotations

import re
from pathlib import Path

from . import fm
from .config import PHASE_IDS, phase_id, phase_index
from .state import now

STATUSES = ["起票", "対応中", "クローズ"]
SEVERITIES = ["致命", "高", "中", "低"]
PREFIX = {"defect": "DEF", "change": "CR"}
LABEL = {"defect": "不具合", "change": "変更要求"}
DIRS = {"defect": "defects", "change": "changes"}
# やり直しを始められる工程（不具合は仕様を変えない。仕様の誤りは変更要求）
START_PHASES = {"defect": PHASE_IDS[1:3], "change": PHASE_IDS[:3]}

DEFECT_BODY = """
## 現象

（何が起きたか。期待値と実際の値。NG になった TC があれば ID とメモ）

## 再現手順

1.

## 原因

（該当箇所（ファイル:行）・関連 ID。エビデンス（実行したコマンド・ログ）を生のテキストで残す。推測は書かない）

## 修正内容

-

## 再確認

（retest に書いた TC と、追加・修正した自動テスト）

## 経緯

- {now} 起票
"""

CHANGE_BODY = """
## 変更内容

（何をどう変えたいか・追加したいか。依頼者の言葉で）

## 現行の振る舞い

（関連する SPEC / TC と、コードの実際の動き）

## 変更後の振る舞い（SPEC / TC の差分）

| 区分 | ID | 変更前 | 変更後 |
|---|---|---|---|
| 変更 | SPEC-xxx | | |
| 追加 | TC-xxx | — | |

## 影響範囲

（`scripts/sdlc trace impact <ID...>` の結果。設計・コード・テストへの影響）

## 経緯

- {now} 起票
"""


def kind_of(item_id: str) -> str:
    return "change" if str(item_id).startswith("CR-") else "defect"


def label(item_id: str) -> str:
    return LABEL[kind_of(item_id)]


def item_dir(root, kind: str) -> Path:
    return Path(root) / "state" / DIRS[kind]


def path(root, item_id: str) -> Path:
    return item_dir(root, kind_of(item_id)) / f"{item_id}.md"


def all_ids(root, kind: str | None = None) -> list[str]:
    out = []
    for k, pre in PREFIX.items():
        if kind and k != kind:
            continue
        d = item_dir(root, k)
        if d.exists():
            out += [p.stem for p in d.glob(f"{pre}-*.md")]
    return sorted(out)


def next_id(root, kind: str) -> str:
    pre = PREFIX[kind]
    nums = [int(m.group(1)) for i in all_ids(root, kind) if (m := re.match(rf"{pre}-(\d+)$", i))]
    return f"{pre}-{(max(nums) + 1 if nums else 1):03d}"


def create(root, kind: str, title: str, detected_in: str, severity: str = "中", retest: list[str] | None = None) -> str:
    if severity not in SEVERITIES:
        raise ValueError(f"severity は {SEVERITIES} のいずれか")
    iid = next_id(root, kind)
    meta = {"id": iid, "kind": kind, "title": title, "status": "起票", "severity": severity,
            "detected_in": phase_id(detected_in), "start_phase": "", "related_ids": [], "retest": retest or [],
            "created_at": now()}
    body = (DEFECT_BODY if kind == "defect" else CHANGE_BODY).format(now=now())
    fm.write(path(root, iid), meta, body)
    return iid


def load(root, item_id: str) -> tuple[dict, str]:
    p = path(root, item_id)
    if not p.exists():
        raise FileNotFoundError(f"{label(item_id)}票がありません: {p}")
    return fm.read(p)


def save(root, item_id: str, meta: dict, body: str) -> None:
    fm.write(path(root, item_id), meta, body)


def log(body: str, msg: str) -> str:
    return body.rstrip("\n") + f"\n- {now()} {msg}\n"


def check_start_phase(kind: str, phase: str) -> str:
    pid = phase_id(phase)
    if pid not in START_PHASES[kind]:
        hint = ("仕様（01）の誤りは /change（変更要求）で扱います。" if kind == "defect" else "")
        raise ValueError(f"{LABEL[kind]}のやり直しは {', '.join(START_PHASES[kind])} から始めます（指定: {pid}）。{hint}")
    return pid


def rework_phases(start: str, resume: str) -> list[str]:
    """やり直す工程（開始工程〜割り込み前の工程）。"""
    a, b = phase_index(start), phase_index(resume)
    return PHASE_IDS[a:max(a, b) + 1]
