"""hooks 共通処理。終了コード 2 + stderr でツール呼び出しを拒否する（Claude に理由が返る）。

この hooks は ~/.claude/hooks/sdlc/（全プロジェクト共通）にも、プロジェクトの .claude/hooks/sdlc/ にも置ける。
  - プロジェクトに .claude/hooks/sdlc/ があれば、~/.claude 側の hook は何もしない（プロジェクト版が上書き）
  - ~/.claude 側の hook は、SDLC プロジェクト（project.yaml に workflow: sdlc）でだけ工程の検査をする
  - 本体ライブラリはプロジェクトの .claude/sdlc/lib を優先し、無ければ hook と同じ場所の .claude/sdlc/lib を使う
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # <base>/.claude/hooks/sdlc
BASE = HERE.parents[1]                           # <base>/.claude
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
LOCAL_INSTALL = (PROJECT_DIR / ".claude").resolve() == BASE.resolve()


def _lib_dir() -> Path:
    project_lib = PROJECT_DIR / ".claude" / "sdlc" / "lib"
    return project_lib if (project_lib / "sdlc_lib").is_dir() else BASE / "sdlc" / "lib"


sys.path.insert(0, str(_lib_dir()))

# Windows でも Claude Code とのやり取り（JSON・メッセージ）を UTF-8 で行う
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def read_input() -> dict:
    try:
        return json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except ValueError:
        return {}


def deny(msg: str):
    print(f"[SDLC ガード] {msg}", file=sys.stderr)
    sys.exit(2)


def allow():
    sys.exit(0)


def maintenance() -> bool:
    """人が SDLC_MAINTENANCE=1 で Claude Code を起動した場合のみワークフロー本体の編集を許可する。"""
    return os.environ.get("SDLC_MAINTENANCE") == "1"


def deferred() -> bool:
    """~/.claude 側の hook で、プロジェクトに自前の hooks がある（そちらに任せる）。"""
    name = Path(sys.argv[0]).name
    return not LOCAL_INSTALL and (PROJECT_DIR / ".claude" / "hooks" / "sdlc" / name).exists()


def sdlc_project(root) -> bool:
    """この hook が工程の検査をすべきプロジェクトか。"""
    from sdlc_lib.config import is_sdlc_project
    return (LOCAL_INSTALL and Path(root).resolve() == PROJECT_DIR) or is_sdlc_project(root)


def _probably_sdlc() -> bool:
    try:
        return sdlc_project(PROJECT_DIR)
    except Exception:  # noqa: BLE001
        return True


def run(fn):
    """ガード本体を実行する。SDLC プロジェクトでの内部エラーは安全側（拒否）に倒す。"""
    if deferred():
        allow()
    try:
        fn(read_input())
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        if maintenance() or not _probably_sdlc():
            allow()
        deny(f"ガードの内部エラーのため拒否しました: {type(e).__name__}: {e}\n"
             "依存関係（pip install -r requirements.txt）と project.yaml を確認してください。")
