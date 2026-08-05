"""replacement_tool（GUI エントリ）が import できることのテスト。

61件の既存テストは replacement_tool を一切 import しない。CI の test.yml も
`uv sync`（--extra gui 無し）なので tkinterdnd2 が入らず import できない。
つまり GUI エントリはリリースまで一切自動検証されない状態だった。
このテストは tkinter/tkinterdnd2 を最小限のスタブに差し替えた子プロセスで
import させることで、少なくとも import 時点のエラー（構文ミス・存在しない
モジュール属性の参照など）を検出できるようにする。
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 子プロセスで実行するスタブ+import スクリプト。
# tkinter/tkinterdnd2 の実体は無くても import 時に参照されないため、
# 属性を最小限だけ持つ空のモジュールで代替する。
_STUB_AND_IMPORT_SCRIPT = """
import sys
import types


def _make_module(name, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


tkinter_mod = _make_module("tkinter", END="end")
filedialog_mod = _make_module("tkinter.filedialog")
messagebox_mod = _make_module("tkinter.messagebox")
ttk_mod = _make_module("tkinter.ttk")

# `from tkinter import filedialog, messagebox` / `from tkinter import ttk` を通すには、
# サブモジュールを sys.modules に登録するだけでなく、tkinter パッケージ本体の属性としても
# 設定する必要がある。通常の import 機構を経由しないスタブでは自動的には設定されない。
tkinter_mod.filedialog = filedialog_mod
tkinter_mod.messagebox = messagebox_mod
tkinter_mod.ttk = ttk_mod

sys.modules["tkinter"] = tkinter_mod
sys.modules["tkinter.filedialog"] = filedialog_mod
sys.modules["tkinter.messagebox"] = messagebox_mod
sys.modules["tkinter.ttk"] = ttk_mod

# `from tkinterdnd2 import TkinterDnD, DND_FILES` を通すために両属性が必要。
tkinterdnd2_mod = _make_module("tkinterdnd2", TkinterDnD=object(), DND_FILES="DND_Files")
sys.modules["tkinterdnd2"] = tkinterdnd2_mod

import replacement_tool

print(replacement_tool.run_main.__name__)
"""


def test_replacement_tool_imports_with_stubbed_gui(tmp_path):
    """GUI エントリが import できることを、tkinter/tkinterdnd2 をスタブして確認する。

    モジュールレベルでウィジェットを構築していないため、スタブだけで import が通る。
    bms_core への結線ミス（存在しない関数の参照）をここで検出する。

    ただし検出できるのはモジュールレベルで評価される参照のみ。
    replacement_tool.py の bms_core.* 呼び出しはすべて create_gui / drop_file /
    run_main の関数本体内にあり、import 時には評価されない。そのため
    「関数内で存在しない bms_core の関数を呼んでいる」結線ミスはこのテストでは
    検出できない（詳細はミューテーション検証の報告を参照）。
    """
    script = tmp_path / "check.py"
    script.write_text(_STUB_AND_IMPORT_SCRIPT, encoding="utf-8")

    # 子プロセスはスクリプト自身のディレクトリ(tmp_path)を sys.path[0] にするため、
    # cwd=REPO_ROOT だけでは replacement_tool / bms_core が見つからない。pytest の
    # pythonpath 設定は pytest プロセス内の sys.path しか変更せず、環境変数
    # PYTHONPATH は継承されないため、明示的に PYTHONPATH を渡す。
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
    assert "run_main" in result.stdout
