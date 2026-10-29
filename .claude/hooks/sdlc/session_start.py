#!/usr/bin/env python3
"""SessionStart: SDLC プロジェクトなら現在の状態をコンテキストに入れる（中断からの再開用）。失敗しても起動は妨げない。"""
from __future__ import annotations

import os
import subprocess
import sys

try:
    from _common import BASE, PROJECT_DIR, deferred, sdlc_project

    if not deferred() and sdlc_project(PROJECT_DIR):
        project_bin = PROJECT_DIR / ".claude" / "sdlc" / "bin" / "sdlc"
        sdlc = project_bin if project_bin.exists() else BASE / "sdlc" / "bin" / "sdlc"
        r = subprocess.run([sys.executable, str(sdlc), "status"], cwd=str(PROJECT_DIR),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                           env=dict(os.environ, PYTHONUTF8="1"))
        out = (r.stdout or r.stderr).strip()
        if out:
            print("## SDLC ワークフローの現在状態（scripts/sdlc status）\n" + out
                  + "\n\n続きから進めるには /sdlc を実行してください。")
except Exception:  # noqa: BLE001
    pass
sys.exit(0)
