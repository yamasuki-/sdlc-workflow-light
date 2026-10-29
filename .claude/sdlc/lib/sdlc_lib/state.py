"""state/phase.json（現在工程・ステップ・割り込み対応）の読み書き。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import PHASE_IDS

STEPS = ["plan", "work", "review", "gate"]
STEP_LABELS = {"plan": "計画", "work": "作成", "review": "レビュー", "gate": "完了判定（ゲート）"}

DEFAULT_STATE = {
    "mode": "normal",            # normal / item（不具合・変更要求の対応中）
    "current_phase": PHASE_IDS[0],
    "step": "plan",
    "item": None,                # 対応中の票（DEF-xxx / CR-xxx）
    "resume_phase": None,        # 割り込み前に進めていた工程（対応後に戻る）
    "resume_step": None,
    "completed": False,          # 最終工程まで完了したか
    "updated_at": None,
}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def phase_json(root) -> Path:
    return Path(root) / "state" / "phase.json"


def load(root) -> dict:
    p = phase_json(root)
    st = dict(DEFAULT_STATE)
    if p.exists():
        st.update(json.loads(p.read_text(encoding="utf-8")))
    return st


def save(root, st: dict) -> None:
    st = dict(st)
    st["updated_at"] = now()
    p = phase_json(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
