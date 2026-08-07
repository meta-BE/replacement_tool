"""replacement_tool（GUI エントリ）のテスト。

既存テストの大半は replacement_tool を一切 import しない。CI の test.yml も
`uv sync`（--extra gui 無し）なので tkinterdnd2 が入らず import できない。
つまり GUI エントリはリリースまで一切自動検証されない状態だった。
ここでは tkinter/tkinterdnd2 を最小限のスタブに差し替えた子プロセスで
import・実行させることで、GUI 無しでもエントリを検証する。
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 子プロセスで tkinter/tkinterdnd2 をスタブするための前置きスクリプト。
# tkinter/tkinterdnd2 の実体は無くても import 時に参照されないため、
# 属性を最小限だけ持つ空のモジュールで代替する。
_STUB_PRELUDE = """
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

# ダイアログ呼び出しを記録する。run_main は例外を握り潰して showerror を出すため、
# 戻り値ではなくここに記録された内容でしか成否を判定できない。
dialogs = {"info": [], "error": []}
messagebox_mod.showinfo = lambda title, message: dialogs["info"].append((title, message))
messagebox_mod.showerror = lambda title, message: dialogs["error"].append((title, message))
messagebox_mod.askyesno = lambda title, message: True

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
"""

_IMPORT_ONLY_SCRIPT = _STUB_PRELUDE + """
print(replacement_tool.run_main.__name__)
"""

# run_main を実際に呼び、bms_core への結線が生きていることを確認する。
# entries は .get() だけを持つ最小のスタブで足りる。
_RUN_MAIN_SCRIPT = _STUB_PRELUDE + """
import os
import tempfile

import bms_core


class _Entry:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


work = os.path.join(tempfile.mkdtemp(), "t.bms")
with open(work, "w", encoding="sjis", newline="") as f:
    f.write("#00101:0100\\n#00111:ZZ00\\n")

entries = [
    _Entry(work),
    _Entry("8"),
    _Entry("ZZ"),
    _Entry("1"),
    _Entry("1"),
    _Entry(bms_core.LANE_ORDER_OPTIONS[0]),
    _Entry(bms_core.SIDE_ORDER_OPTIONS[0]),
]

replacement_tool.run_main(entries)

assert not dialogs["error"], dialogs["error"]
assert dialogs["info"], "成功ダイアログが呼ばれていない"

with open(os.path.splitext(work)[0] + "_replaced.bms", encoding="sjis", newline="") as f:
    assert f.read() == "#00101:0000\\n#00111:0100\\n", "置換結果が期待と異なる"

print("OK")
"""


def _run_stubbed(script_source, tmp_path):
    """スタブ入りスクリプトを子プロセスで実行する。"""
    script = tmp_path / "check.py"
    script.write_text(script_source, encoding="utf-8")

    # 子プロセスはスクリプト自身のディレクトリ(tmp_path)を sys.path[0] にするため、
    # cwd=REPO_ROOT だけでは replacement_tool / bms_core が見つからない。pytest の
    # pythonpath 設定は pytest プロセス内の sys.path しか変更せず、環境変数
    # PYTHONPATH は継承されないため、明示的に PYTHONPATH を渡す。
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )


def test_replacement_tool_imports_with_stubbed_gui(tmp_path):
    """GUI エントリが import できることを、tkinter/tkinterdnd2 をスタブして確認する。

    モジュールレベルでウィジェットを構築していないため、スタブだけで import が通る。
    ただしここで検出できるのはモジュールレベルで評価される参照のみで、関数本体内の
    結線は test_run_main_is_wired_to_bms_core が担当する。
    """
    result = _run_stubbed(_IMPORT_ONLY_SCRIPT, tmp_path)

    assert result.returncode == 0, result.stderr
    assert "run_main" in result.stdout


def test_run_main_is_wired_to_bms_core(tmp_path):
    """run_main を実際に呼び、bms_core への結線と置換結果を検証する。

    run_main が entries を引数で受け取るため、GUI を起動せずに呼べる。
    tk._default_root 経由でグローバルに受け渡していた頃は不可能だった。
    存在しない bms_core の関数を呼ぶ結線ミスが入れば、run_main の except が
    それを握り潰して showerror を出すため、dialogs["error"] で検出できる。
    """
    result = _run_stubbed(_RUN_MAIN_SCRIPT, tmp_path)

    assert result.returncode == 0, result.stderr + result.stdout
    assert "OK" in result.stdout
