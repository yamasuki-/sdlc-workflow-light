---
name: sdlc
description: SDLC ワークフロー（軽量版）の最上位オーケストレーター。state/ を読んで現在工程・ゲート状況を判定し、次の工程スキルを起動する（中断からの再開もこれで行う）。開発を進める・続きから再開するときに使う。
---

# /sdlc — 状態管理とルーティングのみ

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/sdlc/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

このスキルは「何を作るか」を持たない。状態を読み、次に起動すべきスキルを決めるだけである。

```
01 要件・仕様 ──[人間ゲート]──> 02 設計 ──> 03 実装 ──> 04 受入確認（人がテスト項目を確認）──> 完了
```

## 手順

0. プロジェクトにランチャ `scripts/sdlc` が無ければ、まだ準備されていないので `/sdlc-init` を起動する。
1. `scripts/sdlc status --json` を実行し、`next.action` を読む。
2. `next.action` に応じて 1 つだけ実行する:

| action | すること |
|---|---|
| `init` | `/sdlc-init` スキルを起動する |
| `need_input` | `input/` に要求ドキュメント（xlsx/docx/pptx/pdf/md）を置くよう人に依頼して停止 |
| `run_phase` / `revise` | `next.skill` のスキルを起動する（再開ステップは `next.step`、差戻しなら差戻し対応） |
| `advance` | `scripts/sdlc phase advance` を実行する。成功したら手順 1 に戻り、次工程のスキルを起動する。失敗したら表示された理由（機械チェック・レビュー判定）に従い、`next.skill` のスキルで直す |
| `await_approval` | 下記「承認待ちの提示」を行って**停止** |
| `blocked_upstream` | `next.message` を人に伝え、承認後の仕様変更なら `/change` で扱うことを提案して停止 |
| `defect` / `change` / `item_close` | `next.skill`（`defect` または `change`）のスキルを `next.item` を引数に起動する |
| `done` | `scripts/sdlc testitems report` と `scripts/sdlc trace matrix` の結果をまとめて報告して終了。`scripts/sdlc security list` で最新のコミットに対するセキュリティレビューが無ければ、`/sdlc-security` の実施を提案する |

3. 人間ゲートで停止したら、このスキルも停止する。
   **自分で `scripts/approve` を実行したり、承認を仮定して先へ進んだりしない。**
4. 人間ゲートの無い工程（既定では 02・03・04）は、完了したら止まらずに次の工程へ進んでよい。
   ただし 04 受入確認は人がテスト項目を確認するので、結果の記入を依頼して停止する（`phase-acceptance` の指示に従う）。

## 割り込みの受付

人から「仕様を変えたい・機能を足したい」と言われたら `/change`、「不具合がある・動きがおかしい」と言われたら `/defect` を起動する。
どちらか迷う場合は人に確認する（承認した仕様どおりに動いていないなら /defect、仕様そのものを変えるなら /change）。
「セキュリティを確認したい」と言われたら `/sdlc-security` を起動する（工程の状態は変えない。いつでも実行できる）。

## 承認待ちの提示

```
工程 <phase> は人による承認待ちです。
- 見てほしいもの: docs/<phase>/ の仕様（SPEC）とテスト項目（TC）
- レビュー報告: docs/<phase>/review.md
- 機械チェック: docs/<phase>/checks.md
- 未解決事項: scripts/sdlc question list（優先度 高があれば先に回答してください）
承認・条件付き承認・差戻しは、端末で次を実行してください:
  scripts/approve <phase>
記録後に /sdlc を実行すると続きから進みます。
```

## 再開について

使用量上限などで中断した場合も、`/sdlc` を実行すれば `state/phase.json`（工程・ステップ）から続きを判定する。
