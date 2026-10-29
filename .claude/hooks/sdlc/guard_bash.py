#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell): シェル経由での承認・ゲート記録・結果シート・ワークフロー本体の改変を検出して拒否する。

Windows では Claude が PowerShell ツールでコマンドを実行することがあるため、PowerShell の書式も検査する。
シェルの完全な解析はできないためヒューリスティックである。すり抜けた改変も、
人が承認した成果物はゲートのハッシュ不一致で検知され、承認は scripts/approve（人が端末で実行）でしか記録できない。
軽量版では、人間ゲートの無い工程（設計・実装など）の成果物はシェルからの変更も検査しない。
"""
from __future__ import annotations

import re

from _common import PROJECT_DIR, allow, deny, maintenance, run, sdlc_project

from sdlc_lib.config import (AGENT_NAMES, PROTECTED_PATHS, RESULTS_FILE, SKILL_NAMES, load_project, main_root,
                             phase_areas, project_problems)

SEP = r"(?:^|[;&|(\n{]|\$\()\s*"   # コマンドの区切り（ここから次のコマンドが始まる）
WRITE_PATTERNS = [
    # bash
    r"(?<![0-9&<>-])>{1,2}(?!&)",                    # リダイレクト（2>&1 等は除外）
    r"\btee\b", r"\bsed\b[^|;&]*\s-i", r"\bperl\b[^|;&]*\s-[a-z]*i", r"\bcp\b", r"\bmv\b", r"\brm\b",
    r"\btouch\b", r"\bln\b", r"\bchmod\b", r"\btruncate\b", r"\bdd\b", r"\brsync\b",
    SEP + r"(?:sudo\s+)?install\s",                  # install コマンド（install.py 等の名前は対象外）
    r"\bgit\s+(checkout|restore|reset|rm|mv|apply|stash|clean|revert|cherry-pick)\b",
    r"\bpatch\b", r"\bunzip\b", r"\btar\b[^|;&]*\s-?x",
    # PowerShell / cmd
    r"(?i)\b(set-content|add-content|out-file|new-item|remove-item|move-item|copy-item|rename-item|clear-content"
    r"|set-item|expand-archive)\b",
    r"(?i)" + SEP + r"(?:del|erase|copy|xcopy|robocopy|move|ren|rename|rd|rmdir|sc|ac|ni|ri|mi|cpi|rni)\s",
    r"(?i)\[(?:system\.)?io\.file\]::",
]
NULL_REDIRECTS = re.compile(r"(?i)\d?>{1,2}\s*(?:/dev/null|\$null|nul\b)|\d>&\d|&>\s*/dev/null|\|\s*out-null")
# approve の呼び出し。コマンドの位置にあるもの、または承認の引数（工程番号・オプション）付きのもの
# （cmd /c・Start-Process・script -c 等で間接的に呼ぶ場合も拾う。文字列中の単なる言及は対象外）
APPROVE_CALL = re.compile(
    SEP + r"(?:&\s*)?(?:(?:sudo|env|exec|nohup|python3?|py|bash|sh|cmd(?:\.exe)?\s+/c)\s+)*"
    r"['\"]?(?:\S*/)?approve(?:\.cmd|\.ps1|\.bat)?['\"]?(?:\s|$|[;&|)])"
    r"|(?:\S*/)?approve(?:\.cmd|\.ps1|\.bat)?['\"]?\s+(?:-|\d)", re.IGNORECASE)
# ワークフロー本体のインストーラ（~/.claude や .claude/ を書き換える）。他の install.py と区別するためオプションで判定
INSTALL_CALL = re.compile(r"(?:\S*/)?install\.py\b[^;&|\n]*--(user|project|uninstall)\b")
# ~/.claude 配下の本体と設定（どのプロジェクトからでも保護する）
HOME_FORMS = (r"(?:~|\$HOME|\$\{HOME\}|\$env:(?:USERPROFILE|HOME)|%USERPROFILE%|/root|/home/[^/\s]+"
              r"|[a-z]:/users/[^/\s]+|/[a-z]/users/[^/\s]+)")
USER_BODY = re.compile(HOME_FORMS + r"/\.claude/(sdlc\b|hooks/sdlc\b|settings"
                       r"|skills/(" + "|".join(map(re.escape, SKILL_NAMES)) + r")\b"
                       r"|agents/(" + "|".join(map(re.escape, AGENT_NAMES)) + r")\.md)", re.IGNORECASE)
RESULTS = re.compile(re.escape(RESULTS_FILE[:-3]) + r"\.(md|xlsx)\b|\bresults\.(md|xlsx)\b")


def writes(cmd: str) -> bool:
    c = NULL_REDIRECTS.sub(" ", cmd)
    return any(re.search(p, c) for p in WRITE_PATTERNS)


def mentions(cmd: str, prefix: str) -> bool:
    return bool(prefix) and re.search(r"(^|[\s'\"=/:(])(\./)?" + re.escape(prefix) + r"(/|\b|$)", cmd) is not None


def check(data: dict):
    cmd = str((data.get("tool_input") or {}).get("command") or "").replace("\\", "/")  # Windows の区切りを統一
    shell = data.get("tool_name") or "Bash"
    if not maintenance():
        if INSTALL_CALL.search(cmd):
            deny("ワークフロー本体のインストール・更新（install.py）は人が実行してください。")
        if writes(cmd) and USER_BODY.search(cmd):
            deny(f"~/.claude の設定ファイルと SDLC ワークフロー本体は {shell} から変更できません。")
    root = main_root(data.get("cwd") or str(PROJECT_DIR)) or PROJECT_DIR
    if not sdlc_project(root):
        allow()
    if APPROVE_CALL.search(cmd):
        deny("scripts/approve は人が端末で実行する承認スクリプトです。Claude は実行できません。"
             "承認が必要な旨を人に伝えて停止してください。")
    if not writes(cmd):
        allow()
    if re.search(r"state/gates", cmd):
        deny(f"state/gates/ は {shell} から変更できません（承認は人が scripts/approve で記録します）。")
    if RESULTS.search(cmd):
        deny(f"受入確認の結果シートは {shell} から変更できません（結果は人が記入します。"
             "TC の反映・再確認・Excel の取り込みは scripts/sdlc testitems を使ってください）。")
    if not maintenance():
        for p in PROTECTED_PATHS:
            if mentions(cmd, p):
                deny(f"{p} はワークフロー本体のため {shell} から変更できません。")
    proj = load_project(root)
    if project_problems(proj):
        areas = ["docs/01-specification", "input"]
    else:
        areas = [a for pid in proj["gates"] for a in phase_areas(proj)[pid]]
    for a in areas:
        if mentions(cmd, a):
            deny(f"人間ゲートのある工程の成果物（{a}/）を {shell} で変更しようとしています。ゲートの検査を通すため "
                 "Write / Edit ツールを使ってください（参照・git merge・テスト実行は可）。")
    allow()


if __name__ == "__main__":
    run(check)
