---
name: phase-acceptance
description: 工程04「受入確認」。テスト項目リスト（TC）の結果シートを用意し、人が手動の TC を見て結果を記入する（Markdown が基本、Excel の出力・取り込みも可）。NG は不具合として起票し /defect に回す。全 TC が OK になれば完了。
---

# 工程 04: 受入確認（04-acceptance）

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/phase-acceptance/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

まず `<SDLC>/phase-flow.md`（共通フロー）を読み、その型に従って進める。以下は本工程固有の内容のみ。
この工程にはレビュー（reviewer）は無い。**確認するのは人**で、Claude は準備・集計・不具合の起票を行う。

## 入力 / 成果物
- 入力: TC（`docs/01-specification/test-items-*.md`）、`docs/03-implementation/test-notes.md`、動くアプリ
- 成果物（`docs/04-acceptance/`）:
  - `results.md` … 結果シート（手動・両方の TC）。**人だけが記入する**（Claude の Write / Edit は拒否される）
  - `results.xlsx` … Excel で記入する場合（任意）
  - `report.md` … 仕様ごとの確認状況（`scripts/sdlc testitems report --write`）
  - `plan.md` / `checks.md`

## 計画（plan）
1. `scripts/sdlc testitems sheet` で結果シートを作る（既にあれば TC の追加・削除を反映。記入済みの結果は残る）。
2. `commands.test` を実行し、自動テストが全件成功していることを確かめる（失敗していれば 03 の不具合として `/defect`）。
3. `plan.md` に、手動確認の件数・確認の順序（前提が共通のものをまとめる）・準備（test-notes.md の要点）を書く。
4. `scripts/sdlc phase step work`。

## 作成（work）— 人による確認
1. 人に確認を依頼して**停止する**:

   ```
   受入確認をお願いします（手動確認 <n> 件）。
   - テスト項目: docs/01-specification/test-items-*.md（何を見れば OK か）
   - 準備・操作の補足: docs/03-implementation/test-notes.md
   - 結果の記入先: docs/04-acceptance/results.md の「結果」列に OK / NG / 保留 / 対象外、確認者・日付・メモ
     （NG はメモに現象を、対象外は理由を書いてください）
   - Excel で記入する場合: `scripts/sdlc testitems export` で docs/04-acceptance/results.xlsx を出力します。
     記入後に `scripts/sdlc testitems import docs/04-acceptance/results.xlsx` で取り込みます（Claude に依頼しても可）。
   記入が終わったら /sdlc を実行してください。
   ```

   Excel を希望されたら `scripts/sdlc testitems export` を実行して渡す。
2. 再開したら（Excel なら先に `testitems import`）`scripts/sdlc testitems report` で集計を見る。
3. **NG** があれば TC ごと（同じ原因はまとめて）に不具合を起票し、`/defect` で対応する:
   `scripts/sdlc defect new --title "<現象>" --detected-in 04 --tc TC-xxx`
   仕様そのものを変えたいという指摘なら `/change` にする（人に確認する）。
   **保留**は理由を人に確認する（環境が無い・判断待ちなど）。
4. 未実施・NG・保留が残っている間は、残りを人に伝えて停止する。

## 完了判定
- すべて OK / 対象外になったら `scripts/sdlc testitems report --write` → `scripts/sdlc phase step gate` →
  `scripts/sdlc phase advance`（組み込みの MUST: 結果シートの手動確認がすべて OK・対象外、`commands.test` の成功）。
- `project.yaml` の `gates` に `04-acceptance` があれば、人に最終承認を依頼して停止する。
- 完了したら、`report.md` の要約（確認件数・自動テスト件数・発生した不具合）を人に報告する。
