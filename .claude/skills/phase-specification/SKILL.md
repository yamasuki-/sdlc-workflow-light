---
name: phase-specification
description: 工程01「要件・仕様」。input/ の要求ドキュメントを取り込み（Excel/Word/PowerPoint/PDF/Markdown）、要求（REQ）・非機能要件（NFR）・質問（Q）・振る舞い仕様（SPEC）・テスト項目リスト（TC）を作る。人の意思が入る唯一の工程で、人間ゲートで承認を得る。
---

# 工程 01: 要件・仕様（01-specification）

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/phase-specification/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

まず `<SDLC>/phase-flow.md`（共通フロー）を読み、その型に従って進める。以下は本工程固有の内容のみ。

この工程が、人が「何を作り、どう振る舞えば OK か」を決める場である。**人に判断してもらうことを早めに・はっきり出す。**

## 入力 / 成果物
- 入力: `input/` の要求ドキュメント（.xlsx / .xlsm / .docx / .pptx / .pdf / .md）。原本もゲートのハッシュ対象。
- 成果物（`docs/01-specification/`）:
  - `intake/<ファイル名>.md`・`intake/assets/` … 取り込み結果（`### SRC-xxx`・出典・確信度）。`scripts/sdlc intake` が作る
  - `requirements.md` … `### REQ-xxx` と `### NFR-xxx`（テンプレート `requirements.md`）
  - `questions.md` … `### Q-xxx` 発注元・利用者への質問（テンプレート `questions.md`）
  - `spec-<領域>.md` … `### SPEC-xxx` 振る舞い仕様（テンプレート `spec.md`）
  - `test-items-<領域>.md` … `### TC-xxx` テスト項目（テンプレート `test-items.md`）
  - `plan.md` / `summary.md` / `checks.md` / `review.md`

## 計画（plan）
1. `input/` のファイル一覧を確認する（未対応形式は人に変換を依頼）。
2. **取り込みは計画ステップで機械的に実行する**（エージェント不要）:
   `scripts/sdlc intake input/<ファイル> [input/...]`
   変換結果の件数・確信度 低の件数・「要画像読取」の件数を plan.md に記録する。
3. 機能領域（入力ドキュメントの章・シート・画面群）を決め、領域ごとの採番範囲を割り当てる（例: 領域 A は SPEC-001〜099）。

## 作成（work）
1. **取り込みの仕上げ**（agent: **analyst**）: 「要画像読取」の断片の画像（`intake/assets/`）を Read ツールで読み、
   該当 SRC の本文を読取結果に置き換えて `- 読取: 画像から読み取り` と確信度を付ける。原文に無い内容を補わない。
2. **要求・質問**（analyst、`requirements.md`・`questions.md`）: すべての SRC を REQ に反映する（要求でない SRC は `- 除外:`）。
   曖昧・矛盾・欠落を Q にし、「回答が無い場合の仮定」を書く。NFR はカテゴリを一通り検討する。
3. **人への早めの確認**: 優先度 高の Q（答えで仕様が大きく変わるもの）は、SPEC を書く前に AskUserQuestion で人に聞き、
   回答を `questions.md` の「回答」に書く（ゲートまで溜めない）。答えが得られないものは仮定で進め、仮定を明記する。
4. **振る舞い仕様**（analyst、領域ごとに `spec-<領域>.md`。並行は最大 2）: 利用者から見た振る舞いを書く。
   入力・正常・業務ルール・**例外・エラー時**・表示/応答・権限。実装方法は書かない。
5. **テスト項目**（agent: **tester**、領域ごとに `test-items-<領域>.md`。対応する SPEC の作成後）:
   SPEC / NFR だけを見て「何を見れば OK か」を作る。正常・異常・境界を含め、種別（手動・自動・両方）を振り分ける。
   - 人が見る必要があるもの（画面の見た目・操作感・文言・業務として妥当か）は **手動** か **両方**
   - 計算・境界値・エラー応答の網羅は **自動**（03 で結合テストにする）
6. `scripts/sdlc trace check`（SRC→REQ→SPEC/NFR→TC が全件つながり、TC に種別があること）→ `scripts/sdlc check`。

## レビュー
- reviewer にチェックリスト `01-specification.md` を渡す。

## 完了判定（人間ゲート）
人に提示するときは、**仕様の要点**（画面・操作の一覧、主要な業務ルール、エラー時の振る舞い）、**仮定で進めた点**、
**手動確認になる TC の件数**（受入確認で人が見る量）を先に要約する。未回答の質問は、仮定で進めてよいかを判断してもらう。
人は `docs/01-specification/` を直接読み、必要なら差戻し（コメントに修正指示）する。
