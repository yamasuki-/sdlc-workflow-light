#!/usr/bin/env python3
"""PreToolUse(Write|Edit|MultiEdit|NotebookEdit): 書き込み先に応じて人間ゲートと結果シートを守る。

どのプロジェクトでも:
  ~/.claude/settings*.json       … 拒否（env で SDLC_MAINTENANCE を設定されると保護が外れるため）
  ~/.claude に置いた本体          … 拒否（~/.claude/sdlc・hooks/sdlc・SDLC のスキル/エージェント）
SDLC プロジェクトでのみ:
  .claude/settings*.json         … 拒否（同上）
  state/gates/**                 … 常に拒否（承認は人が scripts/approve で記録する）
  プロジェクトに置いた本体・ランチャ … 拒否（SDLC_MAINTENANCE=1 で起動時のみ許可）
  受入確認の結果シート            … 常に拒否（結果は人が記入する。CLI の sheet / reset / import は可）
  工程 k の成果物領域            … 工程 k より前の人間ゲートがすべて有効、かつ工程 k が承認済みでないときのみ許可
                                   （人間ゲートの無い工程は問わない。軽量版では設計・実装は自由に直せる）
"""
from __future__ import annotations

import os
from pathlib import Path

from _common import allow, deny, maintenance, run, sdlc_project

from sdlc_lib import gates
from sdlc_lib.config import (GATES_DIR, RESULTS_FILE, is_protected, is_user_body_path, is_user_settings, load_project,
                             main_root, phase_of_path, project_problems, under, worktree_root)

MAINT_HINT = "変更が必要なら人が編集するか、SDLC_MAINTENANCE=1 で Claude Code を起動してください。"
RESULTS_FILES = (RESULTS_FILE, RESULTS_FILE[:-3] + ".xlsx")


def target_path(data: dict) -> Path | None:
    ti = data.get("tool_input") or {}
    p = ti.get("file_path") or ti.get("notebook_path") or ti.get("path")
    if not p:
        return None
    p = Path(os.path.expanduser(str(p)))
    if not p.is_absolute():
        p = Path(data.get("cwd") or os.getcwd()) / p
    # シンボリックリンク（macOS の /var → /private/var 等）や Windows の短い名前（RUNNER~1 等）を実体のパスにそろえる。
    # そろえないと git のルートと比べられず、判定の対象外として素通りしてしまう
    return Path(os.path.realpath(p))


def check(data: dict):
    path = target_path(data)
    if path is None:
        allow()
    if not maintenance():
        if is_user_settings(path):
            deny(f"{path} は Claude Code の設定ファイル（hooks・env）のため編集できません。{MAINT_HINT}")
        if is_user_body_path(path):
            deny(f"{path} は ~/.claude に置いた SDLC ワークフロー本体のため編集できません。{MAINT_HINT}")
    wroot = worktree_root(path)
    if wroot is None:
        allow()
    try:
        rel = path.relative_to(wroot).as_posix()
    except ValueError:
        allow()
    mroot = main_root(wroot) or wroot
    if not sdlc_project(mroot):
        allow()

    if under(rel, GATES_DIR):
        deny("state/gates/ への書き込みは禁止です。承認は人が端末で `scripts/approve <工程>` を実行して記録します。")
    if is_protected(rel) and not maintenance():
        deny(f"{rel} はワークフロー本体（ゲートの強制機構）のため編集できません。{MAINT_HINT}")
    if rel in RESULTS_FILES:
        deny(f"{rel} は受入確認の結果シートです。結果は人が記入します（Claude は記入しない）。"
             "TC の反映は `scripts/sdlc testitems sheet`、再確認は `scripts/sdlc testitems reset` を使ってください。")

    proj = load_project(mroot) or load_project(wroot)
    if project_problems(proj):
        if rel.startswith(("docs/", "input/")):
            deny("project.yaml が未作成・不完全です。先に /sdlc-init を実行してください。")
        allow()

    phase = phase_of_path(rel, proj)
    if phase is None:
        allow()

    files = gates.list_files(mroot)
    bad = gates.prerequisites(mroot, proj, phase, files)
    if bad:
        lines = "\n".join(f"  ✘ {s['phase']}: {s['reason']}" for s in bad)
        deny(f"{rel} は工程 {phase} の成果物です。前の人間ゲートが有効でないため書き込めません:\n{lines}\n"
             "人による承認（scripts/approve）を待つか、承認後の変更なら /change（仕様の変更）で扱ってください。")
    own = gates.gate_status(mroot, proj, phase, files)
    if own["valid"]:
        deny(f"{rel} は人が承認済みの工程 {phase} の成果物です。仕様を変えるなら /change、"
             "作り間違いなら /defect でやり直しを開始してから変更してください。")
    allow()


if __name__ == "__main__":
    run(check)
