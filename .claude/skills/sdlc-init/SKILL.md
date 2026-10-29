---
name: sdlc-init
description: プロジェクト固有情報 project.yaml（言語・テストフレームワーク・コマンド・ディレクトリ・人間ゲートを置く工程）を対話的に作成し、state/ と docs/ を初期化する。最初に一度、または project.yaml を直すときに使う。
---

# /sdlc-init — project.yaml の作成

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/sdlc-init/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

ワークフロー本体は言語非依存。言語・テストに関する情報はすべて `project.yaml` に置く。

## 手順

1. 本体が使う Python と依存関係を確認する:
   `bash "${CLAUDE_SKILL_DIR}/../../sdlc/bin/py" -c "import yaml, openpyxl, docx, pptx, pdfplumber"`
   失敗したら、その Python（`bash "${CLAUDE_SKILL_DIR}/../../sdlc/bin/py" --which` で分かる）に
   `-m pip install -r requirements.txt` で入れるよう人に依頼する（hooks も同じ Python で動く）。
2. **準備**: プロジェクトにランチャ `scripts/sdlc` が無ければ、本体を直接呼んで作る:
   `bash "${CLAUDE_SKILL_DIR}/../../sdlc/bin/py" "${CLAUDE_SKILL_DIR}/../../sdlc/bin/sdlc" init`
   これでランチャ（`scripts/sdlc`・`scripts/approve` と Windows 用の `.cmd`）、`state/`・`docs/`、`.gitignore`・`.gitattributes`、
   CLAUDE.md の全体ルール import（`@~/.claude/sdlc/RULES.md`、プロジェクト配置なら `@.claude/sdlc/RULES.md`）、
   `project.yaml` の雛形（`workflow: sdlc` 付き）が用意される。以降は `scripts/sdlc` を使う。
   既存の `project.yaml` があれば読む（`workflow: sdlc` が無ければ追加する）。
3. 既存コードやビルド定義（package.json, pyproject.toml, pom.xml, go.mod 等）があれば読み、候補を推定する。
4. AskUserQuestion で次を確認する（推定値があれば推奨として先頭に出す）:
   - 言語 / テストフレームワーク（結合テストを書ける構成か。画面があるなら E2E ツールも）
   - `commands.test`（全自動テスト。終了コード 0 = 全成功。03・04 の完了判定と不具合のクローズに使う）
   - 任意: `test_integration` / `lint`
   - `src_dir` / `test_dir`（重ならない別ディレクトリ）
   - **人間ゲートを置く工程**（`gates`）: 既定は `01-specification` だけ。設計・実装・受入確認も人が承認したい場合に追加する
5. 機械チェック（`checks`）を設定する。スタックに合うツールを MUST / SHOULD / MAY に振り分けて提案し、人に確認する:
   - MUST: 失敗したら先に進めないもの（例: lint、型検査、ビルド）
   - SHOULD: 警告扱い（例: 依存脆弱性スキャン、シークレットスキャン）
   - `common` は全工程、工程 ID のブロック（例 `03-implementation`）はその工程だけに適用される。
   - 自動修正するコマンド（`--fix` / `--write`）は使わない（検査のみ）。コマンドは bash の書式で書く。
   - 随時のセキュリティレビュー（`/sdlc-security`）で使うツール（依存脆弱性スキャン・SAST・シークレットスキャン）を
     `security.tools` に提案する（任意。工程の完了判定には使わない）。
6. `project.yaml` を書き、`scripts/sdlc project check` が通るまで直す。
7. `scripts/sdlc init` を再実行する（何度実行してもよい）。
8. プロジェクト固有ルールが要るか人に確認し、要るなら `<SDLC>/templates/rules/common.md` などを `rules/` にコピーして記入する
   （コーディング規約・テストの作法・追加のレビュー観点。言語・フレームワーク固有の内容はここに書く）。
9. `src_dir`・`test_dir` が無ければ作成し、`commands.test` が実行できること（テスト 0 件で成功または想定どおりの結果）を確認する。
10. `.gitignore` にビルド成果物・キャッシュ（言語に応じて）を追記する（ゲートのハッシュから除外される）。
11. 決めたこと（言語・ツールの選定理由など）を `scripts/sdlc decision add` で記録する。
12. `git add -A && git commit -m "sdlc-init: project.yaml"`。
13. 次の一手を伝える: 「`input/` に要求ドキュメントを置き、`/sdlc` を実行してください」。
