# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 概要

BMS 譜面ファイル（.bms/.bml/.bme）内の「無音ノーツ」（`ZZ` など）を、BGM レーンに配置されたノーツへ自動で置換する GUI ツール。無音ノーツで概形を作った譜面を実ノーツへ変換する用途を想定。7KEYS / 14KEYS 譜面、62進数 BMS に対応。

## コマンド

```bash
# 開発環境セットアップ（uv ベース。CI と同じ Python 3.13 に揃える）
uv python install 3.13
uv sync --extra gui     # .venv を作成。GUI 実行や make build にも必要な tkinterdnd2 を含める
uv tool install pyright  # pyright-langserver を PATH に配置（LSP 用。.venv 内には入れない）

# 実行（GUI/ディスプレイが必要）
uv run python replacement_tool.py

# テスト実行（pytest。tests/ 配下 76件）
make test        # = uv run pytest
make typecheck    # = pyright（[tool.pyright] で .venv を参照）
make golden       # golden fixture (tests/fixtures/expected/*) を再生成。要目視 diff

# ローカル動作確認ビルド（mac ネイティブ。要 pyinstaller）
make build

# リリース（最新 v* タグを semver bump してタグ push → CI が Windows exe をビルド）
make release-patch   # / release-minor / release-major
```

- テストは `pytest`（`tests/` 配下、`pyproject.toml` の `[tool.pytest.ini_options]` で設定）。型チェックは `pyright`（同ファイルの `[tool.pyright]` で `.venv` を参照）。Lint 専用ツールは無い。
- 配布用 `.exe` は PyInstaller（onefile/console）でビルドする。`v*` タグ push を起点に GitHub Actions（`.github/workflows/build-windows.yml`, windows-latest）が exe をビルドし、`replacement_tool_<tag>.zip` を Release に添付する。exe はリポジトリにコミットしない。
  - zip 内の exe 名は日本語（`無音ノーツ自動置換ツール.exe`）のまま。Release のアセット名だけ ASCII にしているのは、GitHub がリリースアセット名の非ASCII文字を除去してしまうため（例: `無音…_v1.0.0.zip` が `_v1.0.0.zip` になる）。
- PyInstaller はクロスコンパイル不可のため、Windows exe の生成は CI 専用。`make build` は mac ネイティブの動作確認用。
- `.github/workflows/test.yml` が push（main）/ pull_request / 手動実行で pytest を ubuntu-latest / windows-latest 両方で走らせる。GUI 依存の `tkinterdnd2` は入れない（`uv sync` に `--extra gui` を付けない）ため、`replacement_tool.py` はスタブ経由でしか検証されない。`tests/test_gui_entry.py` が tkinter / tkinterdnd2 をスタブした子プロセスで import に加えて `run_main(entries)` の実行まで行うため、**関数本体内の `bms_core` 結線ミス（存在しない関数名の呼び出し）も検出できる**。これは `run_main` が entries をグローバル状態ではなく引数で受け取るようになったことで可能になった。

## アーキテクチャ

2ファイル構成。`bms_core.py` が純ロジック（tkinter 非依存・テスト対象）、`replacement_tool.py` が GUI エントリ（PyInstaller の入口。ファイル名は Makefile / build-windows.yml が依存しているため不変）。処理は関数チェーンで進む:

```
[replacement_tool.py]
create_gui() → run_main(entries)   # entries は .get() を持つウィジェット列。引数で渡す
  → bms_core.validate_params()   # 入力バリデーション（文字列 → int への変換も兼ねる）
  → bms_core.run_replacement()   # ここから bms_core.py 内で完結
  ...
drop_file() → bms_core.parse_dropped_path()   # D&D イベントデータからパスを1つ取り出す

[bms_core.py]
run_replacement()
  → load_file()        # sjis で読込（newline='' で改行コードを保持。後述）
  → process_bars()     # 小節ごとにループ
      → process_single_bar()
          → collect_bgm_lane()   # BGM レーン(chの01)を収集
          → collect_key_lanes()  # キーレーンを収集（順序はプルダウン設定で決定）
          → replace_notes()      # 置換の中核アルゴリズム
              → _object_string()  # データ部からオブジェクト列を取り出す（空データ部は空文字）
          → update_content()
  → save_file(content_replaced, file_path, on_conflict=None)
                        # 同階層に _replaced 付きで sjis 出力。on_conflict は上書き確認の
                        # 手段を呼び出し側(GUI)から注入するコールバック。None は「上書きしない」
```

`validate_params` と `parse_dropped_path` はどちらも元々 `replacement_tool.py` 内にあったロジックを `bms_core.py` へ抽出したもの（GUI に依存しないため）。旧 `main()` は `bms_core.run_replacement()` に改名している。

### 理解に不可欠な BMS ドメイン知識

出典: [BMS command definitions (hitkey)](https://hitkey.nekokan.dyndns.info/cmdsJP.htm)

- 行フォーマットは `#XXXYY:データ`。`XXX` = 小節番号（3桁ゼロ埋め、000-999）、`YY` = チャンネル。
- **チャンネル `01` = BGM レーン**（自動再生音）。同一小節に複数行あり得るが、各行は独立扱いで統合してはならない（仕様上の規定）。本ツールも 1 行ずつ収集して扱う。
- **キーレーンは beatmania IIDX 系の割り当て**を採用。1P 側 = `11,12,13,14,15,18,19`（7鍵）、2P 側 = `21,22,23,24,25,28,29`。`16`/`26` はスクラッチ、`17`/`27` は未使用で、いずれも `collect_key_lanes` のリストから除外され置換対象外。
- ノーツデータは **2文字1組**。`00` は「ノーツなし」。コロン以降のデータ部を `%`/`*` で分割した先頭要素が実データ。
- **オブジェクト番号の基数**: 標準 BMS は 16進（`00`-`FF`）または 36進（`00`-`ZZ`、1296種、**大文字小文字を区別しない**）。本ツールが対応を謳う「62進数」（`0-9A-Za-z` で大小文字を区別）は**標準仕様外の拡張**で、`#BASE` 相当の宣言コマンドも仕様には存在しない。無音ノーツ定義で大文字小文字を区別しているのはこの 62進拡張に合わせるため。

### 置換対象外チャンネルと LN の注意点

- 本ツールが**編集するのは `01`（BGM）と上記キーチャンネルのみ**。`02`（小節長/拍子）、`03`/`08`（BPM）、`09`（STOP）、`3x`/`4x`（不可視オブジェクト）、`5x`/`6x`（RDM 記法の LN）、`Dx`/`Ex`（地雷ノーツ）などはすべて素通しで保持される。
- **LN が未対応（readme 記載）の具体的理由**: `#LNOBJ` 方式の LN は、終点オブジェクトを RDM 用の別チャンネルではなく**通常のキーチャンネル `11`-`29` に直接配置**する。そのため LN 終点が本ツールの編集対象に紛れ込み、無音ノーツと誤認して移動すると LN が破損し得る。RDM 記法（`#LNTYPE 1`、チャンネル `5x`/`6x`）の LN はチャンネル的に編集対象外だが、こちらも動作は未検証。

### 置換アルゴリズムの「なぜ」（`replace_notes`）

各行はノーツ数（分解能）が異なり得るため、位置を**インデックス比較ではなく既約分数で比較**する。キー側の位置 `i/cutsize` と BGM 側の位置 `j/cutsize` をそれぞれ `gcd` で約分し、約分後の分子・分母が一致した場合に同一タイミングとみなして置換する。これにより分解能の異なる行同士でも正しくタイミングが対応する。置換時、キー側には BGM のオブジェクト番号を書き込み、BGM 側は `00`（消去）にする。

### プルダウン設定の意味

`bms_core.py` の `KEY_LANE_TABLE`（`(置換レーン順, 置換サイド順) → チャンネル配列` の辞書）が、GUI の「置換レーン順」×「置換サイド順」の全組み合わせを表現している。ここを変更するとキー音を割り当てる優先順位（左/右/中央から、1P→2P か 2P→1P か）が変わる。

GUI のプルダウン選択肢（`bms_core.LANE_ORDER_OPTIONS` / `bms_core.SIDE_ORDER_OPTIONS`）は `KEY_LANE_TABLE` のキーと兼用の文字列であり、`replacement_tool.py` はこの2つの定数からプルダウンの選択肢を導出する（`create_gui` 内でハードコードしない）。これにより「GUI の選択肢文字列」と「`collect_key_lanes` が参照するテーブルのキー」が別々に定義されて食い違う、という不整合が構造的に起きなくなっている。選択肢の文言を変える場合は `KEY_LANE_TABLE` のキーも必ず同時に変える。

## 重要な制約・慣習

- **文字コードは Shift-JIS（`sjis`）**。BMS ファイルの読込・書込は必ず sjis。`readme.txt` のみ UTF-8。※ BMS 仕様は文字コードを規定しておらず日本語譜面が慣習的に Shift_JIS なだけ。UTF-8 等の譜面は `load_file` で `UnicodeDecodeError` になり読込失敗する。
- **改行コードは入力をそのまま保持する**。`load_file` / `save_file` はいずれも `open(..., newline='')` で開いており、Python 側で改行コードの変換を行わない。`update_content` が行を書き戻す際も `_line_ending()` で元の行末（`\r\n` / `\n` / `\r` / 無し）を取り直して付け直すため、置換対象になった行も含めて入力の CRLF/LF がそのまま出力に引き継がれる。
- 無音ノーツ定義は**大文字・小文字を区別**する（バリデーションでも `00` は禁止）。
- 置換対象小節は `開始位置 ≦ 小節 ≦ 終了位置` の**閉区間**（終了位置の小節も含む）。v1.x では半開区間だったが、readme.txt の使用例が閉区間を前提に書かれており実装と食い違っていたため、readme 側に実装を合わせた。`start == end` は「その1小節だけ」を意味する有効な指定。
- BGM レーン最大値より右のレーンは置換対象外。キー音は BGM レーン左端から優先選択される。**空欄は「制限なし」**（`validate_params` が `None` を返し `collect_bgm_lane` が全件収集する）。`0` はこれとは別で「0本まで」を意味し1本も収集しない。両者を混同しないこと。
- バージョンは git tag（`v*`）を真実とし、ビルド時に `_version.py`（`__version__`）を生成して GUI タイトルに表示する。未生成時は `dev`。
- 旧版アーカイブとして `old_version/verX.Y.Z/` にコピーを残す運用は継続する（ただし exe バイナリはコミットしない）。現状 `old_version/` 配下に残るのは各バージョンの `readme.txt` のみで、ソースコードのスナップショットは含まれていない。ソースが `bms_core.py` / `replacement_tool.py` の2ファイルに分かれたことで、仮に将来ソースも archive する運用に変える場合は対象が単一スクリプトではなく2ファイルになる点に注意。
- **既知の問題は `TODO.md` に記録する**。かつては「記録するが修正しない」方針だったが、2026-08-07 に方針を変更し、記録済みのバグは修正する運用にした（LN 未対応など、規模の都合で残しているものは `TODO.md` に理由付きで残る）。挙動が仕様通りか疑わしい場合はまず `TODO.md` を確認すること。
