# replacement_tool テスト基盤 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `replacement_tool` に GUI 非依存のロジック層 `bms_core.py` を切り出し、純関数のユニットテストと実ファイルを通す golden テストの2層構成、および `uv` ベースの開発環境と push/PR で回る CI を導入する。

**Architecture:** `replacement_tool.py`（330行の単一スクリプト）から純ロジックを `bms_core.py` へ移し、`tkinter` / `tkinterdnd2` の import を GUI エントリ側にのみ残す。既存コードは import すらできないため厳密な TDD は取れず、**移動 → 現行の振る舞いを記述する characterization test → 意図的な変更（改行保持）** の順で進める。golden はバイト単位比較とし、改行を OS 非依存にすることで CI を `ubuntu-latest` で回す。

**Tech Stack:** Python 3.13, uv, pytest, pyright, GNU Make, GitHub Actions (ubuntu-latest / windows-latest), PyInstaller。

**Spec:** `docs/superpowers/specs/2026-08-04-test-infrastructure-design.md`

## Global Constraints

以下は全タスク共通。各タスクの要件はこれを暗黙に含む。

- 作業ブランチは `test-infrastructure`（作成済み・spec コミット済み `12919f8`）。
- Python は **3.13**（CI の `build-windows.yml:19` に一致させる）。
- すべての出力・コミットメッセージ・コードコメントは**日本語**。
- 各コミットの末尾に `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` を付ける。
- PyInstaller のエントリポイント名 **`replacement_tool.py` は変更しない**（`Makefile` と `build-windows.yml` の両方が依存）。
- BMS ファイルの入出力エンコーディングは **`sjis`** 固定。
- **Task 7 以外で振る舞いを変えない。** 移動したロジックは1行も書き換えない。例外の型・メッセージ・ログ文言もそのまま維持する。
- 既存バグは**修正しない**。Task 8 で `TODO.md` に記録するだけ。
- `bms_core.py` は `tkinter` / `tkinterdnd2` を import してはならない。
- `.venv/` はコミットしない。

---

## File Structure

| ファイル | 区分 | 責務 |
|---|---|---|
| `bms_core.py` | 新規 | 置換ロジック・ファイル入出力・バリデーション。GUI 非依存 |
| `replacement_tool.py` | 変更 | GUI エントリ。ウィジェット構築と `bms_core` への結線のみ |
| `pyproject.toml` | 新規 | 依存・pytest・pyright 設定 |
| `Makefile` | 変更 | `test` / `typecheck` / `golden` ターゲット追加、`build` を `uv run` 経由へ |
| `.gitignore` | 変更 | `.venv/` を追加 |
| `.gitattributes` | 新規 | fixture のバイト保持（`-text`） |
| `TODO.md` | 新規 | 既知バグの記録 |
| `tests/test_io.py` | 新規 | `load_file` / `save_file` |
| `tests/test_collect_lanes.py` | 新規 | `collect_bgm_lane` / `collect_key_lanes` / `KEY_LANE_TABLE` |
| `tests/test_validation.py` | 新規 | `validate_params` / `parse_dropped_path` |
| `tests/test_replace_notes.py` | 新規 | `replace_notes` |
| `tests/test_newline.py` | 新規 | 改行保持（Task 7 で追加） |
| `tests/golden_cases.py` | 新規 | golden の入力とパラメータ定義。テストと再生成スクリプトで共有 |
| `tests/test_golden.py` | 新規 | 実ファイル往復のバイト比較 |
| `tests/regenerate_golden.py` | 新規 | golden 再生成 |
| `tests/fixtures/input/*.bms` | 新規 | 手書きの最小譜面 |
| `tests/fixtures/expected/*.bms` | 新規 | golden |
| `.github/workflows/test.yml` | 新規 | push / PR で pytest |
| `.github/workflows/build-windows.yml` | 変更 | `workflow_dispatch` 追加 |

---

### Task 1: 開発環境の整備

**Files:**
- Create: `pyproject.toml`
- Modify: `Makefile`, `.gitignore`

**Interfaces:**
- Consumes: なし
- Produces: `make test` で pytest が動く状態。`uv run python` がプロジェクトの `.venv`（Python 3.13）を使う。

- [ ] **Step 1: uv で Python 3.13 を用意する**

```bash
uv python install 3.13
```

- [ ] **Step 2: `pyproject.toml` を作成する**

`pythonpath = ["."]` はリポジトリルートを `sys.path` に入れ、`tests/` 配下から `import bms_core` を可能にするために必要（pytest の prepend モードは `tests/` しか追加しないため）。

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
pythonpath = ["."]

[tool.pyright]
venvPath = "."
venv = ".venv"
```

- [ ] **Step 3: `.venv` を作成する**

```bash
uv sync --extra gui
```

- [ ] **Step 4: uv の Python 3.13 に tkinter があるか検証する**

```bash
uv run --extra gui python -c "import tkinter; print('tkinter', tkinter.TkVersion)"
```

期待: `tkinter 8.6` のような出力。

**失敗した場合**: `make build` はローカルで動かないが、テストには影響しない（`bms_core` は tkinter 不要）。その事実を Task 8 の `TODO.md` に「ローカルの `make build` は tkinter 不足で動作しない。exe の確認は `build-windows.yml` の手動実行で行う」と記録して先へ進むこと。**ここで止まらない。**

- [ ] **Step 5: `.gitignore` に `.venv/` を追加する**

既存の末尾に1行追加する。

```
.venv/
```

- [ ] **Step 6: `Makefile` にターゲットを追加する**

`.PHONY` 行に `test typecheck golden` を追加し、既存の `build` ターゲットを差し替え、末尾に新ターゲットを追加する。

```make
.PHONY: build release-patch release-minor release-major _release _gen-version test typecheck golden
```

`build` ターゲットを次に差し替える（`.venv` 依存と `uv run` を追加）:

```make
# ローカル (mac ネイティブ) 動作確認用。Windows exe は CI で生成する。
build: .venv _gen-version
	uv run pyinstaller --onefile --collect-all tkinterdnd2 --name "無音ノーツ自動置換ツール" replacement_tool.py
```

ファイル末尾に追加:

```make
.venv: pyproject.toml
	uv sync --extra gui

test: .venv
	uv run pytest

typecheck: .venv
	pyright

golden: .venv
	uv run python tests/regenerate_golden.py
```

- [ ] **Step 7: pyright を PATH に入れる**

Claude Code の LSP が PATH 上の `pyright-langserver` を直接起動するため、`.venv` 内ではなく global tool として入れる。

```bash
uv tool install pyright
```

- [ ] **Step 8: pyright が起動することを確認する**

```bash
which pyright-langserver && pyright --version
```

期待: パスとバージョンが表示される。`which` が失敗する場合は `uv tool update-shell` を実行してシェルを開き直す。

- [ ] **Step 9: pytest が動くことを確認する**

```bash
make test
```

期待: `no tests ran` で終了する（この時点でテストは0件。**エラーで落ちなければ成功**）。

- [ ] **Step 10: コミット**

```bash
git add pyproject.toml Makefile .gitignore
git commit -m "$(cat <<'EOF'
build: uv ベースの開発環境と test/typecheck ターゲットを追加

Python 3.13 の .venv、pytest、pyright を導入する。GUI 依存(tkinterdnd2)は
extra に切り出し、テストが tkinter を必要としない構成にする。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `bms_core.py` へロジックを移動する

**Files:**
- Create: `bms_core.py`, `tests/test_io.py`
- Modify: `replacement_tool.py`

**Interfaces:**
- Consumes: Task 1 の `.venv` / pytest 設定
- Produces:
  - `bms_core.load_file(file_path) -> tuple[list[str], list[str]]`
  - `bms_core.save_file(content_replaced, file_path, on_conflict=None) -> str`
  - `bms_core.collect_bgm_lane(content, bar, max_bgmlanenumber) -> list[tuple[str, int]]`
  - `bms_core.collect_key_lanes(content, bar, lane_order, side_order) -> list[tuple[str, int]]`
  - `bms_core.replace_notes(lane_keys, lane_bgm, no_sound_objnumber) -> tuple[list, list, int]`
  - `bms_core.update_content(content_replaced, lane_keys, lane_bgm) -> None`
  - `bms_core.process_single_bar(...) -> int`
  - `bms_core.process_bars(...) -> int`
  - `bms_core.run_replacement(file_path, max_bgmlanenumber, no_sound_objnumber, start, end, lane_order, side_order, on_conflict=None) -> tuple[str, int]`

`save_file` の `on_conflict` は「出力先が既に存在するとき呼ばれ、上書きしてよければ `True` を返す」コールバック。`None` は「上書きしない」を意味する。これは**移動を成立させるために必須の変更**で、これが無いと `bms_core` が `messagebox` を import してしまい tkinter 非依存を達成できない。未使用だった `replace_count` 引数はここで削除する。

- [ ] **Step 1: 失敗するテストを書く（`tests/test_io.py`）**

```python
"""bms_core のファイル入出力と GUI 非依存性のテスト。"""

import subprocess
import sys
from pathlib import Path

import pytest

import bms_core

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_bms_core_imports_without_tkinter(tmp_path):
    """bms_core が tkinter に依存しないことを、import をブロックした子プロセスで確認する。

    sys.modules に None を入れると、その名前の import は ImportError になる。
    """
    script = tmp_path / "check.py"
    script.write_text(
        "import sys\n"
        "sys.modules['tkinter'] = None\n"
        "sys.modules['tkinterdnd2'] = None\n"
        "import bms_core\n"
        "print(bms_core.run_replacement.__name__)\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "run_replacement" in result.stdout


def test_load_file_reads_sjis(tmp_path):
    path = tmp_path / "t.bms"
    path.write_bytes("#TITLE テスト\n".encode("sjis"))

    content, content_replaced = bms_core.load_file(str(path))

    assert content == ["#TITLE テスト\n"]
    assert content_replaced == content
    assert content_replaced is not content  # copy を返すこと


def test_load_file_raises_on_invalid_sjis(tmp_path):
    path = tmp_path / "t.bms"
    path.write_bytes(b"#TITLE \x80\xff\n")

    with pytest.raises(UnicodeDecodeError):
        bms_core.load_file(str(path))


def test_save_file_writes_replaced_suffix_in_same_dir(tmp_path):
    src = tmp_path / "song.bms"
    src.write_bytes("#TITLE T\n".encode("sjis"))

    output_path = bms_core.save_file(["#TITLE X\n"], str(src))

    assert output_path == str(tmp_path / "song_replaced.bms")
    assert (tmp_path / "song_replaced.bms").read_text(encoding="sjis") == "#TITLE X\n"


def test_save_file_raises_when_output_exists_and_no_callback(tmp_path):
    src = tmp_path / "song.bms"
    src.write_bytes(b"")
    (tmp_path / "song_replaced.bms").write_bytes(b"old")

    with pytest.raises(Exception, match="上書きがキャンセルされました"):
        bms_core.save_file(["new\n"], str(src))

    assert (tmp_path / "song_replaced.bms").read_bytes() == b"old"


def test_save_file_raises_when_callback_returns_false(tmp_path):
    src = tmp_path / "song.bms"
    src.write_bytes(b"")
    (tmp_path / "song_replaced.bms").write_bytes(b"old")

    with pytest.raises(Exception, match="上書きがキャンセルされました"):
        bms_core.save_file(["new\n"], str(src), on_conflict=lambda p: False)

    assert (tmp_path / "song_replaced.bms").read_bytes() == b"old"


def test_save_file_overwrites_when_callback_returns_true(tmp_path):
    src = tmp_path / "song.bms"
    src.write_bytes(b"")
    (tmp_path / "song_replaced.bms").write_bytes(b"old")

    bms_core.save_file(["new\n"], str(src), on_conflict=lambda p: True)

    assert (tmp_path / "song_replaced.bms").read_text(encoding="sjis") == "new\n"
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/test_io.py -v
```

期待: 収集時に `ModuleNotFoundError: No module named 'bms_core'` で全件エラー。

- [ ] **Step 3: `bms_core.py` を作成する**

`replacement_tool.py` の該当関数を**1行も書き換えずに**移す。変更するのは `save_file` のシグネチャと上書き確認、`main` → `run_replacement` の改名のみ。`logging.basicConfig` はアプリケーション側の設定なので移さない（`replacement_tool.py` に残す）。

```python
"""BMS 譜面の無音ノーツ置換ロジック。GUI には依存しない。"""

import logging
import os
from math import gcd


# メイン処理
def run_replacement(file_path, max_bgmlanenumber, no_sound_objnumber, start, end, lane_order, side_order, on_conflict=None):
    content, content_replaced = load_file(file_path)
    replace_count = process_bars(content, content_replaced, start, end, max_bgmlanenumber, no_sound_objnumber, lane_order, side_order)
    output_path = save_file(content_replaced, file_path, on_conflict)
    return output_path, replace_count


# ファイル読み込み
def load_file(file_path):
    logging.info(f"ファイルの読み込み開始: {file_path}")
    try:
        with open(file_path, 'r', encoding='sjis') as f:
            content = f.readlines()
    except UnicodeDecodeError:
        logging.error("Shift-JISで読み込めませんでした")
        raise
    content_replaced = content.copy()
    logging.info(f"ファイル読み込み完了: {len(content)}行")
    return content, content_replaced


# 小節ごとの処理
def process_bars(content, content_replaced, start, end, max_bgmlanenumber, no_sound_objnumber, lane_order, side_order):
    replace_count = 0
    for bar in range(start, end):
        count = process_single_bar(content, content_replaced, bar, max_bgmlanenumber, no_sound_objnumber, lane_order, side_order)
        replace_count += count
    return replace_count


# 単一小節の処理
def process_single_bar(content, content_replaced, bar, max_bgmlanenumber, no_sound_objnumber, lane_order, side_order):
    logging.info(f"小節 {bar} の処理開始")
    lane_bgm = collect_bgm_lane(content, bar, max_bgmlanenumber)
    logging.info(f"小節 {bar} のBGMレーン: {len(lane_bgm)}個")

    replace_count = 0
    if lane_bgm:
        lane_keys = collect_key_lanes(content, bar, lane_order, side_order)
        logging.info(f"小節 {bar} のキーレーン: {len(lane_keys)}個")
        lane_keys, lane_bgm, count = replace_notes(lane_keys, lane_bgm, no_sound_objnumber)
        replace_count = count
        update_content(content_replaced, lane_keys, lane_bgm)

    logging.info(f"小節 {bar} の処理完了")
    return replace_count


# ファイル保存
def save_file(content_replaced, file_path, on_conflict=None):
    output_path = os.path.splitext(file_path)[0] + "_replaced" + os.path.splitext(file_path)[1]
    logging.info(f"ファイル出力開始: {output_path}")

    # 上書き確認の手段は呼び出し側(GUI)から渡す。None は「上書きしない」を意味する。
    if os.path.exists(output_path):
        if on_conflict is None or not on_conflict(output_path):
            logging.info("上書きがキャンセルされました")
            raise Exception("ファイルの上書きがキャンセルされました")

    with open(output_path, 'w', encoding='sjis') as f:
        f.writelines(content_replaced)
    logging.info(f"ファイル出力完了: {output_path}")
    return output_path


# BGMレーンの収集
def collect_bgm_lane(content, bar, max_bgmlanenumber):
    lane_bgm = []
    bar_str = f"{bar:03d}"
    for idx, line in enumerate(content):
        if line.startswith(f"#{bar_str}01") and len(lane_bgm) < max_bgmlanenumber:
            lane_bgm.append((line.strip(), idx))
    return lane_bgm


# キーレーンの収集
def collect_key_lanes(content, bar, lane_order, side_order):
    lane_keys = []
    bar_str = f"{bar:03d}"

    # プルダウンメニューに応じたkey_lanesの設定
    if side_order == "左レーン→右レーン":
        if lane_order == "1234567（左側レーンから順に置換）":
            key_lanes = ["11", "12", "13", "14", "15", "18", "19", "21", "22", "23", "24", "25", "28", "29"]
        elif lane_order == "7654321（右側レーンから順に置換）":
            key_lanes = ["19", "18", "15", "14", "13", "12", "11", "29", "28", "25", "24", "23", "22", "21"]
        elif lane_order == "4352617（中央レーンから順に置換１）":
            key_lanes = ["14", "13", "15", "12", "18", "11", "19", "24", "23", "25", "22", "28", "21", "29"]
        elif lane_order == "4536271（中央レーンから順に置換２）":
            key_lanes = ["14", "15", "13", "18", "12", "19", "11", "24", "25", "23", "28", "22", "29", "21"]
    else:  # side_order == "右レーン→左レーン"
        if lane_order == "1234567（左側レーンから順に置換）":
            key_lanes = ["21", "22", "23", "24", "25", "28", "29", "11", "12", "13", "14", "15", "18", "19"]
        elif lane_order == "7654321（右側レーンから順に置換）":
            key_lanes = ["29", "28", "25", "24", "23", "22", "21", "19", "18", "15", "14", "13", "12", "11"]
        elif lane_order == "4352617（中央レーンから順に置換１）":
            key_lanes = ["24", "23", "25", "22", "28", "21", "29", "14", "13", "15", "12", "18", "11", "19"]
        elif lane_order == "4536271（中央レーンから順に置換２）":
            key_lanes = ["24", "25", "23", "28", "22", "29", "21", "14", "15", "13", "18", "12", "19", "11"]

    for lane in key_lanes:
        for idx, line in enumerate(content):
            if line.startswith(f"#{bar_str}{lane}"):
                lane_keys.append((line.strip(), idx))
    return lane_keys
```

続けて `replace_notes` と `update_content` を、`replacement_tool.py:258-325` から**完全にそのまま**コピーして `bms_core.py` の末尾に追加する。インデント・コメント・ログ文言を含め一字も変えないこと。

- [ ] **Step 4: `replacement_tool.py` を GUI 側に絞る**

`replacement_tool.py` から次を削除する: `main`, `load_file`, `process_bars`, `process_single_bar`, `save_file`, `collect_bgm_lane`, `collect_key_lanes`, `replace_notes`, `update_content`、および `import os` と `from math import gcd`。

import 群（1〜7行目）を次に差し替える:

```python
import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import re

import bms_core
```

`run_main` の末尾（現 `:146`）の `main(...)` 呼び出しを差し替える:

```python
        output_path, replace_count = bms_core.run_replacement(
            file_path, max_bgmlanenumber, no_sound_objnumber, start, end, lane_order, side_order,
            on_conflict=lambda path: messagebox.askyesno(
                "上書き確認", f"{path} は既に存在します。上書きしますか？"
            ),
        )
```

`logging.basicConfig`、`try: from _version import __version__` のブロック、`try: from tkinterdnd2 import ...` のブロックは**そのまま残す**。

- [ ] **Step 5: テストが通ることを確認する**

```bash
uv run pytest tests/test_io.py -v
```

期待: 7件すべて PASS。

- [ ] **Step 6: GUI が壊れていないことを確認する**

```bash
uv run --extra gui python -c "import replacement_tool; print('import OK')"
```

期待: `import OK`。tkinter が無い環境ではこの確認をスキップし、その旨を報告すること（Task 1 Step 4 の結果に依存する）。

- [ ] **Step 7: コミット**

```bash
git add bms_core.py replacement_tool.py tests/test_io.py
git commit -m "$(cat <<'EOF'
refactor: 置換ロジックを bms_core.py へ分離する

tkinter への依存を GUI エントリ側に閉じ込め、ロジックをテスト可能にする。
save_file の上書き確認は messagebox 直呼びをやめ、呼び出し側から
コールバックで渡す形に変更した。ロジック自体は変更していない。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: レーン表を辞書化し GUI 選択肢を導出する

**Files:**
- Create: `tests/test_collect_lanes.py`
- Modify: `bms_core.py`, `replacement_tool.py`

**Interfaces:**
- Consumes: Task 2 の `bms_core.collect_key_lanes` / `collect_bgm_lane`
- Produces:
  - `bms_core.LANE_ORDER_OPTIONS: list[str]`（4要素）
  - `bms_core.SIDE_ORDER_OPTIONS: list[str]`（2要素）
  - `bms_core.KEY_LANE_TABLE: dict[tuple[str, str], list[str]]`（8エントリ、キーは `(lane_order, side_order)`）

現行は GUI の選択肢文字列と `collect_key_lanes` の分岐条件が別々に書かれており、片方だけ直すと `key_lanes` が未定義のまま参照され `UnboundLocalError` になる。定義元を1か所に集約して構造的に防ぐ。

- [ ] **Step 1: 失敗するテストを書く（`tests/test_collect_lanes.py`）**

```python
"""レーン収集とレーン表のテスト。"""

import bms_core


def test_table_covers_exactly_the_gui_options():
    """GUI の選択肢の全組合せが、過不足なくレーン表のキーになっていること。"""
    expected = {
        (lane, side)
        for lane in bms_core.LANE_ORDER_OPTIONS
        for side in bms_core.SIDE_ORDER_OPTIONS
    }
    assert set(bms_core.KEY_LANE_TABLE) == expected


def test_every_entry_has_14_unique_lanes():
    for key, lanes in bms_core.KEY_LANE_TABLE.items():
        assert len(lanes) == 14, key
        assert len(set(lanes)) == 14, key


def test_scratch_and_unused_channels_are_excluded():
    """16/26 はスクラッチ、17/27 は未使用。いずれも置換対象外。"""
    excluded = {"16", "17", "26", "27"}
    for key, lanes in bms_core.KEY_LANE_TABLE.items():
        assert not (set(lanes) & excluded), key


def test_collect_key_lanes_follows_table_order():
    """収集順はレーン表の並び順に従うこと（ファイル上の並び順ではない）。"""
    content = ["#00112:0100\n", "#00111:0200\n"]
    lane_order = bms_core.LANE_ORDER_OPTIONS[1]   # 7654321（右側レーンから順に置換）
    side_order = bms_core.SIDE_ORDER_OPTIONS[0]   # 左レーン→右レーン

    result = bms_core.collect_key_lanes(content, 1, lane_order, side_order)

    # 表の並びは 19,18,15,14,13,12,11,... なので 12 が 11 より先に来る
    assert result == [("#00112:0100", 0), ("#00111:0200", 1)]


def test_collect_bgm_lane_keeps_multiple_lines_separate():
    """同一小節に複数ある BGM 行は統合せず個別に扱う（BMS 仕様上の規定）。"""
    content = ["#00101:0100\n", "#00101:0200\n", "#00111:ZZ00\n"]

    assert bms_core.collect_bgm_lane(content, 1, 8) == [
        ("#00101:0100", 0),
        ("#00101:0200", 1),
    ]


def test_collect_bgm_lane_respects_max():
    content = ["#00101:0100\n", "#00101:0200\n", "#00101:0300\n"]

    assert bms_core.collect_bgm_lane(content, 1, 2) == [
        ("#00101:0100", 0),
        ("#00101:0200", 1),
    ]


def test_collect_bgm_lane_ignores_other_bars_and_channels():
    content = ["#00201:0100\n", "#00102:0.75\n", "#00109:0100\n", "#00101:0300\n"]

    assert bms_core.collect_bgm_lane(content, 1, 8) == [("#00101:0300", 3)]
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/test_collect_lanes.py -v
```

期待: `AttributeError: module 'bms_core' has no attribute 'LANE_ORDER_OPTIONS'` で先頭3件が失敗。`test_collect_key_lanes_follows_table_order` も同じ理由で失敗。`collect_bgm_lane` の3件は PASS する。

- [ ] **Step 3: `bms_core.py` に定義を追加し `collect_key_lanes` を書き換える**

`import` 群の直後（ファイル冒頭）に追加:

```python
# GUI のプルダウン選択肢。KEY_LANE_TABLE のキーと兼ねているため、
# 文字列を変える場合は必ず KEY_LANE_TABLE も同時に変わる。
LANE_ORDER_OPTIONS = [
    "1234567（左側レーンから順に置換）",
    "7654321（右側レーンから順に置換）",
    "4352617（中央レーンから順に置換１）",
    "4536271（中央レーンから順に置換２）",
]
SIDE_ORDER_OPTIONS = ["左レーン→右レーン", "右レーン→左レーン"]

# beatmania IIDX 系の割り当て。1P=11-19 / 2P=21-29。
# 16/26 はスクラッチ、17/27 は未使用のため置換対象に含めない。
KEY_LANE_TABLE = {
    (LANE_ORDER_OPTIONS[0], SIDE_ORDER_OPTIONS[0]): ["11", "12", "13", "14", "15", "18", "19", "21", "22", "23", "24", "25", "28", "29"],
    (LANE_ORDER_OPTIONS[1], SIDE_ORDER_OPTIONS[0]): ["19", "18", "15", "14", "13", "12", "11", "29", "28", "25", "24", "23", "22", "21"],
    (LANE_ORDER_OPTIONS[2], SIDE_ORDER_OPTIONS[0]): ["14", "13", "15", "12", "18", "11", "19", "24", "23", "25", "22", "28", "21", "29"],
    (LANE_ORDER_OPTIONS[3], SIDE_ORDER_OPTIONS[0]): ["14", "15", "13", "18", "12", "19", "11", "24", "25", "23", "28", "22", "29", "21"],
    (LANE_ORDER_OPTIONS[0], SIDE_ORDER_OPTIONS[1]): ["21", "22", "23", "24", "25", "28", "29", "11", "12", "13", "14", "15", "18", "19"],
    (LANE_ORDER_OPTIONS[1], SIDE_ORDER_OPTIONS[1]): ["29", "28", "25", "24", "23", "22", "21", "19", "18", "15", "14", "13", "12", "11"],
    (LANE_ORDER_OPTIONS[2], SIDE_ORDER_OPTIONS[1]): ["24", "23", "25", "22", "28", "21", "29", "14", "13", "15", "12", "18", "11", "19"],
    (LANE_ORDER_OPTIONS[3], SIDE_ORDER_OPTIONS[1]): ["24", "25", "23", "28", "22", "29", "21", "14", "15", "13", "18", "12", "19", "11"],
}
```

`collect_key_lanes` の本体を差し替える:

```python
# キーレーンの収集
def collect_key_lanes(content, bar, lane_order, side_order):
    lane_keys = []
    bar_str = f"{bar:03d}"
    key_lanes = KEY_LANE_TABLE[(lane_order, side_order)]

    for lane in key_lanes:
        for idx, line in enumerate(content):
            if line.startswith(f"#{bar_str}{lane}"):
                lane_keys.append((line.strip(), idx))
    return lane_keys
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/test_collect_lanes.py -v
```

期待: 7件すべて PASS。

- [ ] **Step 5: GUI の選択肢を `bms_core` から導出する**

`replacement_tool.py` の `create_gui` 内（現 `:47-54`）のローカル定義を削除し、参照に差し替える。

```python
    # プルダウンメニューの選択肢（レーン表と定義元を共有する）
    lane_order_options = bms_core.LANE_ORDER_OPTIONS
    side_order_options = bms_core.SIDE_ORDER_OPTIONS
```

以降の `lane_order_options[0]` などの参照はそのままで動く。

- [ ] **Step 6: 全テストを流して回帰が無いことを確認する**

```bash
make test
```

期待: 14件すべて PASS（`test_io.py` 7件 + `test_collect_lanes.py` 7件）。

- [ ] **Step 7: コミット**

```bash
git add bms_core.py replacement_tool.py tests/test_collect_lanes.py
git commit -m "$(cat <<'EOF'
refactor: レーン表を辞書化し GUI 選択肢の定義元を一本化する

collect_key_lanes の8分岐を KEY_LANE_TABLE へ集約し、GUI のプルダウン
選択肢をそこから導出するようにした。選択肢文字列だけを変更したときに
key_lanes が未定義になる事故が構造的に起きなくなる。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: バリデーションとドロップパス解析を抽出する

**Files:**
- Create: `tests/test_validation.py`
- Modify: `bms_core.py`, `replacement_tool.py`

**Interfaces:**
- Consumes: Task 3 の `bms_core`
- Produces:
  - `bms_core.validate_params(file_path, max_bgmlanenumber, no_sound_objnumber, start, end) -> tuple[int, int, int]` — 文字列を受け取り、検証して `(max_bgmlanenumber, start, end)` を int で返す。不正時は `ValueError`
  - `bms_core.parse_dropped_path(data: str) -> str`

**注意**: `"-1"` は `str.isdigit()` が `False` を返すため、範囲エラーではなく「整数で入力してください」になる。現行の振る舞いであり、変えない。

- [ ] **Step 1: 失敗するテストを書く（`tests/test_validation.py`）**

```python
"""入力バリデーションとドロップパス解析のテスト。"""

import pytest

import bms_core

VALID = dict(
    file_path="/tmp/a.bms",
    max_bgmlanenumber="8",
    no_sound_objnumber="ZZ",
    start="1",
    end="2",
)


def _call(**overrides):
    params = {**VALID, **overrides}
    return bms_core.validate_params(**params)


def test_valid_params_return_ints():
    assert _call() == (8, 1, 2)


@pytest.mark.parametrize("field", ["file_path", "max_bgmlanenumber", "no_sound_objnumber", "start", "end"])
def test_empty_field_is_rejected(field):
    with pytest.raises(ValueError, match="すべての項目を入力してください"):
        _call(**{field: ""})


def test_non_numeric_max_bgmlanenumber_is_rejected():
    with pytest.raises(ValueError, match="BGMレーン最大位置 は整数で入力してください"):
        _call(max_bgmlanenumber="abc")


def test_negative_value_is_rejected_as_non_integer():
    """'-1' は isdigit() が False のため、範囲エラーではなく整数エラーになる。"""
    with pytest.raises(ValueError, match="開始位置 は整数で入力してください"):
        _call(start="-1")


def test_out_of_range_value_is_rejected():
    with pytest.raises(ValueError, match="終了小節 は0～999の範囲で入力してください"):
        _call(end="1000")


@pytest.mark.parametrize("value", ["Z", "ZZZ", "Z-", "あ"])
def test_malformed_silent_note_is_rejected(value):
    with pytest.raises(ValueError, match="無音ノーツ定義は2桁の数字またはアルファベットで入力してください"):
        _call(no_sound_objnumber=value)


def test_zero_zero_silent_note_is_rejected():
    with pytest.raises(ValueError, match="無音ノーツ定義に '00' は使用できません"):
        _call(no_sound_objnumber="00")


def test_start_must_be_less_than_end():
    with pytest.raises(ValueError, match="開始位置は終了位置より小さくなければなりません"):
        _call(start="5", end="5")


def test_lowercase_silent_note_is_accepted():
    """62進拡張のため大文字・小文字を区別する。小文字も有効な定義。"""
    assert _call(no_sound_objnumber="zz") == (8, 1, 2)


def test_parse_dropped_path_plain():
    assert bms_core.parse_dropped_path("/a/b.bms") == "/a/b.bms"


def test_parse_dropped_path_single_braced():
    """空白を含むパスは中括弧で囲まれて渡される。"""
    assert bms_core.parse_dropped_path("{/a/b c.bms}") == "/a/b c.bms"


def test_parse_dropped_path_takes_first_of_multiple():
    assert bms_core.parse_dropped_path("{/a/1.bms} {/a/2.bms}") == "/a/1.bms"


def test_parse_dropped_path_empty():
    assert bms_core.parse_dropped_path("") == ""
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/test_validation.py -v
```

期待: `AttributeError: module 'bms_core' has no attribute 'validate_params'` で全件失敗。

- [ ] **Step 3: `bms_core.py` に2関数を追加する**

`import` に `re` を追加し、`KEY_LANE_TABLE` の定義の後に置く。検証内容と例外メッセージは `replacement_tool.py:119-142` から一字も変えない。

```python
NO_SOUND_PATTERN = re.compile(r'^[0-9A-Za-z]{2}$')


def validate_params(file_path, max_bgmlanenumber, no_sound_objnumber, start, end):
    """GUI から受け取った文字列を検証し、(max_bgmlanenumber, start, end) を int で返す。"""
    if not all([file_path, max_bgmlanenumber, no_sound_objnumber, start, end]):
        raise ValueError("すべての項目を入力してください")

    # 数値項目のチェック (0～999)
    for value, name in [(max_bgmlanenumber, "BGMレーン最大位置"), (start, "開始位置"), (end, "終了小節")]:
        if not value.isdigit():
            raise ValueError(f"{name} は整数で入力してください")
        num = int(value)
        if num < 0 or num > 999:
            raise ValueError(f"{name} は0～999の範囲で入力してください")

    max_bgmlanenumber = int(max_bgmlanenumber)
    start = int(start)
    end = int(end)

    # 無音ノーツ定義のチェック (2桁の数字/アルファベット, "00"以外)
    # .lower() は文字クラスが両ケースを含むため実質無意味だが、現行の振る舞いを維持する（TODO.md 参照）
    if not NO_SOUND_PATTERN.match(no_sound_objnumber.lower()):
        raise ValueError("無音ノーツ定義は2桁の数字またはアルファベットで入力してください")
    if no_sound_objnumber == "00":
        raise ValueError("無音ノーツ定義に '00' は使用できません")

    # 開始位置と終了位置の関係チェック
    if start >= end:
        raise ValueError("開始位置は終了位置より小さくなければなりません")

    return max_bgmlanenumber, start, end


def parse_dropped_path(data):
    """ドラッグ＆ドロップのイベントデータからファイルパスを1つ取り出す。

    複数ファイルがドロップされた場合、tkinterdnd2 は "{path1} {path2}" 形式で渡す。
    先頭の1つだけを使う。
    """
    if data.startswith('{') and data.endswith('}'):
        return data[1:-1].split('} {')[0]
    return data
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
uv run pytest tests/test_validation.py -v
```

期待: 20件すべて PASS。

- [ ] **Step 5: `replacement_tool.py` を抽出後の関数に差し替える**

`run_main` のバリデーション部（現 `:118-142`）を1行に置き換える:

```python
        max_bgmlanenumber, start, end = bms_core.validate_params(
            file_path, max_bgmlanenumber, no_sound_objnumber, start, end
        )
```

`drop_file` の解析部を差し替える:

```python
def drop_file(event, entry):
    file_path = event.data
    if file_path:
        file_path = bms_core.parse_dropped_path(file_path)
        entry.delete(0, tk.END)
        entry.insert(0, file_path)
```

`import re` が `replacement_tool.py` で未使用になるので削除する。

- [ ] **Step 6: 全テストを流す**

```bash
make test
```

期待: 34件すべて PASS。

- [ ] **Step 7: コミット**

```bash
git add bms_core.py replacement_tool.py tests/test_validation.py
git commit -m "$(cat <<'EOF'
refactor: バリデーションとドロップパス解析を bms_core へ抽出する

run_main と drop_file に埋まっていたロジックを純関数として切り出した。
検証内容と例外メッセージは現行のまま。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `replace_notes` の characterization テスト

**Files:**
- Create: `tests/test_replace_notes.py`

**Interfaces:**
- Consumes: `bms_core.replace_notes(lane_keys, lane_bgm, no_sound_objnumber) -> tuple[list, list, int]`
- Produces: なし（テストのみ。コードは変更しない）

このタスクは**コードを一切変更しない**。現行の振る舞いを記述して固定するだけ。テストが落ちたらテストの期待値ではなく実装を疑うのではなく、まず期待値の計算を検算すること（下記の各テストにトレース根拠をコメントで記載済み）。

- [ ] **Step 1: テストを書く（`tests/test_replace_notes.py`）**

```python
"""replace_notes の置換アルゴリズムのテスト。

位置の一致判定は既約分数で行われる。キー側 i/cutsize と BGM 側 j/cutsize を
それぞれ gcd で約分し、分子・分母がともに一致したときに同じタイミングとみなす。
"""

import pytest

import bms_core


def _run(key_lines, bgm_lines, no_sound="ZZ"):
    """行文字列のリストを (行, 行番号) のタプル列に整えて replace_notes を呼ぶ。"""
    lane_keys = [(line, i) for i, line in enumerate(key_lines)]
    lane_bgm = [(line, 100 + i) for i, line in enumerate(bgm_lines)]
    keys, bgm, count = bms_core.replace_notes(lane_keys, lane_bgm, no_sound)
    return [line for line, _ in keys], [line for line, _ in bgm], count


def test_same_resolution_same_position():
    # キー位置0 (0/2 -> 0/1) と BGM 位置0 (0/2 -> 0/1) が一致する
    keys, bgm, count = _run(["#00111:ZZ00"], ["#00101:0100"])

    assert keys == ["#00111:0100"]
    assert bgm == ["#00101:0000"]
    assert count == 1


def test_position_zero_matches_across_resolutions():
    # gcd(0, n) == n なので位置0は常に 0/1 に約分され、分解能が違っても一致する
    keys, bgm, count = _run(["#00111:ZZ000000"], ["#00101:0100"])

    assert keys == ["#00111:01000000"]
    assert bgm == ["#00101:0000"]
    assert count == 1


def test_different_resolution_matches_by_reduced_fraction():
    # キーは4分割、BGM は8分割。キー位置1 (1/4) と BGM 位置2 (2/8 -> 1/4) が対応する
    keys, bgm, count = _run(["#00111:00ZZ0000"], ["#00101:0102030405060708"])

    assert keys == ["#00111:00030000"]
    assert bgm == ["#00101:0102000405060708"]
    assert count == 1


def test_consumed_bgm_note_is_not_reused():
    # 1本目のキーが BGM 行1の位置0を消費するので、2本目は BGM 行2から取る
    keys, bgm, count = _run(
        ["#00111:ZZ00", "#00112:ZZ00"],
        ["#00101:0100", "#00101:0200"],
    )

    assert keys == ["#00111:0100", "#00112:0200"]
    assert bgm == ["#00101:0000", "#00101:0000"]
    assert count == 2


def test_non_silent_notes_are_untouched():
    keys, bgm, count = _run(["#00111:AA00"], ["#00101:0100"])

    assert keys == ["#00111:AA00"]
    assert bgm == ["#00101:0100"]
    assert count == 0


def test_silent_note_definition_is_case_sensitive():
    """62進拡張に合わせ、無音ノーツ定義は大文字・小文字を区別する。"""
    keys, bgm, count = _run(["#00111:zz00"], ["#00101:0100"], no_sound="ZZ")

    assert keys == ["#00111:zz00"]
    assert count == 0


def test_silent_note_remains_when_no_bgm_at_that_position():
    # キー位置1 (1/2) に対応する BGM ノーツが存在しない
    keys, bgm, count = _run(["#00111:00ZZ"], ["#00101:0100"])

    assert keys == ["#00111:00ZZ"]
    assert bgm == ["#00101:0100"]
    assert count == 0


def test_multiple_replacements_in_one_line():
    # キー位置0 (0/1) は BGM 位置0、キー位置2 (2/4 -> 1/2) は BGM 位置2 (2/4 -> 1/2)
    keys, bgm, count = _run(["#00111:ZZ00ZZ00"], ["#00101:01020304"])

    assert keys == ["#00111:01000300"]
    assert bgm == ["#00101:00020004"]
    assert count == 2


def test_odd_length_key_data_raises():
    with pytest.raises(Exception, match="キーオブジェクト数が2で割り切れません"):
        _run(["#00111:ZZ0"], ["#00101:0100"])


def test_odd_length_bgm_data_raises():
    with pytest.raises(Exception, match="BGMオブジェクト数が2で割り切れません"):
        _run(["#00111:ZZ00"], ["#00101:010"])
```

- [ ] **Step 2: テストを実行する**

```bash
uv run pytest tests/test_replace_notes.py -v
```

期待: 10件すべて PASS。**1件でも落ちたら実装を変更せず、期待値の計算を検算して報告すること**（このタスクは現行の振る舞いを記述するのが目的であり、実装を変えてはならない）。

- [ ] **Step 3: コミット**

```bash
git add tests/test_replace_notes.py
git commit -m "$(cat <<'EOF'
test: replace_notes の既約分数マッチを検証するテストを追加

分解能の異なる行同士のタイミング一致、消費済み BGM ノーツの非再利用、
無音ノーツ定義の大文字小文字区別など、現行の振る舞いを固定する。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: fixture と golden テスト

**Files:**
- Create: `tests/fixtures/input/basic_7k.bms`, `tests/fixtures/input/resolution_mix.bms`, `tests/fixtures/input/passthrough.bms`, `tests/fixtures/input/14k.bms`, `tests/fixtures/input/sjis_crlf.bms`
- Create: `tests/golden_cases.py`, `tests/test_golden.py`, `tests/regenerate_golden.py`, `.gitattributes`
- Create（生成物）: `tests/fixtures/expected/*.bms`

**Interfaces:**
- Consumes: `bms_core.run_replacement`, `bms_core.LANE_ORDER_OPTIONS`, `bms_core.SIDE_ORDER_OPTIONS`
- Produces: `tests/golden_cases.py` の `GOLDEN_CASES: list[tuple[str, str, dict]]`（ケース名, 入力ファイル名, `run_replacement` のキーワード引数）、`INPUT_DIR`, `EXPECTED_DIR`

- [ ] **Step 1: `.gitattributes` を作成する**

git の改行正規化で golden が壊れるのを防ぐ。golden はバイト単位で比較するため必須。

```
tests/fixtures/**/*.bms -text
```

- [ ] **Step 2: 入力 fixture を作成する**

次のスクリプトをリポジトリルートで実行する（`sjis_crlf.bms` は CRLF + Shift-JIS のため手打ちでは作らない）。

```bash
uv run python - <<'PYEOF'
from pathlib import Path

d = Path("tests/fixtures/input")
d.mkdir(parents=True, exist_ok=True)

basic_7k = """*---------------------- HEADER FIELD
#PLAYER 1
#GENRE TEST
#TITLE BASIC7K
#ARTIST TEST
#BPM 120
#PLAYLEVEL 1
#RANK 3

#WAV01 kick.wav
#WAV02 snare.wav
#WAV03 hat.wav
#WAV04 crash.wav
#WAVZZ silent.wav

*---------------------- MAIN DATA FIELD
#00101:01020304
#00111:ZZ00ZZ00
#00112:00ZZ00ZZ
#00201:01020304
#00211:ZZ00ZZ00
"""

resolution_mix = """#TITLE RESOLUTION
#00101:0102030405060708
#00111:ZZZZZZZZ
"""

passthrough = """#TITLE PASSTHROUGH
#00102:0.75
#00103:18
#00108:01
#00109:0100
#00116:ZZ000000
#00117:ZZ000000
#00131:ZZ000000
#00151:ZZ000000
#001D1:ZZ000000
#00101:01020304
#00111:ZZ00ZZ00
"""

fourteen_k = """#TITLE 14KEYS
#00101:0100
#00101:0200
#00111:ZZ00
#00121:ZZ00
"""

sjis_crlf = """#TITLE テスト譜面
#ARTIST 作者
#00101:0102
#00111:ZZ00
"""

for name, text in [
    ("basic_7k.bms", basic_7k),
    ("resolution_mix.bms", resolution_mix),
    ("passthrough.bms", passthrough),
    ("14k.bms", fourteen_k),
]:
    (d / name).write_bytes(text.encode("sjis"))

# 文字コードと改行の保持を検証する唯一の fixture（Shift-JIS + CRLF）
(d / "sjis_crlf.bms").write_bytes(sjis_crlf.replace("\n", "\r\n").encode("sjis"))

print("作成完了")
PYEOF
```

- [ ] **Step 3: fixture が意図どおりのバイト列か確認する**

```bash
file tests/fixtures/input/*.bms
uv run python -c "print(open('tests/fixtures/input/sjis_crlf.bms','rb').read())"
```

期待: `sjis_crlf.bms` の出力に `\r\n` と `\x83e\x83X\x83g`（「テスト」の Shift-JIS）が含まれること。他の4本には `\r` が含まれないこと。

- [ ] **Step 4: `tests/golden_cases.py` を作成する**

```python
"""golden テストの入力と実行パラメータの定義。テストと再生成スクリプトで共有する。"""

from pathlib import Path

import bms_core

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
INPUT_DIR = FIXTURE_DIR / "input"
EXPECTED_DIR = FIXTURE_DIR / "expected"

LANE_1234567 = bms_core.LANE_ORDER_OPTIONS[0]
LEFT_FIRST = bms_core.SIDE_ORDER_OPTIONS[0]
RIGHT_FIRST = bms_core.SIDE_ORDER_OPTIONS[1]

_BASE = dict(
    max_bgmlanenumber=8,
    no_sound_objnumber="ZZ",
    start=1,
    end=2,
    lane_order=LANE_1234567,
    side_order=LEFT_FIRST,
)

# (ケース名, 入力ファイル名, run_replacement のキーワード引数)
# 期待ファイルは expected/<ケース名>.bms
GOLDEN_CASES = [
    ("basic_7k", "basic_7k.bms", dict(_BASE)),
    ("resolution_mix", "resolution_mix.bms", dict(_BASE)),
    ("passthrough", "passthrough.bms", dict(_BASE)),
    ("14k_left_first", "14k.bms", dict(_BASE)),
    ("14k_right_first", "14k.bms", {**_BASE, "side_order": RIGHT_FIRST}),
    ("sjis_crlf", "sjis_crlf.bms", dict(_BASE)),
]
```

- [ ] **Step 5: `tests/regenerate_golden.py` を作成する**

```python
"""golden ファイルを再生成する。make golden から呼ぶ。

生成後は必ず git diff を目視で確認すること。golden はレビューされて初めて意味を持つ。
"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bms_core
from golden_cases import EXPECTED_DIR, GOLDEN_CASES, INPUT_DIR


def main():
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    for name, input_name, params in GOLDEN_CASES:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / input_name
            shutil.copyfile(INPUT_DIR / input_name, work)
            output_path, count = bms_core.run_replacement(file_path=str(work), **params)
            (EXPECTED_DIR / f"{name}.bms").write_bytes(Path(output_path).read_bytes())
            print(f"{name}: {count}件置換 -> expected/{name}.bms")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: `tests/test_golden.py` を作成する**

```python
"""実ファイルを1往復させる golden テスト。

バイト単位で比較することで、文字コード・改行・行数・非対象チャンネルの保持を
1つの assert で同時に検証する。
"""

import shutil
from pathlib import Path

import pytest

import bms_core
from golden_cases import EXPECTED_DIR, GOLDEN_CASES, INPUT_DIR


@pytest.mark.parametrize(
    "name, input_name, params",
    GOLDEN_CASES,
    ids=[case[0] for case in GOLDEN_CASES],
)
def test_golden(name, input_name, params, tmp_path):
    work = tmp_path / input_name
    shutil.copyfile(INPUT_DIR / input_name, work)

    output_path, _ = bms_core.run_replacement(file_path=str(work), **params)

    actual = Path(output_path).read_bytes()
    expected = (EXPECTED_DIR / f"{name}.bms").read_bytes()
    assert actual == expected
```

- [ ] **Step 7: golden を生成する**

```bash
make golden
```

期待する出力:

```
basic_7k: 4件置換 -> expected/basic_7k.bms
resolution_mix: 4件置換 -> expected/resolution_mix.bms
passthrough: 2件置換 -> expected/passthrough.bms
14k_left_first: 2件置換 -> expected/14k_left_first.bms
14k_right_first: 2件置換 -> expected/14k_right_first.bms
sjis_crlf: 1件置換 -> expected/sjis_crlf.bms
```

- [ ] **Step 8: 生成された golden を手で検算する**

**このステップを飛ばしてはならない。** golden は中身が正しいことを人が確認して初めて価値を持つ。

```bash
cat tests/fixtures/expected/basic_7k.bms
cat tests/fixtures/expected/14k_left_first.bms
cat tests/fixtures/expected/14k_right_first.bms
diff <(uv run python -c "print(open('tests/fixtures/input/passthrough.bms',encoding='sjis').read(),end='')") \
     <(uv run python -c "print(open('tests/fixtures/expected/passthrough.bms',encoding='sjis').read(),end='')")
```

確認すべき内容:

- `basic_7k.bms`: データ行が次の5行になっていること。**小節2（`#002xx`）は入力のまま変わっていないこと**（`start=1, end=2` は小節2を含まない）。

```
#00101:00000000
#00111:01000300
#00112:00020004
#00201:01020304
#00211:ZZ00ZZ00
```

- `resolution_mix.bms`: `#00101:0002000400060008` と `#00111:01030507`。キー4分割の位置0/1/2/3 が BGM 8分割の位置0/2/4/6 に対応している。
- `passthrough.bms`: 上記 `diff` の出力が **`#00101` と `#00111` の2行のみ**であること。`#00116`（スクラッチ）や `#00117`（未使用）に `ZZ` が残っていること。
- `14k_left_first.bms`: `#00111:0100` / `#00121:0200`（1P が先に BGM 行1を取る）。
- `14k_right_first.bms`: `#00111:0200` / `#00121:0100`（2P が先に BGM 行1を取る）。**左右で結果が入れ替わっていること**。
- `sjis_crlf.bms`: `#00101:0002` / `#00111:0100`。この時点では改行が **LF** になっている（改行修正は Task 7）。

- [ ] **Step 9: golden テストが通ることを確認する**

```bash
uv run pytest tests/test_golden.py -v
```

期待: 6件すべて PASS。

- [ ] **Step 10: 全テストを流す**

```bash
make test
```

期待: 50件すべて PASS。

- [ ] **Step 11: コミット**

```bash
git add .gitattributes tests/fixtures tests/golden_cases.py tests/test_golden.py tests/regenerate_golden.py
git commit -m "$(cat <<'EOF'
test: 実ファイルを往復させる golden テストを追加

手書きの最小譜面5本を fixture とし、出力をバイト単位で比較する。
非対象チャンネルの素通し、置換対象小節の範囲、14Keys の左右順、
Shift-JIS の往復を検証する。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: 入力の改行コードを保持する

**Files:**
- Create: `tests/test_newline.py`
- Modify: `bms_core.py`
- Modify（再生成）: `tests/fixtures/expected/sjis_crlf.bms`

**Interfaces:**
- Consumes: `bms_core.run_replacement`, `bms_core.update_content`
- Produces: `bms_core._line_ending(line: str) -> str`（内部ヘルパ）

**このタスクが計画で唯一の意図的な振る舞い変更。** 現状は読込時に universal newlines で `\r\n` が `\n` に潰れ、書込時に `os.linesep` へ変換されるため、CRLF の譜面を mac ビルドで処理すると全行が LF に変わる。修正後は入力の改行がそのまま出力され、実行 OS に依存しなくなる。

- [ ] **Step 1: 失敗するテストを書く（`tests/test_newline.py`）**

```python
"""改行コードの保持を検証する。バイト単位で比較する。"""

from pathlib import Path

import bms_core

PARAMS = dict(
    max_bgmlanenumber=8,
    no_sound_objnumber="ZZ",
    start=1,
    end=2,
    lane_order=bms_core.LANE_ORDER_OPTIONS[0],
    side_order=bms_core.SIDE_ORDER_OPTIONS[0],
)


def _run(tmp_path, raw):
    src = tmp_path / "t.bms"
    src.write_bytes(raw)
    output_path, _ = bms_core.run_replacement(file_path=str(src), **PARAMS)
    return Path(output_path).read_bytes()


def test_crlf_is_preserved(tmp_path):
    result = _run(tmp_path, b"#00101:0102\r\n#00111:ZZ00\r\n")

    assert result == b"#00101:0002\r\n#00111:0100\r\n"


def test_lf_is_preserved(tmp_path):
    result = _run(tmp_path, b"#00101:0102\n#00111:ZZ00\n")

    assert result == b"#00101:0002\n#00111:0100\n"


def test_missing_trailing_newline_is_preserved(tmp_path):
    result = _run(tmp_path, b"#00101:0102\n#00111:ZZ00")

    assert result == b"#00101:0002\n#00111:0100"


def test_untouched_lines_keep_their_newline(tmp_path):
    """置換対象外の行も改行が変わらないこと。"""
    result = _run(tmp_path, b"#TITLE T\r\n#00101:0102\r\n#00111:ZZ00\r\n")

    assert result == b"#TITLE T\r\n#00101:0002\r\n#00111:0100\r\n"
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
uv run pytest tests/test_newline.py -v
```

期待: `test_crlf_is_preserved` と `test_untouched_lines_keep_their_newline` が FAIL（`\r\n` ではなく `\n` が返る）。`test_lf_is_preserved` は PASS。`test_missing_trailing_newline_is_preserved` は PASS。

- [ ] **Step 3: `load_file` と `save_file` を `newline=''` に変える**

`bms_core.py` の `load_file` の `open` を差し替える:

```python
        # newline='' で開くと、行の分割は行いつつ改行コードの変換を行わない。
        # 入力の CRLF/LF をそのまま往復させるために必要。
        with open(file_path, 'r', encoding='sjis', newline='') as f:
            content = f.readlines()
```

`save_file` の `open` を差し替える:

```python
    with open(output_path, 'w', encoding='sjis', newline='') as f:
        f.writelines(content_replaced)
```

- [ ] **Step 4: `update_content` を行末保持に変える**

`bms_core.py` の `update_content` の直前にヘルパを追加し、本体を差し替える:

```python
def _line_ending(line):
    """行末の改行コードを返す。最終行に改行が無い場合は空文字を返す。"""
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    if line.endswith("\r"):
        return "\r"
    return ""


# コンテンツ更新
def update_content(content_replaced, lane_keys, lane_bgm):
    # 収集時に strip() 済みの行を書き戻すため、元の行末を取り直して付け直す。
    for set_key_single, key_index in lane_keys:
        content_replaced[key_index] = set_key_single + _line_ending(content_replaced[key_index])
        logging.debug(f"キー行更新: 行 {key_index}")
    for set_bgm_single, bgm_index in lane_bgm:
        content_replaced[bgm_index] = set_bgm_single + _line_ending(content_replaced[bgm_index])
        logging.debug(f"BGM行更新: 行 {bgm_index}")
```

- [ ] **Step 5: テストが通ることを確認する**

```bash
uv run pytest tests/test_newline.py -v
```

期待: 4件すべて PASS。

- [ ] **Step 6: golden を再生成する**

```bash
make golden
```

- [ ] **Step 7: golden の差分が `sjis_crlf.bms` だけであることを確認する**

**これが「改行以外は何も変えていない」ことの証明になる。**

```bash
git status --short tests/fixtures/expected/
```

期待: `M tests/fixtures/expected/sjis_crlf.bms` の **1行のみ**。他の5本に差分が出た場合は改行修正が他の振る舞いを壊しているので、**先へ進まず報告すること**。

```bash
uv run python -c "print(open('tests/fixtures/expected/sjis_crlf.bms','rb').read())"
```

期待: `\r\n` が含まれること。

- [ ] **Step 8: 全テストを流す**

```bash
make test
```

期待: 54件すべて PASS。

- [ ] **Step 9: コミット**

```bash
git add bms_core.py tests/test_newline.py tests/fixtures/expected/sjis_crlf.bms
git commit -m "$(cat <<'EOF'
fix: 入力ファイルの改行コードを保持する

読込・書込とも newline='' で開き、update_content は元の行末を引き継ぐ
ようにした。従来は CRLF の譜面を mac ビルドで処理すると全行が LF に、
LF の譜面を Windows exe で処理すると全行が CRLF に変わっていた。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: `TODO.md` と CI

**Files:**
- Create: `TODO.md`, `.github/workflows/test.yml`
- Modify: `.github/workflows/build-windows.yml`

**Interfaces:**
- Consumes: Task 1 の `pyproject.toml`（`uv sync` / `uv run pytest`）
- Produces: push / PR で回るテストジョブ、`build-windows.yml` の手動実行

- [ ] **Step 1: `TODO.md` を作成する**

Task 1 Step 4（uv の Python に tkinter があるか）の結果に応じて、末尾の「7.」を含めるか判断すること。tkinter があった場合は 7. を削除する。

```markdown
# TODO

テスト基盤の導入（2026-08-04）中に見つかった既知の問題。いずれも未修正。

## 既知バグ

1. **`replace_notes` がデータ部の空な行で `IndexError` になる**
   `bms_core.py` の `obj_str = ...split()[0]` は、コロン以降が空の行（`#00111:`）で
   `IndexError: list index out of range` を送出する。キー側・BGM側の両方に同じ問題がある。

2. **「BGMレーン最大位置」に `0` を入れると黙って何も置換されない**
   `collect_bgm_lane` の `len(lane_bgm) < max_bgmlanenumber` により BGM 行を1本も収集せず、
   `process_single_bar` の `if lane_bgm:` が偽になって置換が0件で終わる。
   `validate_params` は `0` を許可しているため、エラーも警告も出ない。

3. **編集した行の行末の空白が失われる**
   `collect_bgm_lane` / `collect_key_lanes` が `line.strip()` で収集し、`update_content` が
   それを書き戻すため、置換対象になった行に限り行末の空白が消える。

4. **`validate_params` の `no_sound_objnumber.lower()` が無意味**
   正規表現 `^[0-9A-Za-z]{2}$` が大文字・小文字の両方を含むため、`.lower()` は結果を変えない。
   現行の振る舞いを維持するために残している。

5. **LN（`#LNOBJ`）が未対応**
   `#LNOBJ` 方式の LN は終点オブジェクトを RDM 用チャンネルではなく通常のキーチャンネル
   `11`-`29` に直接配置するため、無音ノーツと誤認して移動すると LN が破損し得る。
   RDM 記法（`#LNTYPE 1`、チャンネル `5x`/`6x`）はチャンネル的に編集対象外だが動作は未検証。

## 改善余地

6. `.github/workflows/build-windows.yml` は pip ベースのまま。将来 uv へ寄せる余地がある。

7. ローカルの `make build` は uv の Python 3.13 に tkinter が無いため動作しない。
   exe の確認は `build-windows.yml` の手動実行（`workflow_dispatch`）で行う。
```

- [ ] **Step 2: `.github/workflows/test.yml` を作成する**

`astral-sh/setup-uv` と `actions/checkout` の最新メジャー版を実行前に確認して固定すること。

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

      # --extra gui を付けない。テストは tkinter を必要としない。
      - name: Install dependencies
        run: uv sync

      - name: Run tests
        run: uv run pytest -v
```

`branches: ['**']` はブランチ push にのみ反応し、タグ push には反応しない。`build-windows.yml` がタグ専用ワークフローである構造は変わらない。

- [ ] **Step 3: `build-windows.yml` に `workflow_dispatch` を追加する**

`on:` ブロックを差し替える:

```yaml
on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
```

`Upload to Release` ステップに条件を追加する:

```yaml
      - name: Upload to Release
        if: startsWith(github.ref, 'refs/tags/')
        uses: softprops/action-gh-release@v2
        with:
          files: dist/replacement_tool_${{ github.ref_name }}.zip
```

その後ろに手動実行用のステップを追加する:

```yaml
      - name: Upload artifact (手動実行時)
        if: github.event_name == 'workflow_dispatch'
        uses: actions/upload-artifact@v4
        with:
          name: replacement_tool_${{ github.ref_name }}
          path: dist/replacement_tool_${{ github.ref_name }}.zip
```

手動実行時は `github.ref_name` がブランチ名になるが、成果物は Release に載らないため実害はない。

- [ ] **Step 4: ワークフローの YAML 構文を検証する**

```bash
uv run python -c "
import sys
try:
    import yaml
except ImportError:
    print('PyYAML 未導入のためスキップ'); sys.exit(0)
for p in ['.github/workflows/test.yml', '.github/workflows/build-windows.yml']:
    yaml.safe_load(open(p, encoding='utf-8')); print('OK', p)
"
```

PyYAML が無ければこのステップはスキップしてよい（CI 側で検証される）。

- [ ] **Step 5: 全テストを流す**

```bash
make test
```

期待: 54件すべて PASS。

- [ ] **Step 6: コミット**

```bash
git add TODO.md .github/workflows/test.yml .github/workflows/build-windows.yml
git commit -m "$(cat <<'EOF'
ci: push/PR で pytest を実行し、Windows ビルドを手動実行可能にする

test.yml を追加して ubuntu-latest でテストを回す。build-windows.yml には
workflow_dispatch を追加し、タグ以外での実行では Release ではなく
artifact として zip を残すようにした。既知バグは TODO.md に記録した。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 7: push して CI が通ることを確認する**

```bash
git push -u origin test-infrastructure
gh run list --branch test-infrastructure --limit 3
```

期待: `Test` ワークフローが `completed / success` になる。失敗した場合はログを確認して修正すること。

```bash
gh run watch
```

---

### Task 9: Windows ビルドの確認

**Files:** なし（確認のみ）

**Interfaces:**
- Consumes: Task 8 で追加した `workflow_dispatch`
- Produces: なし

このタスクは**リファクタで PyInstaller が `bms_core.py` を取り込めるか**を確認するもの。`--onefile` の依存解析は `replacement_tool.py` の `import bms_core` を辿って同梱するはずだが、実測で確認する。

- [ ] **Step 1: ビルドワークフローを手動実行する**

```bash
gh workflow run build-windows.yml --ref test-infrastructure
```

- [ ] **Step 2: 完了を待つ**

```bash
gh run watch
```

期待: `completed / success`。

- [ ] **Step 3: artifact が生成されていることを確認する**

```bash
gh run list --workflow build-windows.yml --limit 1
gh run download <RUN_ID> --dir /tmp/build-check
ls -la /tmp/build-check
```

期待: zip が存在し、展開すると `無音ノーツ自動置換ツール.exe` と `readme.txt` が含まれること。

- [ ] **Step 4: 人による確認を依頼する**

**ここは自動化できない。** ユーザーに次を依頼して報告を待つこと。

> Windows 環境で artifact の exe を起動し、
> (1) GUI が表示されること、
> (2) プルダウンに4つのレーン順と2つのサイド順が出ること、
> (3) 実際の譜面を1つ置換して結果が想定どおりであること
> を確認してください。

- [ ] **Step 5: 確認結果を報告する**

exe が起動しない場合は PyInstaller が `bms_core.py` を取り込めていない可能性が高い。その場合は `--hidden-import bms_core` の追加、あるいは `--paths .` の指定を検討する。

---

## Self-Review

**1. Spec coverage**

| spec のセクション | 対応タスク |
|---|---|
| 5.1 ファイル構成 | Task 1〜8 全体 |
| 5.2 `bms_core.py` の公開 API | Task 2, 3, 4 |
| 5.2.1 レーン表の辞書化 | Task 3 |
| 5.2.2 バリデーションの抽出 | Task 4 |
| 5.2.3 上書き確認の注入 | Task 2（移動を成立させるため前倒し） |
| 5.3 GUI エントリ | Task 2 Step 4, Task 3 Step 5, Task 4 Step 5 |
| 5.4 `pyproject.toml` | Task 1 Step 2 |
| 5.5 開発環境セットアップ | Task 1 Step 1, 3, 4, 7 |
| 5.6 Makefile | Task 1 Step 6 |
| 5.7 `.gitignore` / `.gitattributes` | Task 1 Step 5, Task 6 Step 1 |
| 6.1 ユニットテスト | Task 2, 3, 4, 5 |
| 6.2 golden テスト | Task 6 |
| 6.3 fixture | Task 6 Step 2 |
| 7 改行保持 | Task 7 |
| 8.1 `test.yml` | Task 8 Step 2 |
| 8.2 `workflow_dispatch` | Task 8 Step 3, Task 9 |
| 10 `TODO.md` | Task 8 Step 1 |

spec 5.4 に無かった `pythonpath = ["."]` を Task 1 で追加している。`tests/` から `import bms_core` を可能にするための実装詳細で、spec の意図（テストが `bms_core` を import できること）に沿う。

spec 9 の実装順序に対し、`save_file` の `on_conflict` 化を Task 2 に前倒ししている。これを分けると Task 2 の時点で `bms_core` が `messagebox` を import することになり、「tkinter 非依存」という Task 2 の成果物が成立しないため。

**2. Placeholder scan**

`TODO.md` の項目7、`test.yml` の Action バージョン、Task 9 Step 4 の人手確認は、いずれも条件と判断基準を明記しており「後で決める」ものではない。それ以外にプレースホルダは無い。

**3. Type consistency**

- `save_file(content_replaced, file_path, on_conflict=None)` — Task 2 で定義、Task 7 で `open` のみ変更。引数は不変。
- `run_replacement(...)` の引数名は Task 2 の定義、Task 6 の `golden_cases.py`、Task 7 の `test_newline.py` で一致（`file_path` / `max_bgmlanenumber` / `no_sound_objnumber` / `start` / `end` / `lane_order` / `side_order` / `on_conflict`）。
- `LANE_ORDER_OPTIONS` / `SIDE_ORDER_OPTIONS` / `KEY_LANE_TABLE` — Task 3 で定義、Task 6・Task 7 で参照。名称一致。
- `GOLDEN_CASES` の要素は `(name, input_name, params)` の3タプル。`test_golden.py` の `parametrize` と `regenerate_golden.py` の `for` で一致。
- `INPUT_DIR` / `EXPECTED_DIR` — `golden_cases.py` で定義、両利用箇所で一致。
