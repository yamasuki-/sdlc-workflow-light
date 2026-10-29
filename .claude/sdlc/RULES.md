# SDLC ワークフロー（軽量版） 全体ルール

このリポジトリは、要求ドキュメントを入力に 4 つの工程で開発を進める軽量なワークフローです。
**進め方に迷ったら `/sdlc` を実行する**（状態を読んで次の工程を起動する）。

```
01 要件・仕様 ──[人間ゲート]──> 02 設計 ──> 03 実装 ──> 04 受入確認（人がテスト項目を確認）──> 完了
```

## 考え方

- **人の意思が入るのは「振る舞い」だけ**: 要件・仕様（何を作り、どう振る舞うか）と、それを確かめるテスト項目（何を見れば OK か）を
  01 でまとめて人が承認する。これが唯一の人間ゲート（既定）。
- **設計は AI が実装するのに足りれば十分**: 02・03 は人のゲートを置かず、機械チェックと AI レビューに合格したら進む。
  人が見たい工程は `project.yaml` の `gates` に追加できる。
- **TDD はしない。単体テストは最小限**: 自動テストは結合テストを中心にし、単体テストは計算・変換・判定などの
  ロジックだけに書く。人が見て確認することを前提に、**テスト項目リスト（TC）**で何を見ればよいかを明確にする。

## 絶対ルール

1. **人間ゲートは人だけが承認する**: 承認は人が端末で `scripts/approve <工程>` を実行して `state/gates/` に記録する。
   - Claude は `scripts/approve` を実行しない・`state/gates/` に書き込まない（hook で拒否される）。
   - 承認待ちになったら、提示内容とコマンドを人に伝えて**停止する**。
   - ワークフロー本体（`.claude/sdlc`・hooks・SDLC のスキル/エージェント・設定ファイル・ランチャ）を、hooks の検査を
     迂回する方法（スクリプト経由の書き換え、コマンドへの `SDLC_MAINTENANCE=1` の付与など）で変更しない。
2. **承認済みの要件・仕様は変更しない**: 変更すると成果物ハッシュが変わりゲートが無効になる。
   振る舞いを変えたい・機能を足したいなら `/change`（01 からやり直し、01 の再承認で合意する）。
   仕様どおりに作れていない（作り間違い）なら `/defect`（02 か 03 からやり直す）。
3. **受入確認の結果は人が記入する**: 結果シート `docs/04-acceptance/results.md` の「結果」列は人が記入する。
   Claude は記入しない（hook で拒否される）。TC の反映・再確認の差し戻し・Excel の取り込みは `scripts/sdlc testitems` で行う。
   Claude が自動テストや画面操作で確認できたことがあっても、手動確認の TC の結果は人に記入してもらう。
4. **トレーサビリティ**: 要求 → 仕様 → テスト項目（REQ → SPEC/NFR → TC）は必須。`scripts/sdlc trace check` が通ること。
   種別「自動」「両方」の TC には、テストコードに `trace: TC-xxx` を付ける。設計（DS）・コードへのトレースは任意。
5. **単体テストは最小限**: 書くのは、条件分岐や計算が多く結合テストでは確かめにくいロジックだけ。
   画面・API・DB を通した振る舞いは結合テスト（自動）か手動の TC で確かめる。
6. **言語非依存**: 言語・テストフレームワーク・コマンドは `project.yaml` だけに書く。ワークフロー本体に持ち込まない。
7. **並行度は最大 2**（Claude Pro 前提）。並行させる作業は担当ファイルが重ならないこと。
8. **状態はファイルに残す**: 進捗は `scripts/sdlc` で `state/` に記録する。中断しても `/sdlc` で再開できるようにする。
9. **機械チェック → レビュー → 完了判定の順**: `scripts/sdlc check` の MUST が失敗している間、
   またはレビュー判定が「不合格」の間は、工程を完了できない（人間ゲートも承認できない）。
10. **決定事項・未解決事項は一元管理**: `state/decisions.md` / `state/open-questions.md` はオーケストレータ（メインセッション）だけが
    `scripts/sdlc decision|question` で追記する。サブエージェントは結果報告で返す。推測で決めず、不明点は未解決事項にする。
11. **セキュリティレビューは随時**: セキュリティの専門レビューは工程に組み込まず、人が必要なときに `/sdlc-security` で実施する
    （全体・差分・パスを対象に `docs/security/` に報告を残す。工程の状態と完了判定は変えない）。所見は人が選んで `/defect` で直す。
12. **プロジェクト固有ルール**: `rules/common.md`・`rules/<工程ID>.md`・`rules/review-<工程ID>.md` があれば従う。

## ID 体系とトレース記法

| 接頭辞 | 工程 | 内容 | 必須 |
|---|---|---|---|
| SRC | 01 | 要求ドキュメントの断片（取り込み。出典・確信度付き） | 取り込んだ場合 |
| REQ / NFR / Q | 01 | 要求 / 非機能要件 / 質問 | ○ |
| SPEC | 01 | 振る舞い仕様（画面・API・業務ルール・エラー時の振る舞い） | ○ |
| TC | 01 | テスト項目（何を見れば OK か。種別: 手動・自動・両方） | ○ |
| DS | 02 | 設計要素（モジュール等） | 任意 |
| DEF / CR | — | 不具合票（`/defect`）/ 変更要求票（`/change`） | — |

- 定義: Markdown の見出し `### SPEC-001: タイトル`（ID は 3 桁以上、全体で一意）
- 追跡元: 定義ブロック内に `- 追跡元: REQ-001, REQ-002`
- TC の種別: 定義ブロック内に `- 種別: 手動 | 自動 | 両方`
- コード・テスト: コメントに `trace: TC-007`（言語のコメント記法で書く。設計 ID `DS-003` を書けば影響範囲の分析に使われる）
- 下流が不要な項目: 定義ブロック内に `- 対象外: 理由`。要求にしない取り込み項目は `- 除外: SRC-005（理由）`

## ディレクトリ

| パス | 内容 | 書き込み |
|---|---|---|
| `input/` | 要求ドキュメント原本（xlsx/docx/pptx/pdf/md） | 01 の承認前のみ |
| `docs/01-specification/` | 要求・仕様・テスト項目・質問（`intake/` に取り込み結果） | 01 の承認前のみ |
| `docs/02-design/` | 設計書 | 01 の承認後（02 にゲートを追加した場合はその承認前） |
| `docs/03-implementation/`・`src_dir`・`test_dir` | コード・テスト・確認の補足（`test-notes.md`） | 同上 |
| `docs/04-acceptance/` | 計画・レポート。`results.md`（結果シート）は**人だけ**が記入 | 同上 |
| `docs/security/` | 随時のセキュリティレビューの報告（`/sdlc-security`） | いつでも |
| `state/` | phase.json・defects・changes・decisions.md・open-questions.md（`gates/` 以外） | `scripts/sdlc` 経由で更新（票は Edit 可） |
| `rules/` | プロジェクト固有ルール・追加のレビュー観点。雛形は `<SDLC>/templates/rules/` | 人が管理（再発防止の観点は Claude が追記） |
| `scripts/sdlc`・`scripts/approve` | 本体へのランチャ（`scripts/sdlc init` が生成） | 不可 |

## よく使うコマンド

シェルコマンドは **Bash ツール**で実行する（Windows でも Git Bash）。PowerShell で実行する場合はランチャを
`scripts\sdlc.cmd ...` と呼ぶ。`scripts/approve`（`scripts\approve.cmd`）は人だけが実行する。

```
scripts/sdlc status                 # 現在工程・ゲート・次のアクション
scripts/sdlc phase step <step>      # ステップの記録（plan / work / review / gate）
scripts/sdlc phase advance          # 工程を完了して次へ（人間ゲート、または機械チェック＋レビュー判定）
scripts/sdlc check [工程]           # 機械チェック（docs/<工程>/checks.md に記録）
scripts/sdlc trace check            # トレーサビリティ検査
scripts/sdlc trace impact <ID...>   # 影響範囲（下流）
scripts/sdlc intake <ファイル...>   # 要求ドキュメントの取り込み（01）
scripts/sdlc testitems sheet        # 結果シートを TC 一覧に合わせて作成・更新（記入済みの結果は残る）
scripts/sdlc testitems export       # 結果シートを Excel に出力（任意）
scripts/sdlc testitems import <xlsx>  # Excel に記入された結果を取り込む
scripts/sdlc testitems reset <TC...> | --item <DEF/CR>   # 再確認のため未実施に戻す
scripts/sdlc testitems report [--write]   # 仕様ごとの確認状況
scripts/sdlc defect new|start|close / change new|start|close
scripts/sdlc security scan [--out <md>]  # project.yaml の security.tools を実行（/sdlc-security）
scripts/sdlc security list          # セキュリティレビューの報告の一覧
scripts/sdlc decision add "..." / question add|answer|list
scripts/sdlc path <相対パス>        # 本体のファイル（<SDLC>/…）の実際のパス
```

工程内の進め方は `<SDLC>/phase-flow.md`（全工程共通の型）に従う。

## ワークフロー本体の配置と `<SDLC>` 表記

本体は `~/.claude/`（全プロジェクト共通）またはプロジェクトの `.claude/`（そのプロジェクト専用・上書き）に置かれている。
スキル・エージェント・この文書の `<SDLC>/…` は本体のファイル（共通フロー・テンプレート・チェックリスト）を表す。
**`scripts/sdlc path <…>` で実際のパスを得てから読む**（例: `scripts/sdlc path templates/review.md`）。
プロジェクトの `.claude/sdlc/` にあればそれ、無ければ `~/.claude/sdlc/` のファイルが返る（ファイル単位で上書きできる）。
本体のファイルは全プロジェクト共通なので編集しない。プロジェクト固有のことは `rules/` に書く。
