---
name: phase-implementation
description: 工程03「実装」。設計に沿ってコードを書き、種別「自動」「両方」のテスト項目を結合テストとして自動化し、単体テストは最小限にする。人が手動確認するための補足（test-notes.md）も作る。TDD は行わない。既定では人間ゲートなし。
---

# 工程 03: 実装（03-implementation）

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/phase-implementation/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

まず `<SDLC>/phase-flow.md`（共通フロー）を読み、その型に従って進める。以下は本工程固有の内容のみ。

## 入力 / 成果物
- 入力: `docs/02-design/`、`docs/01-specification/`（SPEC・TC）、`project.yaml`、`rules/`
- 成果物:
  - `<src_dir>/` … 実装コード（`trace: DS-xxx` は任意）
  - `<test_dir>/` … 結合テスト（種別「自動」「両方」の TC ごとに `trace: TC-xxx`）と、設計で選んだロジックの単体テスト
  - `docs/03-implementation/` … `plan.md` / `test-notes.md`（手動確認の補足。テンプレート `test-notes.md`）/
    `summary.md` / `checks.md` / `review.md`

## 作成
1. **実装**（agent: **implementer**）: モジュール（設計の DS・領域）ごとに作業単位を分ける。並行は最大 2 で、
   担当ファイルが重ならない単位だけを `isolation: "worktree"` で並行させ、完了ごとに `git merge --no-ff` する。
   共有ファイル（共通型・設定）を触る作業は先に済ませる。実装者は動作確認のための単体テストを書いてよいが、最小限にする。
2. **結合テストとテスト項目の準備**（agent: **tester**、実装の後）:
   - 種別「自動」「両方」の TC を結合テストとして自動化する（各テストに `trace: TC-xxx`）。TC の期待結果をそのまま検証する。
   - `docs/03-implementation/test-notes.md` に、人が手動の TC を実施するための準備（起動方法・データ・URL・具体的な操作）を書く。
   - テストが失敗したら、テストを実装に合わせて変えずに理由を報告する（実装の誤りなら implementer に直させる。
     TC・仕様が誤っていると思われる場合は人に伝える）。
3. `commands.test`（と `lint`）を実行して全件成功を確認する → `scripts/sdlc trace check` → `scripts/sdlc check`
   （組み込みの MUST: 自動テストの TC にテストコードがあること、`commands.test` の成功）。

## レビュー・完了判定
- reviewer にチェックリスト `03-implementation.md` を渡す（セキュリティは基本の観点だけ）。
- セキュリティの専門レビューはこの工程では行わない。人が必要なときに `/sdlc-security` で実施する
  （工程の完了後に「必要なら `/sdlc-security` でセキュリティレビューができます」と一言添える）。
- 人間ゲートが無ければ `scripts/sdlc phase advance` で 04 へ進み、`/phase-acceptance` を続ける。
