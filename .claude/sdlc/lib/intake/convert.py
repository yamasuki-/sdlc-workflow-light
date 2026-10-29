#!/usr/bin/env python3
"""要求ドキュメント（xlsx / docx / pptx / pdf / md）を共通中間形式（Markdown＋出典メタデータ）に変換する。

  scripts/sdlc intake input/要求仕様.xlsx [input/...] [--out docs/01-specification/intake]

出力: docs/01-specification/intake/<ファイル名>.md（断片ごとに SRC-ID・出典・種別・確信度）
     docs/01-specification/intake/assets/（画像化した図。phase-specification で読み取る）
工程 01 のゲートが承認済みの場合は実行できない（要求ドキュメントの変更は /change 経由）。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from intake import adapters
from sdlc_lib import gates
from sdlc_lib.config import find_root, load_project, project_problems
from sdlc_lib.state import now

SRC_RE = re.compile(r"^###\s+SRC-(\d+)", re.MULTILINE)


def next_src(out_dir: Path) -> int:
    nums = [0]
    for p in out_dir.glob("*.md"):
        nums += [int(n) for n in SRC_RE.findall(p.read_text(encoding="utf-8"))]
    return max(nums) + 1


def render(rel_input: str, fmt: str, sha: str, frags, start: int) -> tuple[str, int]:
    lines = [f"# 取り込み: {Path(rel_input).name}", "",
             f"- 入力: {rel_input}", f"- 形式: {fmt}", f"- SHA-256: {sha}", f"- 取り込み日時: {now()}",
             f"- 断片数: {len(frags)}（確信度 低: {sum(1 for f in frags if f.confidence == '低')}）", ""]
    n = start
    for f in frags:
        lines += [f"### SRC-{n:03d}", "", f"- 出典: {rel_input} / {f.source}", f"- 種別: {f.kind}",
                  f"- 確信度: {f.confidence}"]
        for note in f.notes:
            lines.append(f"- 注記: {note}")
        for a in f.assets:
            lines.append(f"- 画像: [{Path(a).name}](assets/{Path(a).name})")
        lines += ["", *[f"> {t}" if t else ">" for t in f.text.splitlines()], ""]
        n += 1
    return "\n".join(lines), n


def main(argv=None):
    p = argparse.ArgumentParser(prog="scripts/sdlc intake", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inputs", nargs="+")
    p.add_argument("--out", default="docs/01-specification/intake")
    a = p.parse_args(argv)

    root = find_root()
    proj = load_project(root)
    if project_problems(proj):
        sys.exit("エラー: project.yaml が不完全です。/sdlc-init を先に実行してください。")
    if gates.gate_status(root, proj, "01-specification")["valid"]:
        sys.exit("エラー: 工程 01 は承認済みです。要求ドキュメントの変更は /change（変更要求）で扱ってください。")
    out_dir = root / a.out
    out_dir.mkdir(parents=True, exist_ok=True)
    assets = out_dir / "assets"
    rel_assets = assets.relative_to(root).as_posix()
    n = next_src(out_dir)
    for inp in a.inputs:
        path = Path(inp).resolve()
        rel = path.relative_to(root).as_posix()
        if not rel.startswith("input/"):
            sys.exit(f"エラー: 要求ドキュメントは input/ 配下に置いてください: {rel}")
        dst = out_dir / f"{path.stem}.md"
        if dst.exists():
            sys.exit(f"エラー: {dst.relative_to(root)} は既に存在します（ID の重複を避けるため上書きしません）。")
        mod = adapters.get(path.suffix)
        frags = mod.convert(path, assets, rel_assets)
        text, n2 = render(rel, path.suffix.lstrip("."), gates.sha256_file(path), frags, n)
        dst.write_text(text, encoding="utf-8")
        low = sum(1 for f in frags if f.confidence == "低")
        print(f"{rel} → {dst.relative_to(root)}: SRC-{n:03d}〜SRC-{n2 - 1:03d}（{len(frags)} 件、確信度 低 {low} 件）")
        n = n2


if __name__ == "__main__":
    main()
