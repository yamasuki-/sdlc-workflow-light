---
name: phase-design
description: 工程02「設計」。承認済みの仕様（SPEC/NFR/TC）から、AI が実装するのに足りる粒度の設計書を 1 つ作る。既定では人間ゲートなし（機械チェックと AI レビューで完了判定）。
---

# 工程 02: 設計（02-design）

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/phase-design/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

まず `<SDLC>/phase-flow.md`（共通フロー）を読み、その型に従って進める。以下は本工程固有の内容のみ。

**目的は実装で迷わないこと**。体裁を整えた設計書や、人に説明するための資料は作らない。

## 入力 / 成果物
- 入力: `docs/01-specification/`（SPEC・NFR・TC・質問の回答・ゲートのコメント）、`project.yaml`、`rules/common.md`、既存コード
- 成果物（`docs/02-design/`）:
  - `design.md` … 構成・モジュール（`### DS-xxx` は任意）・IF・データ・エラー処理・セキュリティ・テスト方針（テンプレート `design.md`）。
    大きければ `design-<領域>.md` に分けてよい
  - `plan.md` / `summary.md` / `checks.md` / `review.md`

## 作成（agent: **implementer**）
- 小〜中規模なら implementer 1 体で `design.md` を書く。大きければ領域ごとに分け（並行は最大 2）、共通部分を先に書く。
- コード片・型定義・スキーマ・Mermaid を書いてよい。
- モジュールは 03 で**並行実装できる粒度**に分け、`src_dir` 内の配置（パス）を決める。
- **テスト方針**を必ず書く:
  - 種別「自動」「両方」の TC を、どの単位（API・画面操作・CLI・DB を含む結合）で自動化するか、テスト環境・データをどう用意するか
  - 単体テストを書くロジック（最小限）とその理由
  - 手動の TC を人が実施するための準備（起動方法・初期データ）
- 決めた技術判断は報告の「決定事項」に書かせ、オーケストレータが `scripts/sdlc decision add` で記録する。
- 仕様の不足・矛盾に気づいたら、勝手に仕様を補わず未解決事項にする。振る舞いを変える必要があれば人に伝え、`/change` を提案する。

## レビュー・完了判定
- reviewer にチェックリスト `02-design.md` を渡す（1 往復で十分なことが多い）。
- 人間ゲートが無ければ `scripts/sdlc phase advance` で 03 へ進み、そのまま `/phase-implementation` を続けてよい。
  `project.yaml` の `gates` に `02-design` があれば、人に承認を依頼して停止する。
