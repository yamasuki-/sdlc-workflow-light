---
name: change
description: 変更要求フロー（割り込み）。承認済みの要件・仕様を変えたい・機能を足したいときに使う。起票→現行の振る舞いの確認→start（01 の承認を再承認要にする）→SPEC/TC を変更→人が 01 を再承認（唯一の人間ゲート）→設計・実装を差分でやり直し→変更した TC を人が確認→クローズ。input/ の要求ドキュメントが改訂されたときもこれを使う。
argument-hint: "[CR-ID | 変更内容の説明]"
---

# /change — 変更要求フロー

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/change/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

```
起票 → 現行の確認 → start → 01 の SPEC/TC を変更 → ★人が 01 を再承認 → 02・03 を差分でやり直し → 戻り先へ → 人が TC を確認 → close
```

変更の合意は **01 の再承認**（`scripts/approve 01`）で行う。変更要求のための別の承認は無い。

## 0. 状況把握
`scripts/sdlc status` と `scripts/sdlc change list` を実行する。引数が CR-ID ならその票を、説明文なら新規起票から始める。

| 票の status / 状態 | 再開位置 |
|---|---|
| 起票 | 1 または 2 |
| 対応中 | 3 以降（`/sdlc` の action に従う。`item_close` なら 5） |

## 1. 起票
```
scripts/sdlc change new --title "<変更の要約>"
```
票（`state/changes/CR-xxx.md`、Edit 可）の「変更内容」に依頼者の言葉で書く。曖昧なら AskUserQuestion で確認する。

## 2. 現行の確認
- **analyst** エージェントに、関連する SPEC / TC と、コードの実際の振る舞いを調べさせる（修正はさせない）。
  依頼者の認識とコードの実態が食い違えば票に明記し、人に確認する。
- 票の「変更後の振る舞い（SPEC / TC の差分）」に、変更・追加・削除する SPEC / TC を表で書く。
  影響範囲は `scripts/sdlc trace impact <SPEC-xxx ...>` で確かめ、「影響範囲」に書く。
- 再確認が必要な既存の TC を票の `retest` に書く（新しく追加する TC は結果シートに未実施で自動的に入る）。

## 3. やり直し開始・仕様の変更
```
scripts/sdlc change start CR-xxx [--from 01]
```
- 01 の人間ゲートが「再承認要」になり、01 の成果物を変更できるようになる（02 以降は 01 の再承認まで止まる）。
  `--from 02` は振る舞いを変えない変更（性能改善など）だけに使う。
- `/sdlc` の指示どおり `/phase-specification` を実行し、票の差分どおりに SPEC / TC（要求ドキュメントが改訂されたなら REQ も）を変更する。
  レビューの観点にチェックリスト `change.md` を加える。
- 人に 01 の再承認を依頼して停止する。提示には**票の差分表**を必ず含める（何が変わるかを人が一目で分かるように）。

## 4. 設計・実装の差分やり直し
- 再承認後は `/sdlc` の指示どおり 02・03 を進める（共通フローの「差分やり直し」。影響範囲だけを変更し、変更後の振る舞いの自動テストを追加・更新する）。

## 5. 確認・クローズ
- 戻り先が 04 受入確認なら、`scripts/sdlc testitems sheet` → `scripts/sdlc testitems reset --item CR-xxx` で
  追加・再確認の TC を未実施にし、人に確認を依頼して停止する。
- `scripts/sdlc change close CR-xxx`（自動テストの全件成功と、`retest` の TC が OK であることを確認して閉じる）。
  新しく追加した TC は、04 の完了判定で OK が求められる。
