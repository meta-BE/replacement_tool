"""bms_core のファイル入出力と GUI 非依存性のテスト。"""

import os
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
    # 子プロセスはスクリプト自身のディレクトリ(tmp_path)を sys.path[0] にするため、
    # cwd=REPO_ROOT だけでは bms_core が見つからない。pytest の pythonpath 設定は
    # pytest プロセス内の sys.path しか変更せず、環境変数 PYTHONPATH は継承されない
    # ため、明示的に PYTHONPATH を渡す。
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
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
