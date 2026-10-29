---
name: defect
description: 不具合対応フロー（割り込み）。承認した仕様どおりに動いていない（受入確認の NG・自動テストの失敗・人の報告）ときに使う。起票→再現→原因特定（エビデンス必須）→設計か実装からやり直し→自動テスト追加→該当 TC を人が再確認→クローズ。仕様そのものを変える場合は /change を使う。
argument-hint: "[DEF-ID | 不具合の説明]"
---

# /defect — 不具合対応フロー

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/defect/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

```
起票 → 再現 → 原因特定 → start（02 か 03 から）→ 修正＋自動テスト追加 → 工程を進めて戻り先へ → 人が TC を再確認 → close
```

軽量版では不具合対応に人の承認は要らない（ただし `project.yaml` で人間ゲートを追加した工程をやり直す場合は、その再承認が要る）。

## 0. 状況把握
`scripts/sdlc status` と `scripts/sdlc defect list` を実行する。引数が DEF-ID ならその票を、説明文なら新規起票から始める。

| 票の status / 状態 | 再開位置 |
|---|---|
| 起票 | 1 または 2 |
| 対応中（`/sdlc` の action が `run_phase`） | 3（`/sdlc` の指示どおり工程スキルを実行） |
| 対応中（action が `item_close`） | 4 |

## 1. 起票・再現
```
scripts/sdlc defect new --title "<現象の要約>" [--detected-in <工程>] [--severity 致命|高|中|低] [--tc TC-xxx ...]
```
- 受入確認の NG なら `--tc` に NG の TC を指定する（再確認の対象 `retest` になる）。
- 票（`state/defects/DEF-xxx.md`、Edit 可）の「現象」「再現手順」を書き、実際に再現させる（コマンド・ログを残す）。

## 2. 原因特定
- **implementer** エージェントに調査を依頼する（修正はまださせない）。渡すもの: 票のパス、関連する SPEC / TC、`<SDLC>/checklists/defect.md`。
- 調査は**エビデンス必須・推測禁止**。原因はファイル:行の粒度で票の「原因」に書く。関係範囲は `scripts/sdlc trace impact <ID...>`。
- 原因で分ける:
  - 設計の誤り → やり直しは 02 から / 実装の誤り → 03 から
  - **承認した仕様そのものが誤り・不足**（仕様どおりに作ると問題がある）→ 不具合ではなく変更。人に確認して `/change` に切り替える
    （票は `scripts/sdlc defect` で閉じずに、経緯に「CR-xxx に移行」と書いて status を クローズ にしてよい）。
- 再確認が必要な TC を票の `retest` に追記する（NG の TC に加え、同じ箇所を通る TC）。

## 3. やり直し
```
scripts/sdlc defect start DEF-xxx --from 02|03
```
- 現在工程を戻り先として記録し、`--from` の工程から進め直す。`retest` の TC は結果シートで未実施に戻る。
- `/sdlc` の指示どおり工程スキルを実行する（共通フローの「差分やり直し」を適用）。必ず:
  - 同じ誤りを検出する**自動テスト**を追加する（結合テスト。ロジックの誤りなら単体テスト）。修正前に失敗することを確かめる
  - 修正は原因の範囲に収める
- 工程の完了は通常どおり `scripts/sdlc phase advance`（機械チェック＋レビュー）。戻り先の工程まで進める。

## 4. 再確認・クローズ
- 戻り先が 04 受入確認なら、`scripts/sdlc testitems sheet` で結果シートを最新にし、`retest` の TC の再確認を人に依頼して停止する
  （`phase-acceptance` の依頼文を使い、対象 TC を明示する）。
- `scripts/sdlc defect close DEF-xxx`（自動テストの全件成功と、`retest` の TC が OK であることを確認して閉じる）。
- 同種の不具合を防ぐ観点があれば `rules/review-<工程ID>.md` に追記する。
