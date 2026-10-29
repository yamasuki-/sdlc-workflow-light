#!/usr/bin/env python3
"""PreToolUse(Skill): 工程スキルの起動時に、それより前の人間ゲートがすべて有効（承認＋ハッシュ一致）か確認する。"""
from __future__ import annotations

from _common import PROJECT_DIR, allow, deny, run

from sdlc_lib import gates
from sdlc_lib.config import SKILL_TO_PHASE, find_root, load_project, project_problems


def check(data: dict):
    ti = data.get("tool_input") or {}
    words = str(ti.get("skill") or ti.get("command") or ti.get("name") or "").lstrip("/").split()
    name = words[0].split(":")[-1] if words else ""
    if name not in SKILL_TO_PHASE:
        allow()
    root = find_root(data.get("cwd") or str(PROJECT_DIR))
    proj = load_project(root)
    probs = project_problems(proj)
    if probs:
        deny("project.yaml が未作成・不完全です。先に /sdlc-init を実行してください: " + "; ".join(probs))
    bad = gates.prerequisites(root, proj, SKILL_TO_PHASE[name])
    if bad:
        deny(f"/{name} を開始できません。前の人間ゲートが有効ではありません:\n"
             + "\n".join(f"  ✘ {s['phase']}: {s['reason']}" for s in bad)
             + "\n人が `scripts/approve <工程>` で承認するまで先の工程には進めません。")
    allow()


if __name__ == "__main__":
    run(check)
