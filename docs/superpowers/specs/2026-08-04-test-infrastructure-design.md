# replacement_tool テスト基盤 設計ドキュメント

- 日付: 2026-08-04
- 対象リポジトリ: `meta-BE/replacement_tool`
- 作業ブランチ: `test-infrastructure`
- 前提となる既存設計: `docs/superpowers/specs/2026-08-02-release-pipeline-design.md`

## 1. 目的

`replacement_tool` に自動テストと再現可能な開発環境を導入する。現状リグレッション検知の
手段が「手元で GUI を起動して目視」しかなく、CI もタグ push 時にしか動かないため、
壊れていることに気づくのがリリース後になる構造を解消する。

あわせて、テストの前提として GUI とロジックの分離、`uv` ベースの仮想環境、
pyright による型チェック環境を整備する。

## 2. 現状と課題（調査結果）

いずれも 2026-08-04 時点の実測。

- テストコードは 0 件。`pytest.ini` / `pyproject.toml` / `tox.ini` / `setup.cfg` いずれも不在。
- `.github/workflows/build-windows.yml:3-7` のトリガは `push: tags: ['v*']` のみ。
  ジョブは exe ビルド → zip → Release 添付だけで、テスト実行ステップが無い。
- `Makefile` のターゲットは `build` / `release-*` のみ。
- テスト用の `.bms` / `.bml` / `.bme` がリポジトリに 1 件も無い。
- **`import replacement_tool` が失敗する**。2 段で詰まる:
  1. `replacement_tool.py:4` の `import tkinter` — homebrew python 3.14.6 に `_tkinter` が無い
  2. 仮に 1 を通しても `replacement_tool.py:9-13` で `tkinterdnd2` 不在時に `exit(1)`。
     これは `SystemExit` なので pytest の収集フェーズごと落ちる
- GUI がロジック層に混入している箇所:
  - `save_file()` が上書き確認で `messagebox.askyesno` を直接呼ぶ（`replacement_tool.py:207`）
  - `run_main()` が `tk._default_root.entries` から値を取る（`replacement_tool.py:108`）ため、
    バリデーション（`:119-142`）を単体で呼べない
- 一方、`collect_bgm_lane` / `collect_key_lanes` / `replace_notes` / `update_content` /
  `process_bars` / `process_single_bar`（`:218-325`）は「文字列リスト in → 文字列リスト out」の
  純関数で、GUI にもファイルシステムにも触っていない。**必要なのは大規模な再設計ではなく、
  import 経路から GUI を外すこと**。
- 環境: `uv 0.11.26` が利用可能。`pyenv` / `mise` / `.python-version` は未使用。
  `pyright` / `pyright-langserver` はどこにも未インストール。

## 3. 制約・前提

- CI のビルドは Python **3.13** 固定（`build-windows.yml:19`）。ローカルもこれに合わせる。
- BMS ファイルの入出力は **Shift-JIS**。テストの fixture もこれに従う。
- 配布物は Windows exe のみ。PyInstaller はクロスコンパイル不可のため、
  Windows ビルドの検証は CI 経由でしか行えない。
- PyInstaller のエントリポイント名 `replacement_tool.py` は変更しない
  （`Makefile` と `build-windows.yml` の両方が依存している）。
- 無音ノーツ定義は大文字・小文字を区別する（62 進拡張のため）。
- すべての出力・コミットメッセージは日本語。

## 4. 決定事項（ユーザー承認済み）

1. **Python 環境**: `uv` + プロジェクト直下 `.venv`、Python 3.13 に統一（CI と一致）。
2. **分離範囲**: 2 ファイル分割。純ロジックを `bms_core.py` へ抜き出し、
   `replacement_tool.py` は GUI 専用エントリにする。`src/` 配下へのパッケージ化はしない（YAGNI）。
3. **GUI テスト**: ウィジェット駆動の自動テストは作らない。代わりに GUI 層に残っていた
   実ロジック（ドロップパス解析・バリデーション）を抜き出してテストし、レーン表は
   辞書化して GUI 選択肢をそこから導出することで不整合を構造的に除去する。
   GUI 本体の確認は手動スモークとする。
4. **改行コード**: 入力の改行をそのまま保持するよう修正する（振る舞い変更を含む）。
5. **既存バグ**: 今回は修正しない。`TODO.md` をリポジトリルートに作成して記録する。
   xfail テストは書かない（記録先を一本化するため）。
6. **ビルド検証**: `build-windows.yml` に `workflow_dispatch` を追加し、リファクタ後に
   手動実行して 1 回確認する。常時のビルド CI は追加しない。

## 5. コンポーネント設計

### 5.1 ファイル構成

```
replacement_tool/
├── bms_core.py                    ★新規 純ロジック（tkinter 非依存・テスト対象）
├── replacement_tool.py               GUI エントリ（PyInstaller 入口・名前不変）
├── pyproject.toml                 ★新規 依存 / pytest / pyright 設定
├── TODO.md                        ★新規 既知バグの記録
├── .gitattributes                 ★新規 fixture のバイト保持
├── .gitignore                        .venv/ を追加
├── Makefile                          test / typecheck / golden ターゲット追加、build を uv run 経由へ
├── tests/                         ★新規
│   ├── test_replace_notes.py
│   ├── test_collect_lanes.py
│   ├── test_validation.py
│   ├── test_io.py
│   ├── test_golden.py
│   ├── regenerate_golden.py
│   └── fixtures/
│       ├── input/*.bms
│       └── expected/*.bms
└── .github/workflows/
    ├── test.yml                   ★新規 push / pull_request で pytest
    └── build-windows.yml             workflow_dispatch 追加
```

### 5.2 `bms_core.py`

既存の関数名は極力そのまま維持し、リファクタを「純粋な移動」に保つ。

| シンボル | 出自 | 変更点 |
|---|---|---|
| `LANE_ORDER_OPTIONS` / `SIDE_ORDER_OPTIONS` | `create_gui:48-54` | 定義をここへ集約 |
| `KEY_LANE_TABLE` | `collect_key_lanes:232-249` の 8 分岐 | `dict[tuple[str, str], list[str]]` へ。キーは `(lane_order, side_order)` |
| `validate_params()` | `run_main:119-142` を抽出 | 新規関数 |
| `parse_dropped_path()` | `drop_file:101-102` を抽出 | 新規関数 |
| `load_file()` | 同名 | `newline=''` で開く |
| `save_file()` | 同名 | `messagebox` をコールバック引数へ置換。未使用引数 `replace_count` を削除 |
| `update_content()` | 同名 | `'\n'` 直付けをやめ、元の行末を引き継ぐ |
| `run_replacement()` | 現 `main()` | 改名（ライブラリ側に `main` があると紛らわしいため）と、`save_file` 呼び出しの引数変更（`replace_count` → `on_conflict`）のみ。処理の流れは同一 |
| `process_bars` / `process_single_bar` / `collect_bgm_lane` / `collect_key_lanes` / `replace_notes` | 同名 | ロジック変更なし |

#### 5.2.1 レーン表の辞書化

```python
LANE_ORDER_OPTIONS = [
    "1234567（左側レーンから順に置換）",
    "7654321（右側レーンから順に置換）",
    "4352617（中央レーンから順に置換１）",
    "4536271（中央レーンから順に置換２）",
]
SIDE_ORDER_OPTIONS = ["左レーン→右レーン", "右レーン→左レーン"]

# GUI の選択肢文字列をそのままキーにする。GUI 側は本テーブルから選択肢を導出するため、
# 文字列を書き換えても両者がズレない。
KEY_LANE_TABLE: dict[tuple[str, str], list[str]] = { ... }
```

`collect_key_lanes` は `KEY_LANE_TABLE[(lane_order, side_order)]` を引くだけになる。
現行は 8 分岐のどれにも当たらない場合 `key_lanes` が未定義のまま
`replacement_tool.py:251` に到達して `UnboundLocalError` になるが、辞書化後は
`KeyError` になる。GUI 経由では到達しない経路であり、どちらもクラッシュだが、
`KeyError` の方が原因が読める。

各値の内容（14 チャンネル、`16`/`17`/`26`/`27` を含まない）は現行から一切変えない。

#### 5.2.2 バリデーションの抽出

```python
def validate_params(file_path, max_bgmlanenumber, no_sound_objnumber, start, end) -> tuple[int, int, int]:
    """GUI から受け取った文字列を検証し、(max_bgmlanenumber, start, end) を int で返す。"""
```

検証内容と例外メッセージは `run_main:119-142` から一字一句変えない
（未入力 / 非数値 / 0〜999 の範囲外 / 無音ノーツの形式 / `"00"` の禁止 / `start >= end`）。
すべて `ValueError` を送出する。

#### 5.2.3 上書き確認の注入

```python
def save_file(content_replaced, file_path, on_conflict=None):
    output_path = os.path.splitext(file_path)[0] + "_replaced" + os.path.splitext(file_path)[1]
    if os.path.exists(output_path):
        if on_conflict is None or not on_conflict(output_path):
            raise Exception("ファイルの上書きがキャンセルされました")
    ...
```

GUI 側は `on_conflict=lambda p: messagebox.askyesno(...)` を渡す。
例外の型（素の `Exception`）とメッセージは現行を維持する。
`on_conflict=None` は「上書きしない」を意味し、テストの既定値になる。

### 5.3 `replacement_tool.py`（GUI エントリ）

残るのは `create_gui` / `browse_file` / `drop_file` / `run_main` / `if __name__` ブロックのみ。
`tkinter` と `tkinterdnd2` の import は**このファイルにのみ存在する**。

`run_main` は次の結線だけになる:

1. Entry から文字列を集める
2. `bms_core.validate_params(...)` を呼ぶ
3. `bms_core.run_replacement(..., on_conflict=lambda p: messagebox.askyesno(...))` を呼ぶ
4. 結果／例外を `messagebox` で表示する

`create_gui` の OptionMenu は `bms_core.LANE_ORDER_OPTIONS` / `SIDE_ORDER_OPTIONS` を参照する。
`drop_file` は `bms_core.parse_dropped_path(event.data)` を呼ぶだけになる。

### 5.4 `pyproject.toml`

```toml
[project]
name = "replacement-tool"
version = "0"
requires-python = ">=3.13"
dependencies = []                       # ロジックは標準ライブラリのみ

[project.optional-dependencies]
gui = ["tkinterdnd2"]                   # GUI 実行と make build のときだけ必要

[dependency-groups]
dev = ["pytest"]

[tool.uv]
package = false                         # 単一スクリプト構成のまま。ビルド対象にしない

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.pyright]
venvPath = "."
venv = ".venv"
```

GUI 依存を extra に切り出したのは、**CI のテストジョブが tkinter を一切必要としない**
ようにするため。ローカルは `uv sync --extra gui` で GUI 実行とビルドもできる状態にする。

### 5.5 開発環境セットアップ

```bash
uv python install 3.13        # CI と同じ版
uv sync --extra gui           # .venv を作成
uv tool install pyright       # pyright-langserver を PATH に配置
```

`pyright` を `.venv` 内ではなく `uv tool`（global tool）として入れるのは、Claude Code の
LSP 機能が PATH 上の `pyright-langserver` を直接起動するため。venv が activate されている
とは限らない。プロジェクトの `.venv` は `[tool.pyright]` の `venvPath` / `venv` 経由で解決させる。

**未検証の前提**: uv 配布の Python 3.13（python-build-standalone）に tkinter が
同梱されているかを未確認。同梱されていれば `make build` がローカルで復活する。
無い場合は `brew install python-tk` 系のフォールバックが必要。
いずれにせよ**テストには影響しない**（`bms_core` は tkinter 不要）。実装の最初に検証する。

### 5.6 `Makefile` 追加ターゲット

```make
.venv: pyproject.toml
	uv sync --extra gui

test: .venv
	uv run pytest

typecheck: .venv
	pyright

golden: .venv
	uv run python tests/regenerate_golden.py

build: .venv _gen-version
	uv run pyinstaller --onefile --collect-all tkinterdnd2 --name "無音ノーツ自動置換ツール" replacement_tool.py
```

`VERSION` の算出ロジックと `release-*` ターゲットは変更しない。

### 5.7 `.gitignore` / `.gitattributes`

`.gitignore` に `.venv/` を追加する。

`.gitattributes`（新規）:

```
tests/fixtures/**/*.bms -text
```

git の改行正規化で golden ファイルが壊れるのを防ぐ。golden はバイト単位で比較するため、
これが無いと CRLF の fixture が環境によって壊れる。

## 6. テスト設計

2 層構成にする。純関数のユニットテストを主軸に置き、実ファイルを通す golden テストを
薄く重ねる。ユニットテストだけではファイル全体の性質（非対象チャンネルの素通し、行数、
文字コード往復）を守れず、golden テストだけでは分解能の組み合わせを網羅できず
失敗時の原因も特定できないため、両方が必要になる。

### 6.1 ユニットテスト

| ファイル | 対象 | ケース |
|---|---|---|
| `test_replace_notes.py` | `replace_notes` | 同分解能・同位置での置換 / 分解能違い（キー 4 分割の位置 1 ↔ BGM 8 分割の位置 2）/ 位置 0 同士（`gcd(0, n) = n` を通る経路）/ 消費済み BGM ノーツが再利用されないこと / 無音ノーツ以外を触らないこと / 対応する BGM が無ければ無音ノーツが残ること / `replace_count` の値 / 奇数長データ部で例外 |
| `test_collect_lanes.py` | `collect_bgm_lane`, `collect_key_lanes`, `KEY_LANE_TABLE` | 同一小節の複数 `#XXX01` を統合せず個別に収集すること / `max_bgmlanenumber` による打ち切り / 8 通りすべてが 14 チャンネルを返し `16`,`17`,`26`,`27` を含まないこと / **`LANE_ORDER_OPTIONS` × `SIDE_ORDER_OPTIONS` の全組合せが `KEY_LANE_TABLE` のキーとして解決すること** |
| `test_validation.py` | `validate_params`, `parse_dropped_path` | 未入力 / 非数値 / 範囲外（`-1`, `1000`）/ 無音ノーツの形式不正 / `"00"` / `start >= end` の各メッセージ / 正常系で int を返すこと / ドロップパスの単一・`{...}` 付き・複数ファイル |
| `test_io.py` | `load_file`, `save_file` | Shift-JIS の往復 / CRLF・LF の保持 / 最終行に改行が無いファイル / 出力パスが同階層の `_replaced` 付きになること / 既存ファイルに対し `on_conflict=None` で例外・`lambda _: True` で上書き |

### 6.2 golden テスト（`test_golden.py`）

手順:

1. fixture を `tmp_path` へコピーする（`save_file` が入力と同階層へ書くため）
2. `bms_core.run_replacement(...)` を実行する
3. 生成された `_replaced` ファイルを expected と**バイト単位で比較**する（`open(..., 'rb')`）

バイト比較にすることで、文字コード・改行・行数・非対象チャンネルの保持を
1 つの assert で同時に守れる。

各ケースのパラメータ（`max_bgmlanenumber` / 無音ノーツ定義 / `start` / `end` /
`lane_order` / `side_order`）はテスト側のテーブルに持ち、`pytest.mark.parametrize` で回す。

### 6.3 fixture

| fixture | 狙い | 形式 |
|---|---|---|
| `basic_7k` | 1P 7 鍵の基本動作（BGM 3 レーン、無音ノーツ `ZZ`） | ASCII / LF |
| `resolution_mix` | キー 16 分割 × BGM 12 分割など、既約分数によるタイミング一致 | ASCII / LF |
| `passthrough` | `02`, `03`, `08`, `09`, `16`, `17`, `3x`, `5x`, `Dx` を同居させ、**1 バイトも変わらない**こと | ASCII / LF |
| `14k` | 2P 側レーンの使用。`side_order` 両方向で 2 ケース | ASCII / LF |
| `sjis_crlf` | `#TITLE` 等に日本語を含み CRLF。文字コードと改行の保持 | Shift-JIS / CRLF |

fixture は実楽曲の譜面ではなく**手書きの最小譜面**とする。著作権とサイズを避けられ、
差分が人間に読める。実ファイルテストの価値は「本物の曲であること」ではなく
「ファイル全体を 1 往復させること」にあるため、これで目的を満たす。

大半を ASCII / LF にしたのは GitHub 上で golden の差分が読めるようにするためで、
文字コードと改行の検証は `sjis_crlf` の 1 本に集約する。

`tests/regenerate_golden.py` は全ケースを実行して `expected/` を上書きする。
`make golden` から呼ぶ。

## 7. 振る舞い変更: 改行コードの保持

これが今回唯一の意図的な振る舞い変更。

### 7.1 現状の問題

`load_file`（`replacement_tool.py:167`）は universal newlines で開くため `\r\n` が `\n` に潰れ、
`save_file`（`:212`）は `newline=None` で書くため `\n` が `os.linesep` に変換される。結果:

| 入力 | Windows exe | mac ビルド |
|---|---|---|
| CRLF | CRLF（維持） | LF（**全行が変わる**） |
| LF | CRLF（**全行が変わる**） | LF（維持） |

配布物が Windows exe のみのため実害は表面化していないが、golden テストの期待値が
実行 OS に依存してしまい、CI の OS を固定せざるを得なくなる。

### 7.2 修正内容

- `load_file`: `open(file_path, 'r', encoding='sjis', newline='')` で開く。
  universal newlines による**分割**は維持されるが**変換**は行われず、
  各行が元の行末を保持したまま返る。
- `save_file`: `open(output_path, 'w', encoding='sjis', newline='')` で書く。
- `update_content`: `'\n'` の直付けをやめ、元の行末を引き継ぐ。

```python
def _line_ending(line: str) -> str:
    """行末の改行コードを返す。最終行に改行が無い場合は空文字を返す。"""
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    if line.endswith("\r"):
        return "\r"
    return ""
```

`update_content` は `content_replaced[index]` の現在値から行末を取得して付け直す。
1 つの行インデックスは 1 つの小節にしか属さないため、二重更新は起こらない。

修正後は入力の改行がそのまま出力され、実行 OS に依存しなくなる。

### 7.3 変更しないもの

`update_content` が編集行を `.strip()` 済みの文字列で書き戻すため、
**行末の空白が失われる**という現行の振る舞いは維持する（`TODO.md` に記録する）。

## 8. CI

### 8.1 新規 `test.yml`

```yaml
name: Test
on:
  push:
    branches: ['**']
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: '3.13'
          enable-cache: true
      - run: uv sync              # --extra gui を付けない = tkinter 不要
      - run: uv run pytest
```

サードパーティ Action（`astral-sh/setup-uv`, `actions/upload-artifact`）のメジャー版は
実装時に最新を確認して固定する。上記は記述時点の想定値。

`ubuntu-latest` で回せるのは、改行修正によって golden が OS 非依存になり、かつ
`bms_core` が tkinter を必要としないため。`branches: ['**']` はタグ push には反応しないので、
`build-windows.yml` がタグ専用ワークフローである構造は変わらない。

タグを打つ時点でその commit は既に push 済み＝テスト済みなので、
リリース側のワークフローにテストジョブは追加しない。

### 8.2 `build-windows.yml` への `workflow_dispatch` 追加

リファクタで PyInstaller が `bms_core.py` を取り込めるかを確認する必要があるが、
現状このワークフローは `v*` タグ push でしか起動できない。手動実行を追加する。

```yaml
on:
  push:
    tags: ['v*']
  workflow_dispatch:
```

タグ以外での起動時は `github.ref_name` がブランチ名になるため、2 か所を分岐させる:

- `Upload to Release` ステップに `if: startsWith(github.ref, 'refs/tags/')` を付ける
- `workflow_dispatch` 時は `actions/upload-artifact@v4` で zip を成果物として保存する
  （ダウンロードして exe を実際に起動して確認できる）

`_version.py` の生成と zip 名は `github.ref_name` をそのまま使う。手動実行時は
ブランチ名が入るが、成果物は Release に載らないため実害はない。

常時のビルド CI は追加しない。ビルド設定はめったに変わらず、Windows runner の
コストに見合わないため。リファクタ後に 1 回手動実行して確認する。

## 9. 実装順序

現行コードは import すらできないため、先に移動しないとテストが 1 行も書けない。
したがって厳密な TDD ではなく、**移動 → 現行振る舞いを記述するテスト（characterization test）
→ 意図的な変更**の順で進める。

1. **環境整備** — `pyproject.toml` / `.venv` / pyright / `Makefile` / `.gitignore`。コード無変更。
   ここで uv の Python 3.13 に tkinter があるかを検証する。
2. **`bms_core.py` へ純粋移動** — ロジックは 1 行も変えない。GUI 側は結線のみに縮小。
   検証は差分レビューと `make build` の手動スモーク。
3. **ユニットテスト追加** — 現行の振る舞いをそのまま記述する。
4. **fixture + golden 追加** — この時点では改行が未修正のため、`sjis_crlf` の expected は
   入力が CRLF でも LF になる（mac / Linux とも `os.linesep` が `\n` のため、
   ステップ 7 で CI を追加するまでの間に OS 差でテストが割れることはない）。
5. **改行修正 + golden 再生成** — `sjis_crlf` だけが LF → CRLF に変わり、他 4 本は差分ゼロに
   なるはず。**これが「改行以外は何も変えていない」ことの証明になる**。
6. **`TODO.md` 追加**
7. **CI 追加** — `test.yml` 新規、`build-windows.yml` に `workflow_dispatch` 追加
8. **ビルド確認** — `build-windows.yml` を手動実行し、artifact の exe が起動することを確認

## 10. `TODO.md` 初版に記録する既知バグ

いずれも今回は修正しない。

1. `replace_notes` — データ部が空の行で `.split()[0]` が `IndexError` になる
   （`replacement_tool.py:263`, `:280`）
2. `collect_bgm_lane` — 「BGMレーン最大位置」に `0` を入れると BGM を 1 本も収集せず、
   置換が黙って 0 件になる。バリデーションは `0` を許可している（`:222`, `:127`）
3. `update_content` — 編集した行のみ `.strip()` 済みで書き戻すため、行末の空白が失われる
   （`:321`, `:324`）
4. `run_main` の `no_sound_objnumber.lower()` — 文字クラスが両ケースを含むため無意味な呼び出し
   （`:135`）
5. LN（`#LNOBJ`）未対応 — 終点オブジェクトが通常のキーチャンネル `11`-`29` に置かれるため、
   無音ノーツと誤認して移動すると LN が破損し得る（readme に既知として記載済み）
6. `build-windows.yml` を将来 uv ベースへ寄せる余地がある（現状は pip ベースで動作中のため据え置き）

## 11. 非スコープ

- GUI ウィジェットの自動テスト（`xvfb` / tkdnd のセットアップコストに見合わない）
- 上記 `TODO.md` に記録するバグの修正
- LN 対応
- Shift-JIS 以外の文字コード対応
- `src/` 配下へのパッケージ化
- Lint / formatter の導入
- `old_version/verX.Y.Z/` 運用の変更
