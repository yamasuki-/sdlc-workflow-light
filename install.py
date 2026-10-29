#!/usr/bin/env python3
"""SDLC ワークフロー（軽量版）本体のインストーラ（人が実行する）。

  python3 install.py --user               # ~/.claude/ に置く（全プロジェクト共通。既定）
  python3 install.py --project <dir>      # <dir>/.claude/ に置く（そのプロジェクト単体で使う／~/.claude 版を上書き）
  python3 install.py --user --uninstall   # 取り除く（--project も同様）
  Windows では PowerShell / コマンドプロンプトで py -3 install.py ...（または python install.py ...）
  オプション: --dry-run（何をするか表示するだけ）

置くもの（.claude/ からの相対パス）:
  sdlc/        本体（bin・lib・テンプレート・チェックリスト・共通フロー・全体ルール RULES.md）
  hooks/sdlc/  人間ゲート・結果シート・Bash・スキル起動のガード
  skills/<SDLC のスキル>/, agents/<SDLC のエージェント>.md
  settings.json に hooks と permissions を追記（他の設定は残す。再実行しても重複しない）
プロジェクトでは、続けて `/sdlc-init`（または `scripts/sdlc init`）でランチャと CLAUDE.md の import を準備する。

更新は 1 ファイルずつ行い、置いたファイルとそのハッシュを sdlc/.install-manifest.json に記録する。
インストール後に変更されたファイル・インストーラが置いていないファイル（プロジェクトでの上書きなど）は
変更・削除せずに報告する（--force で置き換える）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / ".claude"
sys.path.insert(0, str(SRC / "sdlc" / "lib"))

from sdlc_lib.config import BODY_DIRS, BODY_FILES, utf8_stdio  # noqa: E402

utf8_stdio()

HOOKS = [  # (イベント, matcher, スクリプト, タイムアウト秒, 失敗時に拒否するか)
    ("PreToolUse", "Write|Edit|MultiEdit|NotebookEdit", "guard_write.py", 600, True),
    ("PreToolUse", "Bash|PowerShell", "guard_bash.py", 60, True),
    ("PreToolUse", "Skill", "guard_skill.py", 60, True),
    ("SessionStart", None, "session_start.py", 60, False),
]
# プロジェクト配置では Windows の PowerShell ツールを止め、Bash ツール（Git Bash）に寄せる
PROJECT_ENV = {"CLAUDE_CODE_USE_POWERSHELL_TOOL": "0"}
DENY = ["Bash(scripts/approve:*)", "Bash(./scripts/approve:*)", "Bash(python3 scripts/approve:*)"]
MARK = "/hooks/sdlc/"
MANIFEST = "sdlc/.install-manifest.json"


def hook_command(scope: str, script: str) -> str:
    """bash（Windows では Git Bash）で入口 run を呼ぶ。run が Python を探して hook を実行する。"""
    if scope == "user":
        base = (Path.home() / ".claude").as_posix()   # Windows では C:/Users/<名前>/.claude
    else:
        base = "${CLAUDE_PROJECT_DIR}/.claude"
    return f'bash "{base}/hooks/sdlc/run" {script}'


def is_sdlc_hook(entry: dict) -> bool:
    return any(MARK in str(h.get("command", "")) for h in entry.get("hooks", []))


def merged_settings(settings: dict, scope: str, remove: bool = False) -> dict:
    s = json.loads(json.dumps(settings))
    hooks = s.setdefault("hooks", {})
    if scope == "project":
        env = s.setdefault("env", {})
        for k, v in PROJECT_ENV.items():
            if remove:
                if env.get(k) == v:
                    del env[k]
            else:
                env.setdefault(k, v)
        if not env:
            del s["env"]
    for event in dict.fromkeys(e for e, *_ in HOOKS):
        hooks[event] = [e for e in hooks.get(event, []) if not is_sdlc_hook(e)]
    if not remove:
        for event, matcher, script, timeout, block in HOOKS:
            h = {"type": "command", "command": hook_command(scope, script), "shell": "bash", "timeout": timeout}
            if block:
                h["onFailure"] = "block"   # hook 自体が動かない（bash・Python が無い等）ときも素通りさせない
            entry = {"hooks": [h]}
            if matcher:
                entry = {"matcher": matcher, **entry}
            hooks[event].append(entry)
    for event in list(hooks):
        if not hooks[event]:
            del hooks[event]
    if not hooks:
        del s["hooks"]
    perms = s.setdefault("permissions", {})
    deny = [d for d in perms.get("deny", []) if d not in DENY]
    if not remove:
        deny += DENY
    if deny:
        perms["deny"] = deny
    else:
        perms.pop("deny", None)
    if not perms:
        del s["permissions"]
    return s


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source_files() -> dict[str, Path]:
    """.claude/ からの相対パス → ソースのファイル。"""
    out = {}
    for d in BODY_DIRS:
        for p in sorted((SRC / d).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                out[p.relative_to(SRC).as_posix()] = p
    for f in BODY_FILES:
        if (SRC / f).is_file():
            out[f] = SRC / f
    return out


def sync(target: Path, uninstall: bool, force: bool, dry: bool) -> dict:
    """ファイル単位で配置・更新・削除する。変更されたファイルは force でなければ残す。"""
    mp = target / MANIFEST
    manifest = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    src = {} if uninstall else source_files()
    new_manifest, report = {}, {"placed": [], "updated": [], "removed": [], "kept": []}
    for rel in sorted(set(src) | set(manifest)):
        dst = target / rel
        installed = manifest.get(rel)
        user_changed = dst.exists() and (installed is None or sha(dst) != installed)
        if rel in src:
            if dst.exists() and sha(dst) == sha(src[rel]):
                new_manifest[rel] = sha(dst)
                continue
            if user_changed and not force:
                report["kept"].append(rel)
                if installed:
                    new_manifest[rel] = installed  # 変更前の記録を残し、次回も変更ありとして扱う
                continue
            report["updated" if dst.exists() else "placed"].append(rel)
            if not dry:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src[rel].read_bytes())
                dst.chmod(src[rel].stat().st_mode & 0o777)
            new_manifest[rel] = sha(src[rel])
        elif dst.exists():  # ソースから無くなった・アンインストール
            if user_changed and not force:
                report["kept"].append(rel)
                continue
            report["removed"].append(rel)
            if not dry:
                dst.unlink()
    if not dry:
        if new_manifest:
            mp.parent.mkdir(parents=True, exist_ok=True)
            mp.write_text(json.dumps(new_manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        elif mp.exists():
            mp.unlink()
        for d in sorted({(target / r).parent for r in set(manifest) | set(src)}, key=lambda p: -len(p.parts)):
            while d != target and d.exists() and not any(d.iterdir()):
                d.rmdir()
                d = d.parent
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--user", action="store_true", help="~/.claude/ に置く（既定）")
    g.add_argument("--project", metavar="DIR", help="DIR/.claude/ に置く")
    p.add_argument("--uninstall", action="store_true")
    p.add_argument("--force", action="store_true", help="インストール後に変更されたファイルも置き換える・削除する")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)

    scope = "project" if a.project else "user"
    target = (Path(a.project).resolve() / ".claude") if a.project else Path.home() / ".claude"
    if target.resolve() == SRC.resolve():
        sys.exit("エラー: ソースリポジトリ自身にはインストールできません（既にこの配置です）。")
    print(f"{'アンインストール' if a.uninstall else 'インストール'}先: {target}（{scope}）")
    rep = sync(target, a.uninstall, a.force, a.dry_run)
    for key, label in (("placed", "配置"), ("updated", "更新"), ("removed", "削除")):
        if rep[key]:
            print(f"  {label}: {len(rep[key])} ファイル")
    if rep["kept"]:
        print("  次のファイルはインストール後に変更された（またはインストーラが置いていない）ため、そのままにしました"
              "（置き換えるなら --force）:")
        for r in rep["kept"]:
            print(f"    {r}")
    sp = target / "settings.json"
    settings = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    new = merged_settings(settings, scope, remove=a.uninstall)
    if new != settings:
        print("  更新: settings.json（hooks・permissions）")
        if not a.dry_run:
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if a.dry_run:
        print("（--dry-run のため変更していません）")
    elif not a.uninstall:
        print("\n次の手順: プロジェクトで Claude Code を起動し /sdlc-init を実行してください"
              "（ランチャ scripts/sdlc・scripts/approve と CLAUDE.md の import を準備します）。")


if __name__ == "__main__":
    main()
