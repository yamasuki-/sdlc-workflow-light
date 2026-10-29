# 使い方（USAGE）

SDLC ワークフロー（軽量版）本体は、次の 2 通りに置けます。どちらも同じファイル構成で、同じコマンドで使えます。

| 配置 | 置き場所 | 向いている場面 |
|---|---|---|
| **A. ユーザ配置（基本）** | `~/.claude/` | 自分の複数のプロジェクトで共通に使う |
| **B. プロジェクト配置** | `<プロジェクト>/.claude/` | そのプロジェクト単体で使う（チームでリポジトリごと共有する、クラウド環境で使う）／A の内容をそのプロジェクトだけ変える |

A と B を併用すると、**プロジェクトの `.claude/` が `~/.claude/` より優先**されます（後述「上書きの仕組み」）。

Linux・macOS・Windows（Git for Windows の Git Bash を使う）で動きます。Windows 固有の注意は「[9. Windows で使う](#9-windows-で使う)」。
以下のコマンド例は bash の書式です（Windows では Git Bash で実行するか、9 章の PowerShell / コマンドプロンプトの書き方に読み替えてください）。

---

## 1. 前提

- Python 3.10 以上、git、bash（Windows では Git for Windows）
- 本体の依存パッケージ:
  ```bash
  python3 -m pip install -r requirements.txt   # PyYAML, openpyxl, python-docx, python-pptx, pdfplumber
  ```
  hooks と `scripts/sdlc` は、`python3` → `python` → `py -3` の順に、3.10 以上で PyYAML を読み込める Python を探して使います。
  特定の Python を使わせたいときは環境変数 `SDLC_PYTHON` に指定します（例: `SDLC_PYTHON="py -3.12"`）。
  どの Python が使われるかは `scripts/sdlc where` で確認できます。
- PowerPoint の図をスライド画像として読み取りたい場合は LibreOffice（`soffice`）と `pdftoppm`（任意）。
  PDF のページの画像化は pdfplumber（同梱の pypdfium2）で行うため追加のツールは不要です。
- PDF はテキスト層から取り込みます。スキャンした PDF（テキスト層なし）はページ画像から読み取るため、
  可能なら元の Word / Excel / PowerPoint を置いてください（出典の精度が上がります）。パスワード付きの PDF は取り込めません。

---

## 2. A. ユーザ配置（~/.claude）

### インストール

```bash
git clone <このリポジトリ> sdlc-workflow-light
cd sdlc-workflow-light
python3 install.py --user            # 何が置かれるか先に見るなら --dry-run
```

`~/.claude/` に次が置かれ、`~/.claude/settings.json` に hooks と permissions が追記されます（既存の設定は残ります。再実行しても重複しません）。

```
~/.claude/sdlc/            本体（bin・lib・テンプレート・チェックリスト・共通フロー・全体ルール RULES.md）
~/.claude/hooks/sdlc/      ガード（hooks）
~/.claude/skills/          sdlc, sdlc-init, phase-*（4 工程）, defect, change, sdlc-security
~/.claude/agents/          analyst, tester, implementer, reviewer, security-reviewer
```

> 本家の sdlc-workflow と同じ名前（`~/.claude/sdlc/`・`/sdlc` など）を使うため、同じ場所に両方は置けません。
> 本家を入れている場所にインストールすると本家を置き換えます（本家にだけあるファイルは、変更していなければ削除されます）。
> 進行中の本家のプロジェクトがある場合は、そのプロジェクトには本家をプロジェクト配置（B）で残してください。

hooks はすべてのプロジェクトで起動しますが、**`project.yaml` に `workflow: sdlc` があるプロジェクトでだけ**工程を検査します。
それ以外のプロジェクトへの影響は、`~/.claude` の設定ファイルと本体を Claude が編集できないこと、
このインストーラ（`install.py --user` 等）を Claude が実行できないことだけです。

### プロジェクトで使い始める

```bash
cd <プロジェクト>          # git リポジトリであること
claude
> /sdlc-init
```

`/sdlc-init` は次を行います（`scripts/sdlc init` を内部で実行）。

- ランチャ `scripts/sdlc`・`scripts/approve`（本体を呼ぶだけの小さなスクリプト）を作る
- `CLAUDE.md` に全体ルールの import `@~/.claude/sdlc/RULES.md` を追加する
- `project.yaml`（`workflow: sdlc` 付き）を対話で作る。言語・テストフレームワーク・テストコマンド・人間ゲートを置く工程・機械チェック
- `state/`・`docs/<工程>/`・`.gitignore` を用意する

> 初回は、CLAUDE.md が `~/.claude` のファイルを import することへの許可ダイアログが出ることがあります。許可してください。
> import は次のセッションから読み込まれます。

ランチャと `CLAUDE.md`・`project.yaml` はコミットしてください。

---

## 3. B. プロジェクト配置（プロジェクト単体で使う）

### インストール

```bash
cd sdlc-workflow-light
python3 install.py --project /path/to/your-project
```

`/path/to/your-project/.claude/` に A と同じ構成が置かれ、`.claude/settings.json` に
`$CLAUDE_PROJECT_DIR/.claude/hooks/sdlc/...` を呼ぶ hooks が追記されます。
`~/.claude` には何も置きません。

```bash
cd /path/to/your-project
claude
> /sdlc-init
```

`CLAUDE.md` には `@.claude/sdlc/RULES.md` が入ります。`.claude/` 一式をコミットすれば、
リポジトリを取得したチームメンバーは追加のインストールなしで使えます（依存パッケージは各自 `pip install`）。

> プロジェクト配置では、`project.yaml` を作る前から hooks が有効です（工程成果物・本体は最初から保護されます）。

### クラウド環境（Claude Code on the web など）で使う場合

クラウドのセッションはリポジトリを毎回新しく取得し、`~/.claude` は引き継がれません。次のどちらかにします。

- **B. プロジェクト配置**にして `.claude/` をコミットする（推奨）
- 環境のセットアップスクリプトで毎回 A を入れる:
  ```bash
  git clone <このリポジトリ> /tmp/sdlc-workflow-light && pip install -r /tmp/sdlc-workflow-light/requirements.txt \
    && python3 /tmp/sdlc-workflow-light/install.py --user
  ```

---

## 4. 上書きの仕組み（A と B の併用・部分的な上書き）

| 対象 | 既定（A） | プロジェクトで上書き | 仕組み |
|---|---|---|---|
| エージェント | `~/.claude/agents/<名前>.md` | `.claude/agents/<名前>.md` | Claude Code の標準（プロジェクト優先） |
| スキル | `~/.claude/skills/<名前>/` | `.claude/skills/<名前>/SKILL.md` | Claude Code は同名スキルを `~/.claude` 側で解決するため、`~/.claude` 版の冒頭でプロジェクト版の有無を確認し、あればそちらに従う |
| hooks | `~/.claude/hooks/sdlc/` | `.claude/hooks/sdlc/`（B のインストールで入る） | 両方登録されていても、プロジェクトに hooks があれば `~/.claude` 側は何もしない |
| CLI・ライブラリ | `~/.claude/sdlc/bin`・`lib` | `.claude/sdlc/bin`・`lib` | ランチャ `scripts/sdlc`・`scripts/approve` がプロジェクトを優先して呼ぶ（bin と lib は組で上書き） |
| テンプレート・チェックリスト・共通フロー・全体ルール | `~/.claude/sdlc/...` | `.claude/sdlc/...`（**ファイル単位**） | スキル・エージェントは `<SDLC>/…` と書かれたファイルを `scripts/sdlc path <相対パス>` で解決する。プロジェクトにあればそれ、無ければ `~/.claude` のもの |

### よくある上書きの例

- **このプロジェクトだけ実装工程のチェックリストを変える**:
  `~/.claude/sdlc/checklists/03-implementation.md` を `.claude/sdlc/checklists/03-implementation.md` にコピーして編集する。
- **仕様書のテンプレートを社内様式にする**: `.claude/sdlc/templates/spec.md` を置く。
- **あるスキルの手順を変える**: `~/.claude/skills/<名前>/` を `.claude/skills/<名前>/` にコピーして編集する。
- **このプロジェクトだけ本体を固定のバージョンにする**: `python3 install.py --project <dir>`（B を併用）。

上書きの状況は次で確認できます。

```bash
scripts/sdlc where                         # 配置（project / user）と、~/.claude を上書きしているファイルの一覧
scripts/sdlc path checklists/03-implementation.md   # 実際に使われるファイル
```

> 上書きファイルは本体の一部として保護されます（SDLC プロジェクトでは Claude が編集できません）。人が編集するか、
> `SDLC_MAINTENANCE=1` で起動したセッションで編集してください。

### 上書きより先に検討すること: `rules/`

言語・フレームワーク・社内規約など**プロジェクト固有の内容は、本体を上書きせず `rules/` に書く**のが基本です
（雛形は `scripts/sdlc path templates/rules/common.md` など）。

| ファイル | 内容 |
|---|---|
| `rules/common.md` | 技術スタック・コーディング規約・テストの作法など（全工程のエージェントが読む） |
| `rules/<工程ID>.md` | その工程の追加ルール（ADD / OVERRIDE / DISABLE / 追加成果物） |
| `rules/review-<工程ID>.md` | その工程の追加レビュー観点。`/defect` の再発防止で追加される観点もここに入る |

---

## 5. 日々の使い方

```
input/ に要求ドキュメント（xlsx / docx / pptx / pdf / md）を置く
> /sdlc                  状態を読んで次の工程を実行する（中断しても続きから再開）
```

```
01 要件・仕様 ──[人間ゲート]──> 02 設計 ──> 03 実装 ──> 04 受入確認（人がテスト項目を確認）──> 完了
```

### 01 要件・仕様を承認する（人間ゲート）

Claude が要求・質問・振る舞い仕様（SPEC）・テスト項目（TC）を作り、承認待ちで停止します。
答えで仕様が大きく変わる質問は、途中で Claude から聞かれます。`docs/01-specification/` を読み、端末で承認します。

```bash
scripts/approve 01                 # 承認 / 条件付き承認 / 差戻し を対話で記録（承認時に機械チェックを再実行）
git add state/gates && git commit -m "gate: 01-specification"
```

見るポイント: 仕様（SPEC）が意図どおりの振る舞いか、エラー時の振る舞いが妥当か、
テスト項目（TC）の「確認ポイント」「期待結果」で OK と判断できるか、手動確認（種別「手動」「両方」）の量が妥当か。

### 02 設計・03 実装（既定では人の承認なし）

Claude が設計・実装・結合テストを作り、機械チェック（テスト全件成功・自動 TC のテストコード）と AI レビューに合格したら次へ進みます。
人が承認したい工程は `project.yaml` に追加します:

```yaml
gates: [01-specification, 02-design]     # 01 は常に対象。02-design / 03-implementation / 04-acceptance を追加できる
```

### 04 受入確認（人がテスト項目を確認する）

Claude が結果シート `docs/04-acceptance/results.md` を用意し、確認を依頼して停止します。
TC（`docs/01-specification/test-items-*.md`）と手動確認の補足（`docs/03-implementation/test-notes.md`）を見ながら確認し、
「結果」列に **OK / NG / 保留 / 対象外** と確認者・日付・メモを記入します（NG はメモに現象、対象外は理由）。

```markdown
| TC | タイトル | 種別 | 結果 | 確認者 | 日付 | メモ |
|---|---|---|---|---|---|---|
| TC-001 | 和が表示される | 手動 | OK | 山田 | 2026-10-29 | |
| TC-003 | 応答時間 | 両方 | NG | 山田 | 2026-10-29 | 2 秒かかる |
```

Excel で記入したい場合（任意）:

```bash
scripts/sdlc testitems export                                   # docs/04-acceptance/results.xlsx を出力（黄色の列に記入）
scripts/sdlc testitems import docs/04-acceptance/results.xlsx   # 記入した結果を results.md に取り込む
```

記入したら `/sdlc` を実行します。NG があれば Claude が不具合を起票して `/defect` で直し、該当 TC を未実施に戻して再確認を依頼します。
すべて OK（または対象外）になれば完了です。確認状況は `scripts/sdlc testitems report` で見られます。

> 結果シートは Claude が書き込めません（hook で拒否）。結果は人が記入してください。

### 割り込み

| やりたいこと | 方法 |
|---|---|
| 仕様どおりに動いていない | `/defect`（再現 → 原因特定 → 設計か実装からやり直し → 自動テスト追加 → 該当 TC を再確認） |
| 仕様を変えたい・機能を足したい | `/change`（SPEC/TC の差分を作る → `scripts/approve 01` で再承認 → 差分でやり直し → 追加・変更した TC を確認） |
| セキュリティを確認したい | `/sdlc-security`（下記） |
| 状態を見る | `scripts/sdlc status` |
| 未解決事項・決定事項を見る | `scripts/sdlc question list` / `scripts/sdlc decision list` |
| コマンドの一覧 | `scripts/sdlc -h` |

### セキュリティレビュー（随時）

セキュリティの専門レビューは工程に組み込まれていません。必要なとき（実装の後・リリース前・定期的に）に実行します。
工程の状態や完了判定には影響しないので、どの時点でも実行できます。

```
> /sdlc-security                    前回のレビュー以降の差分（初回は全体）を提案して実施
> /sdlc-security all                全体
> /sdlc-security since v1.0.0       指定したコミット・タグからの差分
> /sdlc-security src/auth           指定したパス
```

1. `project.yaml` の `security.tools` のツールを実行します（任意。例: 依存脆弱性スキャン・SAST・シークレットスキャン）:
   ```yaml
   security:
     tools: ["pip-audit", {name: semgrep, cmd: "semgrep --config auto --error src"}, "gitleaks detect --no-banner"]
   ```
2. security-reviewer がチェックリスト（OWASP Top 10・入力検証・秘密情報・ビジネスロジック・DoS・LLM 機能・依存・インフラ・NFR）で
   レビューし、`docs/security/security-review-<日付>.md` に報告します（対象コミットも記録）。
3. 所見ごとに、不具合として起票する（Critical / High は推奨）・受容する・後で対応する、を選びます。
   起票した所見は `/defect` で直します。過去の報告は `scripts/sdlc security list` で見られます。

---

## 6. 更新・アンインストール

```bash
cd sdlc-workflow-light && git pull
python3 install.py --user                     # A を更新（本体を置き換える。プロジェクト側のファイルは変えない）
python3 install.py --project <dir>            # B を更新
python3 install.py --user --uninstall         # A を取り除く（settings.json の SDLC の hooks も外す）
python3 install.py --project <dir> --uninstall
```

インストーラは置いたファイルを `sdlc/.install-manifest.json` に記録し、1 ファイルずつ更新します。
**インストール後に変更したファイルと、インストーラが置いていないファイル（プロジェクトで追加した上書きファイルなど）は、
変更・削除せずにそのまま残し、一覧を表示します**（置き換えるなら `--force`）。

プロジェクトで `~/.claude` 版を上書きしているファイルは、A を更新しても自動では追従しません。
`scripts/sdlc where` で一覧を確認し、必要なら取り込み直してください。

---

## 7. ワークフロー本体を変更する（メンテナンスモード）

本体・設定ファイル・ランチャは、ゲートの強制機構を守るため Claude が編集できません。本体を直す方法は 2 つあります。

### 方法 1: メンテナンスモードでセッションを開始する（基本）

```bash
SDLC_MAINTENANCE=1 claude
```

クラウド環境では、環境の設定で環境変数 `SDLC_MAINTENANCE=1` を追加してから**新しいセッション**を開始します
（環境変数はセッション開始時に読み込まれるため、実行中のセッションでは切り替わりません。
`.claude/settings.local.json` や `~/.claude/settings.json` の `env` に書く方法は、Claude が自分で保護を外せないよう hooks で禁止しています）。
このモードでは Claude が Write / Edit ツールで本体を直接編集できます。作業が終わったら外してください。
`state/gates/` はこのモードでも書き込めません。

### 方法 2: 人の指示のもと、適用のコマンドにだけ指定する

環境変数を変えずに、実行中のセッションで本体を更新する方法です。**人が明示的に指示したときだけ**使います。

1. Claude は本体の変更を、リポジトリの外の作業コピーで実装し、自己テストを通す（リポジトリ内の本体は書き換えない）。
2. 変更を 1 つのパッチと適用スクリプトにまとめ、人に内容を示す。
3. 人の指示を受けて、適用スクリプトを 1 回の Bash 呼び出しとして、そのコマンドにだけ指定して実行する:
   ```bash
   SDLC_MAINTENANCE=1 bash <適用スクリプト>     # パッチ適用 → 自己テスト → コミット
   ```

> **この方法が通る理由と限界**: コマンドの先頭に付けた環境変数は hooks には渡らず、hooks の判定はメンテナンスモードに
> なりません。通るのは、Bash ガードがコマンドの文字列だけを見るため、スクリプトの中で行う書き換えまでは検出しないからです。
> つまり Claude が自分の判断で同じことをすれば保護をすり抜けられます。保護の実効性は、Claude がこの手順を人の指示なしに
> 使わないこと（`RULES.md` の絶対ルール）と、ゲート記録・成果物ハッシュ・git の履歴による事後の検知に依存します。
> より強く守りたい場合は方法 1 だけを使い、変更は人がレビューしてからコミットしてください。

このソースリポジトリでの開発も同じです（ソースリポジトリ自体がプロジェクト配置になっています）。
変更後は自己テスト `python3 -m unittest discover -s tests` を通し、`python3 install.py ...` で配置し直します。
Windows / macOS / Linux での自己テストは GitHub Actions（`.github/workflows/tests.yml`）でも実行されます。

---

## 8. トラブルシュート

| 症状 | 確認すること |
|---|---|
| `/sdlc` などのスキルが出てこない | A: `~/.claude/skills/` に、B: `.claude/skills/` に置かれているか。Claude Code を再起動する |
| hooks が効いていない | `/hooks` で SDLC の hooks（`hooks/sdlc/guard_*.py`）が登録されているか。A では `project.yaml` に `workflow: sdlc` があるか |
| 結果シートを Claude が直せない | 仕様です（結果は人が記入する）。TC の追加・削除の反映は `scripts/sdlc testitems sheet`、再確認は `testitems reset` |
| 03 を完了できない（自動テストなし） | 種別「自動」「両方」の TC に、テストコードの `trace: TC-xxx` があるか（`scripts/sdlc trace check`） |
| すべての書き込みが「ガードの内部エラー」で拒否される | hooks が使う Python（`scripts/sdlc where` で表示）に `requirements.txt` の依存が入っているか |
| 「Python 3.10 以上が見つからない」で拒否される | Python 3.10 以上が PATH にあるか。`SDLC_PYTHON` を設定した場合はその値が正しいか（設定するとそれだけを使う） |
| hooks が実行できず、すべての操作が拒否される | hooks は `onFailure: block` で登録されている（hooks が動かないときに素通りさせないため）。bash（Windows では Git Bash）と Python があるか確認する |
| `SDLC ワークフロー本体が見つかりません` | A なら `~/.claude/sdlc/bin/sdlc`、B なら `.claude/sdlc/bin/sdlc` があるか（`install.py` を実行したか） |
| 全体ルール（RULES.md）が読み込まれていない | `CLAUDE.md` の import 行（`@~/.claude/sdlc/RULES.md` か `@.claude/sdlc/RULES.md`）と、外部 import の許可。`scripts/sdlc init` を再実行すると配置に合わせて直る |
| A と B のどちらが使われているか分からない | `scripts/sdlc where` |

---

## 9. Windows で使う

### 前提

| 必要なもの | 確認・補足 |
|---|---|
| Git for Windows（Git Bash） | Claude Code の Bash ツールと、このワークフローの hooks は Git Bash で動きます。Claude Code が Git Bash を見つけられない場合は `CLAUDE_CODE_GIT_BASH_PATH` を設定します（Claude Code の設定）。**WSL の bash では動きません** |
| Python 3.10 以上 | python.org のインストーラ（`py` ランチャ付き）を推奨。Microsoft Store の `python3` エイリアスだけでは動きません（自動で除外します） |
| 依存パッケージ | PowerShell で `py -3 -m pip install -r requirements.txt`（hooks が使う Python に入れる。`scripts/sdlc where` で確認） |

### インストール（PowerShell / コマンドプロンプト）

```powershell
git clone <このリポジトリ> sdlc-workflow-light
cd sdlc-workflow-light
py -3 install.py --user                       # ~/.claude（C:\Users\<名前>\.claude）に配置
py -3 install.py --project C:\work\my-app      # プロジェクト配置の場合
```

`~/.claude/settings.json` の hooks は `bash "C:/Users/<名前>/.claude/hooks/sdlc/run" guard_write.py` の形で登録され、
Git Bash から実行されます。

### Claude Code の中（Bash ツールと PowerShell ツール）

Windows の Claude Code は、Git Bash があっても既定で PowerShell ツールを使ってコマンドを実行します。

- ガード（`guard_bash.py`）は **Bash ツールと PowerShell ツールの両方**を検査します（`Set-Content`・`Out-File`・`Remove-Item`・
  `Copy-Item`・`>` などの書き込み、`approve` の呼び出し、`\` 区切りのパスも検出）。
- スキル・ルールは bash の書式でコマンドを書いているため、**Bash ツールを使う設定を推奨**します。
  - プロジェクト配置（B）では、インストーラが `.claude/settings.json` に `"CLAUDE_CODE_USE_POWERSHELL_TOOL": "0"` を入れます。
  - ユーザ配置（A）では、必要に応じて人が `~/.claude/settings.json` の `env` に同じ設定を追加してください
    （このファイルは Claude からは編集できません）。
- PowerShell ツールで実行する場合、ランチャは `scripts\sdlc.cmd status` のように呼びます。

### 人が使うコマンド

| 用途 | PowerShell / コマンドプロンプト | Git Bash |
|---|---|---|
| 承認 | `.\scripts\approve.cmd 01` | `winpty bash scripts/approve 01`（mintty では TTY と判定されないため `winpty` が必要） |
| 状態の確認 | `.\scripts\sdlc.cmd status` | `scripts/sdlc status` |

承認スクリプトは、対話端末（TTY）以外から、または Claude Code から起動されたプロセス（環境変数 `CLAUDECODE` がある）からは
実行できません。Windows Terminal / PowerShell / コマンドプロンプトの画面で人が実行してください。

### 改行コード

- `scripts/sdlc init` はプロジェクトの `.gitattributes` に、ランチャと本体の bash スクリプトを LF に固定する設定を追加します
  （`core.autocrlf` で CRLF になると bash で動かないため）。ソースリポジトリにも同様の `.gitattributes` があります。
- ゲートの成果物ハッシュは、テキストファイルの CRLF / LF の違いを無視して計算します。Windows と Linux / macOS の
  メンバーが混在しても、改行の変換だけでゲートが無効になることはありません。

### 取り込み（PowerPoint の図）

スライドの画像化に使う LibreOffice（`soffice`）と `pdftoppm`（Poppler）は任意です。Windows では PATH に通っていなければ
図は「要画像読取（画像化できず）」として残り、人が画像を用意するか質問リストに回します。

### Windows での既知の制約

- WSL の bash は使えません（Windows のパスを扱えないため）。WSL 内で Claude Code を動かす場合は Linux として扱います。
- テストを `src_dir` の中に置く言語慣習は、他の OS と同様に使えません。
