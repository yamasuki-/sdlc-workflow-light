"""機械チェック（LLM レビューと工程の完了判定の前段）。

project.yaml の checks に、工程ごと（と全工程共通の common）に 3 階層でコマンドを書く:
  MUST   … 失敗したらレビューに進めない・工程を完了できない（人間ゲートも承認できない）
  SHOULD … 警告。レビュアーが判断する
  MAY    … 参考情報
組み込みの MUST:
  trace       … トレーサビリティ検査（全工程）
  test        … commands.test が成功すること（03 実装・04 受入確認）
  acceptance  … 結果シートの手動確認がすべて OK / 対象外であること（04 受入確認）
コマンドが見つからない（終了コード 127）場合は失敗ではなく skipped（未インストール）として扱う。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from . import testitems, trace
from .config import phase_id, phase_index, phase_name
from .shell import run_shell
from .state import now

LEVELS = ("must", "should", "may")
LEVEL_LABEL = {"must": "MUST", "should": "SHOULD", "may": "MAY"}
TEST_PHASES = ("03-implementation", "04-acceptance")


def _entries(items) -> list[dict]:
    out = []
    for i, it in enumerate(items or [], 1):
        cmd = str((it.get("cmd") if isinstance(it, dict) else it) or "").strip()
        name = str(it.get("name") or "") if isinstance(it, dict) else ""
        name = name or (cmd.split()[0] if cmd else f"check{i}")
        if cmd:
            out.append({"name": name, "cmd": cmd})
    return out


def configured(proj: dict, phase) -> dict[str, list[dict]]:
    cfg = proj.get("checks") or {}
    pid = phase_id(phase)
    out = {lv: [] for lv in LEVELS}
    for key in ("common", pid):
        block = cfg.get(key) or {}
        for lv in LEVELS:
            out[lv] += _entries(block.get(lv))
    return out


def _run_cmd(root, cmd: str, timeout: int) -> tuple[str, int | None, str]:
    try:
        r = run_shell(cmd, root, timeout)
    except subprocess.TimeoutExpired:
        return "fail", None, f"タイムアウト（{timeout} 秒）"
    out = (r.stdout + r.stderr).strip()
    if r.returncode == 127:  # シェルがコマンドを見つけられなかった = 未インストール
        return "skipped", r.returncode, out[-1500:]
    return ("pass" if r.returncode == 0 else "fail"), r.returncode, out[-1500:]


def _item(level, name, cmd, problems: list[str], ok_text="OK"):
    return {"level": level, "name": name, "cmd": cmd, "status": "fail" if problems else "pass",
            "rc": 1 if problems else 0, "output": "\n".join(problems[:50]) or ok_text}


def run(root, proj: dict, phase) -> dict:
    pid = phase_id(phase)
    g = trace.build(root, proj)
    items = [_item("must", "trace", f"scripts/sdlc trace check --upto {pid}", trace.check(g, phase_index(pid)))]
    timeout = int(proj.get("check_timeout_sec") or 300)
    if pid in TEST_PHASES:
        cmd = str(proj["commands"].get("test") or "").strip()
        status, rc, out = _run_cmd(root, cmd, timeout) if cmd else ("fail", None, "commands.test が未設定")
        if status == "skipped":
            status = "fail"   # テストが実行できないのは未インストールの任意ツールとは違い、完了させない
        items.append({"level": "must", "name": "test", "cmd": cmd, "status": status, "rc": rc, "output": out})
    if pid == "04-acceptance":
        items.append(_item("must", "acceptance", f"（組み込み）{testitems.RESULTS_FILE} の手動確認結果",
                           testitems.problems(root, g)))
    for lv, entries in configured(proj, pid).items():
        for e in entries:
            status, rc, out = _run_cmd(root, e["cmd"], timeout)
            items.append({"level": lv, "name": e["name"], "cmd": e["cmd"], "status": status, "rc": rc, "output": out})
    counts = {lv: {s: sum(1 for i in items if i["level"] == lv and i["status"] == s)
                   for s in ("pass", "fail", "skipped")} for lv in LEVELS}
    return {"phase": pid, "at": now(), "items": items, "counts": counts,
            "must_passed": counts["must"]["fail"] == 0,
            "skipped": [i["name"] for i in items if i["status"] == "skipped"]}


def report_path(root, phase) -> Path:
    return Path(root) / "docs" / phase_id(phase) / "checks.md"


def render(res: dict) -> str:
    pid = res["phase"]
    verdict = "PASS" if res["must_passed"] else "FAIL（MUST 失敗あり）"
    lines = [f"# 機械チェック結果: {pid} {phase_name(pid)}", "", f"- 実行日時: {res['at']}",
             f"- 判定: **{verdict}**", "", "| 階層 | pass | fail | skipped（未インストール） |", "|---|---|---|---|"]
    for lv in LEVELS:
        c = res["counts"][lv]
        lines.append(f"| {LEVEL_LABEL[lv]} | {c['pass']} | {c['fail']} | {c['skipped']} |")
    if res["skipped"]:
        lines += ["", "未インストールのため実行できなかったチェック（CI で必ず実行すること）: "
                  + ", ".join(res["skipped"])]
    for lv in LEVELS:
        its = [i for i in res["items"] if i["level"] == lv]
        if not its:
            continue
        lines += ["", f"## {LEVEL_LABEL[lv]}"]
        for i in its:
            lines += ["", f"### {i['name']} — {i['status']}", "", f"- コマンド: `{i['cmd']}`", f"- 終了コード: {i['rc']}"]
            if i["status"] != "pass" and i["output"]:
                lines += ["", "```", *i["output"].splitlines()[-50:], "```"]
    return "\n".join(lines) + "\n"


def summary_line(res: dict) -> str:
    c = res["counts"]
    return (f"{'PASS' if res['must_passed'] else 'FAIL'}"
            f"（MUST 失敗 {c['must']['fail']}・SHOULD 警告 {c['should']['fail']}・MAY {c['may']['fail']}・"
            f"未インストール {len(res['skipped'])}）")


def security_scan(root, proj: dict) -> list[dict]:
    """project.yaml の security.tools（依存脆弱性・SAST・シークレットスキャン等）を実行する（/sdlc-security が使う）。

    工程の完了判定には使わない。終了コード 0 以外は「検出あり」として出力をレビュアーに渡す。
    """
    timeout = int(proj.get("check_timeout_sec") or 300)
    out = []
    for e in _entries((proj.get("security") or {}).get("tools")):
        status, rc, text = _run_cmd(root, e["cmd"], timeout)
        out.append({"name": e["name"], "cmd": e["cmd"], "status": {"pass": "OK", "fail": "検出あり・失敗",
                    "skipped": "未インストール"}[status], "rc": rc, "output": text})
    return out


def render_security(items: list[dict]) -> str:
    if not items:
        return ("セキュリティツールは未設定です（project.yaml の security.tools に依存脆弱性スキャン・SAST・"
                "シークレットスキャン等を書くと実行されます）。\n")
    lines = ["| ツール | コマンド | 結果 | 終了コード |", "|---|---|---|---|"]
    lines += [f"| {i['name']} | `{i['cmd']}` | {i['status']} | {i['rc']} |" for i in items]
    for i in items:
        if i["status"] != "OK" and i["output"]:
            lines += ["", f"### {i['name']}", "", "```", *i["output"].splitlines()[-80:], "```"]
    return "\n".join(lines) + "\n"


def review_verdicts(root, phase) -> list[tuple[str, str]]:
    """docs/<工程>/ の *review*.md から判定行を拾う。"""
    out = []
    for p in sorted(Path(root, "docs", phase_id(phase)).glob("*review*.md")):
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip().lstrip("-*").strip().replace("**", "")
            if s.startswith(("判定", "残指摘", "verdict")):
                out.append((p.relative_to(root).as_posix(), s))
    return out


def review_failed(root, phase) -> list[str]:
    return [f"{path} の判定が不合格" for path, line in review_verdicts(root, phase)
            if line.startswith(("判定", "verdict")) and ("不合格" in line or "fail" in line.lower())]
