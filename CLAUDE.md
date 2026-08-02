# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 概要

BMS 譜面ファイル（.bms/.bml/.bme）内の「無音ノーツ」（`ZZ` など）を、BGM レーンに配置されたノーツへ自動で置換する GUI ツール。無音ノーツで概形を作った譜面を実ノーツへ変換する用途を想定。7KEYS / 14KEYS 譜面、62進数 BMS に対応。

## コマンド

```bash
# 依存ライブラリのインストール（tkinterdnd2 が唯一の外部依存）
pip install tkinterdnd2

# 実行（GUI/ディスプレイが必要）
python replacement_tool.py

# ローカル動作確認ビルド（mac ネイティブ。要 pyinstaller）
make build

# リリース（最新 v* タグを semver bump してタグ push → CI が Windows exe をビルド）
make release-patch   # / release-minor / release-major
```

- テスト・Lint 設定は存在しない（単一スクリプト構成）。
- 配布用 `.exe` は PyInstaller（onefile/console）でビルドする。`v*` タグ push を起点に GitHub Actions（`.github/workflows/build-windows.yml`, windows-latest）が exe をビルドし、`replacement_tool_<tag>.zip` を Release に添付する。exe はリポジトリにコミットしない。
  - zip 内の exe 名は日本語（`無音ノーツ自動置換ツール.exe`）のまま。Release のアセット名だけ ASCII にしているのは、GitHub がリリースアセット名の非ASCII文字を除去してしまうため（例: `無音…_v1.0.0.zip` が `_v1.0.0.zip` になる）。
- PyInstaller はクロスコンパイル不可のため、Windows exe の生成は CI 専用。`make build` は mac ネイティブの動作確認用。

## アーキテクチャ

全ロジックは `replacement_tool.py` 1ファイルに集約。処理は関数チェーンで進む:

```
create_gui() → run_main()[入力バリデーション] → main()
  → load_file()        # sjis で読込
  → process_bars()     # 小節ごとにループ
      → process_single_bar()
          → collect_bgm_lane()   # BGM レーン(chの01)を収集
          → collect_key_lanes()  # キーレーンを収集（順序はプルダウン設定で決定）
          → replace_notes()      # 置換の中核アルゴリズム
          → update_content()
  → save_file()        # 同階層に _replaced 付きで sjis 出力
```

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

`collect_key_lanes` 内のハードコードされたチャンネル配列が、GUI の「置換レーン順」×「置換サイド順」の全組み合わせを表現している。ここを変更するとキー音を割り当てる優先順位（左/右/中央から、1P→2P か 2P→1P か）が変わる。

## 重要な制約・慣習

- **文字コードは Shift-JIS（`sjis`）**。BMS ファイルの読込・書込は必ず sjis。`readme.txt` のみ UTF-8。※ BMS 仕様は文字コードを規定しておらず日本語譜面が慣習的に Shift_JIS なだけ。UTF-8 等の譜面は `load_file` で `UnicodeDecodeError` になり読込失敗する。
- 無音ノーツ定義は**大文字・小文字を区別**する（バリデーションでも `00` は禁止）。
- 置換対象小節は `開始位置 ≦ 小節 < 終了位置`（終了位置は含まない）。
- BGM レーン最大値より右のレーンは置換対象外。キー音は BGM レーン左端から優先選択される。
- バージョンは git tag（`v*`）を真実とし、ビルド時に `_version.py`（`__version__`）を生成して GUI タイトルに表示する。未生成時は `dev`。
- 旧版アーカイブとして `old_version/verX.Y.Z/` にコピーを残す運用は継続する（ただし exe バイナリはコミットしない）。
