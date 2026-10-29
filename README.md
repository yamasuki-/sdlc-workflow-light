# sdlc-workflow-light

Claude Code 上で動く、**軽量版**のソフトウェア開発ワークフローです。
[sdlc-workflow](https://github.com/yamasuki-/sdlc-workflow)（V 字モデル・8 工程・全工程ゲート・TDD）を元に、
**人の意思が入るのは「振る舞い」（要件・仕様）だけ**に絞りました。

- 要件・仕様と「何を見れば OK か」（テスト項目リスト）を、**人が 1 回だけ承認**する
- 設計は AI が実装するのに足りれば十分。設計・実装は機械チェックと AI レビューで進む（人のゲートは任意で追加）
- **TDD はしない。単体テストは最小限**。自動テストは結合テストを中心にし、最後は人がテスト項目リストを見て確認する
- 結果の記入は Markdown が基本。Excel の出力・取り込みもできる

本家とは同居させません（同じ名前の `/sdlc`・`scripts/sdlc` を使います）。**インストールと使い方は [USAGE.md](USAGE.md)**。

対応環境: Linux / macOS / Windows（Git for Windows の Git Bash と Python 3.10 以上）。

## 全体像

```
/sdlc（最上位）… state/ を読んで次の工程スキルを起動するだけ
 ├─ 工程スキル phase-*（全工程が同じ型: 計画 → 作成 → レビュー → 完了判定）
 ├─ /defect … 不具合（仕様どおりに作れていない）。設計か実装からやり直し、人が TC を再確認
 ├─ /change … 変更要求（振る舞いを変える）。仕様を直して 01 を再承認し、差分でやり直し
 ├─ /sdlc-security … セキュリティレビュー。工程とは別に、必要なときに随時実施（全体・差分・パス）
 └─ サブエージェント analyst / tester / implementer / reviewer / security-reviewer
```

| 工程 | 主な成果物 | 担当 | 完了判定（既定） |
|---|---|---|---|
| **01 要件・仕様** | 取り込み（SRC）、要求 REQ・非機能 NFR・質問 Q、**振る舞い仕様 SPEC**、**テスト項目 TC** | analyst / tester | **人間ゲート**（唯一） |
| 02 設計 | 設計書（構成・モジュール・IF・データ・テスト方針。コード片可） | implementer | 機械チェック＋AI レビュー |
| 03 実装 | コード、結合テスト（種別「自動」の TC）、最小限の単体テスト、手動確認の補足 | implementer / tester | 機械チェック（テスト成功）＋AI レビュー |
| 04 受入確認 | 結果シート（**人が記入**）、確認状況レポート | 人（Claude は準備・集計・起票） | 手動の TC がすべて OK |

`project.yaml` の `gates` に `02-design` などを追加すると、その工程も人の承認を必要にできます。

## テスト項目リスト（TC）

仕様ごとに「何を見れば OK か」を 01 で作り、仕様と一緒に人が承認します。

```markdown
### TC-001: 貸出上限を超えると借りられない
- 追跡元: SPEC-003
- 種別: 手動 | 自動 | 両方
- 前提: 3 冊借りている社員でログインしている
- 手順:
  1. 在庫のある本の「借りる」を押す
- 確認ポイント: 画面上部のメッセージ、貸出一覧の件数
- 期待結果: 「同時に借りられるのは 3 冊までです」と表示され、貸出一覧は 3 件のまま
```

- 種別「自動」「両方」は 03 で結合テストにします（テストコードに `trace: TC-001`）。テストコードが無いと 03 を完了できません。
- 種別「手動」「両方」は 04 で人が確認し、`docs/04-acceptance/results.md` の「結果」列に OK / NG / 保留 / 対象外 を記入します。
  Claude は記入できません（hook で拒否）。Excel で記入したい場合は `scripts/sdlc testitems export` → 記入 → `import`。
- NG は不具合として起票し `/defect` で直し、該当 TC を人が再確認します。

## 使い方（概要）

```bash
pip install -r requirements.txt     # 本体の依存（Python 3.10+）
python3 install.py --user           # ~/.claude/ に配置（プロジェクト単体なら --project <dir>）
cd <プロジェクト> && claude
> /sdlc-init                        # ランチャ scripts/sdlc・CLAUDE.md の import・project.yaml を準備
# input/ に要求ドキュメントを置く
> /sdlc                             # 01 要件・仕様を作り、人間ゲートで停止する
scripts/approve 01                  # 人が端末で承認（Claude からは実行できない）
> /sdlc                             # 02 設計 → 03 実装 → 04 受入確認（結果の記入を依頼して停止）
# docs/04-acceptance/results.md に結果を記入（または Excel で記入して取り込む）
> /sdlc                             # NG があれば /defect、すべて OK なら完了
```

## 品質の仕組み

| 仕組み | 内容 |
|---|---|
| 人間ゲート | 01（と `gates` で追加した工程）。人が `scripts/approve` で承認すると成果物の SHA-256 を記録し、承認後の変更はハッシュ不一致で検知する |
| 機械チェック | `scripts/sdlc check`。組み込みの MUST: トレース（REQ→SPEC/NFR→TC、自動 TC→テストコード）、`commands.test` の成功（03・04）、結果シートの手動確認がすべて OK（04）。ほかに `project.yaml` の `checks`（MUST / SHOULD / MAY） |
| AI レビュー | reviewer（作成者と別コンテキスト・チェックリスト＋`rules/review-*.md`）。判定「不合格」の間は工程を完了できない |
| 結果シートの保護 | `results.md` / `results.xlsx` は Claude の Write / Edit・シェルからの書き込みを拒否。CLI の `testitems sheet / reset / import` だけが更新する |
| /defect | 再現 → エビデンス付きの原因特定 → 02 か 03 からやり直し → 自動テスト追加 → `retest` の TC を人が再確認 → close |
| /change | 現行確認 → SPEC/TC の差分 → 01 を再承認（変更の合意）→ 02・03 を差分でやり直し → 追加・変更した TC を人が確認 → close |
| /sdlc-security | 工程とは別に随時実施。`project.yaml` の `security.tools`（依存脆弱性・SAST・シークレットスキャン）を実行し、security-reviewer がチェックリスト（OWASP Top 10 ほか）でレビューして `docs/security/` に報告。工程の完了判定は止めず、所見は人が選んで `/defect` で直す |

## 強制の仕組み（hooks）

| 仕組み | 内容 |
|---|---|
| ゲート（`guard_write.py`） | 工程 k の成果物は、k より前の人間ゲートがすべて有効なときだけ書き込める。承認済みの工程の成果物は変更不可。人間ゲートの無い工程（既定で 02〜04）は自由に直せる |
| 結果シート（`guard_write.py`・`guard_bash.py`） | `docs/04-acceptance/results.md`・`results.xlsx` への Claude の書き込みを拒否 |
| 自己承認の防止 | `state/gates/` への書き込みは常に拒否。`scripts/approve` は TTY 必須で、Claude Code から起動されたプロセスでは動かない |
| 設定ファイル・本体の保護 | `~/.claude/settings*.json` と本体（`.claude/sdlc`・hooks・SDLC のスキル/エージェント・ランチャ）は Claude が編集できない |
| 工程スキル起動（`guard_skill.py`） | 前の人間ゲートが無効なら `phase-*` スキルの起動を拒否 |
| 適用範囲 | `~/.claude` の hooks は `project.yaml` に `workflow: sdlc` があるプロジェクトでだけ検査する |

本家との違い: TDD ガード（失敗テストが無いと src を編集できない）・単体テストの凍結・タスク DAG・工程ごとの書き込み制限（ゲートの無い工程）は持ちません。
セキュリティレビューは実装工程のゲートではなく、`/sdlc-security` で随時行います。

### 限界

- Bash 経由の改変検出はヒューリスティックです。すり抜けても、人が承認した成果物の改変はゲートのハッシュ不一致で検知されます。
- 結果シートは CLI（`testitems import` など）からは更新できるため、Claude が Excel を作って取り込むことは技術的には防げません
  （ルールで禁止）。結果シートの変更は git の履歴で確認してください。
- テストを `src_dir` 配下に置く言語慣習（Go の `_test.go` など）には対応していません（`test_dir` は別ディレクトリ）。

## ワークフロー本体の保守

本体（`.claude/sdlc/`・`.claude/hooks/sdlc/`・SDLC のスキル/エージェント・`.claude/settings.json`）は、
Claude による編集が hook で禁止されています（このソースリポジトリも同様）。変更するときは環境変数を付けて起動します:

```bash
SDLC_MAINTENANCE=1 claude
```

自己テスト:

```bash
python3 -m unittest discover -s tests -v
```

## ディレクトリ

### 本体（`~/.claude/` またはプロジェクトの `.claude/` に置く）

```
sdlc/
  RULES.md                    全体ルール。プロジェクトの CLAUDE.md から import
  phase-flow.md               工程内共通フロー
  templates/                  成果物テンプレート（requirements / questions / spec / test-items / design / test-notes /
                              plan / summary / review / security-review / project.yaml、rules/ の雛形）
  checklists/                 レビューチェックリスト（01・02・03・defect・change・security）
  bin/sdlc                    状態管理 CLI
  bin/approve                 人が実行する承認スクリプト
  bin/py                      本体を動かす Python を探して実行する（SDLC_PYTHON で指定可）
  lib/sdlc_lib/               共通ライブラリ（ゲート・トレース・テスト項目・機械チェック・割り込み票）
  lib/intake/                 取り込みの形式別アダプタ（xlsx / docx / pptx / pdf / md）
hooks/sdlc/                   ゲート・結果シート・シェル・スキル起動のガード（入口は bash の run）
skills/                       sdlc, sdlc-init, phase-specification, phase-design, phase-implementation,
                              phase-acceptance, defect, change, sdlc-security
agents/                       analyst, tester, implementer, reviewer, security-reviewer
settings.json                 hooks と permissions（インストーラが追記）
```

### プロジェクト

```
CLAUDE.md                     全体ルールの import（scripts/sdlc init が追加）
project.yaml                  プロジェクト固有情報（workflow: sdlc、言語・テスト・コマンド・gates）
scripts/sdlc, scripts/approve 本体へのランチャ（Windows 用の .cmd も）
input/                        要求ドキュメント原本
docs/01-specification/        intake/（取り込み）、requirements.md、questions.md、spec-*.md、test-items-*.md
docs/02-design/               design.md
docs/03-implementation/       test-notes.md（手動確認の補足）
docs/04-acceptance/           results.md（結果シート。人が記入）、results.xlsx（任意）、report.md
docs/security/                security-review-<日付>.md（/sdlc-security の報告）、scan-<日付>.md（ツールの結果）
state/
  phase.json                  現在工程・ステップ、割り込み対応の状態
  gates/<工程>.md             人間ゲートの承認記録（成果物ハッシュ付き）
  defects/DEF-xxx.md          不具合票
  changes/CR-xxx.md           変更要求票
  decisions.md / open-questions.md
rules/                        プロジェクト固有ルール・追加のレビュー観点
```

### このソースリポジトリ

```
.claude/                      本体（上の「本体」と同じ形。プロジェクト配置として hooks も有効）
install.py                    インストーラ（--user / --project <dir> / --uninstall / --dry-run）
tests/                        ワークフロー自己テスト
.github/workflows/tests.yml   自己テストを Linux / Windows / macOS で実行する CI
examples/                     動作確認用のサンプル要求ドキュメント
USAGE.md                      インストールと使い方
```
