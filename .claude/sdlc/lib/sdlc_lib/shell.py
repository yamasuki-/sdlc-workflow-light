"""project.yaml のコマンド（テスト・機械チェック）を OS によらず bash で実行する。

Windows では shell=True が cmd.exe になり、bash の書式で書いたコマンドが動かないため、Git Bash を明示的に使う。
WSL の bash（C:\\Windows\\System32\\bash.exe）は Windows のパスを扱えないので使わない。
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

WINDOWS = os.name == "nt"


def find_bash() -> str | None:
    """使う bash の実行ファイル。見つからなければ None。"""
    for env in ("SDLC_BASH", "CLAUDE_CODE_GIT_BASH_PATH"):
        p = os.environ.get(env)
        if p and Path(p).is_file():
            return p
    found = shutil.which("bash")
    if found and not (WINDOWS and ("\\system32\\" in found.lower() or "windowsapps" in found.lower())):
        return found
    if WINDOWS:
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432"),
                     os.environ.get("LOCALAPPDATA") and str(Path(os.environ["LOCALAPPDATA"]) / "Programs")):
            if not base:
                continue
            for rel in (r"Git\bin\bash.exe", r"Git\usr\bin\bash.exe"):
                p = Path(base) / rel
                if p.is_file():
                    return str(p)
    return None


def run_shell(cmd: str, cwd, timeout: int | None = None) -> subprocess.CompletedProcess:
    """cmd を bash で実行する（UTF-8 で出力を受け取る）。TimeoutExpired はそのまま送出する。"""
    kw = dict(cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
              env=dict(os.environ, PYTHONUTF8="1"))
    if not WINDOWS:
        return subprocess.run(cmd, shell=True, **kw)
    bash = find_bash()
    if bash is None:
        return subprocess.CompletedProcess(cmd, 127, "", "bash が見つかりません（Git for Windows をインストールするか SDLC_BASH を設定）")
    return subprocess.run([bash, "-c", cmd], **kw)
