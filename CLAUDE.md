# sdlc-workflow-light（軽量版ワークフロー本体のソースリポジトリ）

このリポジトリは SDLC ワークフロー軽量版の開発用です。利用者向けの使い方は `USAGE.md`、構成は `README.md`。
元にした本家は `yamasuki-/sdlc-workflow`（参照のみ。こちらから変更しない）。

## 軽量版の方針（変更時に守る）

- 人の意思が入るのは「振る舞い」（要件・仕様とテスト項目）だけ。既定の人間ゲートは 01 要件・仕様の 1 回。
  他の工程のゲートは `project.yaml` の `gates` で任意に追加する。
- 設計は AI が実装するのに足りれば十分（コード片可・人の承認なし）。
- TDD はしない。単体テストは最小限、結合テストと人による確認（テスト項目リスト TC）が中心。
- 受入確認の結果（`docs/04-acceptance/results.md`）は人だけが記入する。Markdown が基本、Excel の出力・取り込みは任意。

## 構成

- 本体はすべて `.claude/` 配下にあり、`install.py` がこの形のまま `~/.claude/`（全プロジェクト共通）または
  `<プロジェクト>/.claude/`（プロジェクト単体・上書き）に配置する。
  - `.claude/sdlc/` … 本体（`bin/`・`lib/`・`templates/`・`checklists/`・`phase-flow.md`・`RULES.md`）
  - `.claude/hooks/sdlc/` … ガード（hooks）
  - `.claude/skills/<SDLC のスキル>/`・`.claude/agents/<SDLC のエージェント>.md`
- 工程・置く対象の一覧は `.claude/sdlc/lib/sdlc_lib/config.py` の `PHASES`・`SKILL_NAMES`・`AGENT_NAMES`・`BODY_DIRS`・`BODY_FILES`。
  スキル・エージェントを追加・改名したらここも更新する。
- プロジェクトで使うときの全体ルールは `.claude/sdlc/RULES.md`（プロジェクトの CLAUDE.md から import される）。

## 開発のルール

- このリポジトリ自体もプロジェクト配置として hooks が有効なので、本体（`.claude/sdlc`・`.claude/hooks/sdlc` 等）の
  編集は `SDLC_MAINTENANCE=1` で起動したセッションで行う。
- 変更したら自己テストを通す: `python3 -m unittest discover -s tests`
- `.claude/settings.json` はインストーラのプロジェクト配置と同じ内容に保つ（自己テストで検査している）。
- 言語・テストフレームワーク固有の内容を本体に入れない（プロジェクトの `project.yaml`・`rules/` に置く）。
- 利用者に影響する変更は `USAGE.md` と `README.md` に反映する。
