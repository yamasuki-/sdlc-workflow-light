---
name: sdlc-security
description: セキュリティ観点のレビューを、工程の流れとは別に随時（実装後・リリース前・定期的に）実施する。対象は全体・指定コミットからの差分・指定パスのいずれか。project.yaml の security.tools を実行し、security-reviewer がチェックリスト（OWASP Top 10・入力検証・秘密情報・ビジネスロジック・DoS・LLM 機能・依存ライブラリ・インフラ定義・NFR）で調べて docs/security/ に報告を残す。工程の完了判定は止めない。所見は人が選んで不具合として起票する。
argument-hint: "[all | since <git ref> | <パス...>]"
---

# /sdlc-security — 随時のセキュリティレビュー

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/sdlc-security/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

軽量版では、セキュリティの専門レビューを工程（03 実装）に組み込まず、**人が必要なときにこのコマンドで実施する**。
工程の状態（`state/phase.json`）は変えず、工程の完了判定も止めない。どの工程の途中でも実行できる
（ただしコードがあることが前提。通常は 03 実装の後か、04 受入確認・リリースの前）。

```
対象範囲を決める → セキュリティツールを実行 → security-reviewer がレビュー → 報告（docs/security/）→ 人が所見の扱いを決める → 起票
```

## 1. 対象範囲を決める

引数で決める。無ければ、前回の報告（`scripts/sdlc security list`）があれば「前回の対象コミットからの差分」を、無ければ「全体」を提案し、
AskUserQuestion で確認する。

| 引数 | 対象 |
|---|---|
| `all` | `src_dir` 全体と依存定義（マニフェスト・ロックファイル）、インフラ・CI 定義（あれば） |
| `since <git ref>` | `git diff --name-only <ref>..HEAD` のファイル。変更箇所を呼ぶ・変更箇所から呼ばれる認証・認可・入力検証の経路も含める |
| `<パス...>` | 指定したファイル・ディレクトリ |

対象コミットは `git rev-parse HEAD` で記録する。未コミットの変更があれば、先にコミットするか、未コミット分も含めてよいか人に確認する。

## 2. セキュリティツールを実行する

```
scripts/sdlc security scan --out docs/security/scan-<YYYY-MM-DD>.md
```

`project.yaml` の `security.tools` に書いたコマンド（依存脆弱性スキャン・SAST・シークレットスキャン等）を実行する。
未設定なら、スタックに合うツールを人に提案してよい（設定は人が `project.yaml` に書くか、人の了承を得て Claude が書く）。
未インストールのツールは失敗ではなく「CI で実行が必要」として報告に残す。

## 3. レビュー（agent: **security-reviewer**、1 体）

依頼に含めるもの:
- 対象範囲・対象コミット・対象ファイル一覧、手順 2 の結果ファイル
- `<SDLC>/checklists/security.md`、`rules/review-security.md`（あれば）、`rules/common.md`
- 仕様の NFR（`docs/01-specification/requirements.md` 等のセキュリティ要件）と設計のセキュリティ（`docs/02-design/`）
- 前回の報告（あれば。未対応だった所見の解消状況を確かめる）
- 出力先: `docs/security/security-review-<YYYY-MM-DD>.md`（同じ日に 2 回目なら `-2` を付ける。テンプレート `<SDLC>/templates/security-review.md`）

## 4. 人への報告と所見の扱い

重大度別の件数と主な所見（Critical / High を先に）を人に示し、AskUserQuestion で扱いを決めてもらう:
- **不具合として起票する**（Critical / High は起票を推奨）→
  `scripts/sdlc defect new --title "[SEC-xx] <要約>" --severity <致命|高|中|低>` で起票し、票の「現象」に報告の所見と該当箇所を書く。
  修正は `/defect` で行う（原因が設計なら 02、実装なら 03 から。認可モデルなど仕様（NFR）の不足なら `/change`）。
  修正のときは、その脆弱性を検出する自動テストを追加する。
- **受容する**（理由を報告の「対応」列に書き、`scripts/sdlc decision add "SEC-xx を受容: <理由>" --source <報告ファイル>`）
- **後で対応する**（報告に残す。次回のレビューで解消状況を確認する）

報告の「対応」列を決まった扱い（DEF-xxx / 受容 / 未対応）に更新し、`git add docs/security && git commit -m "security review: <日付>"`。

## 注意
- 修正はこのスキルの中では行わない（起票して `/defect` に回す）。security-reviewer はコードを変更しない。
- 進行中の工程や割り込み対応（`/defect`・`/change`）がある場合も、このスキルは状態を変えない。起票した不具合は、
  `/sdlc` が次に案内する（進行中の対応が終わってから着手する）。
- 同じ種類の所見を繰り返さないための観点は `rules/review-security.md` に追記する（人の了承を得て）。
