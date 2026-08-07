import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

import bms_core

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except ImportError:
    print("エラー: tkinterdnd2 ライブラリが見つかりません。インストールしてください: pip install tkinterdnd2")
    exit(1)

# バージョン: ビルド時に Makefile / CI が _version.py を生成して注入する。
# ローカルで直接実行するなど未生成の場合は dev にフォールバックする。
try:
    from _version import __version__
except ImportError:
    __version__ = "dev"

# ロギングの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 処理0-1: GUI表示
def create_gui():
    root = TkinterDnD.Tk()  # tkinterdnd2 の Tk を使用
    root.title(f"無音ノーツ自動置換ツール {__version__}")
    root.geometry("700x380")

    # ドラッグ・アンド・ドロップの設定
    root.drop_target_register(DND_FILES)
    root.dnd_bind('<<Drop>>', lambda event: drop_file(event, entries[0]))

    # 入力フィールドとラベル
    labels = [
        "ファイルパス（ドラッグ・アンド・ドロップでも読込可）:",
        "BGMレーン最大位置（空欄で無制限）:",
        "無音ノーツ定義（大文字・小文字は区別されます）:",
        "置換対象区間の開始位置（～小節目から）:",
        "置換対象区間の終了位置（～小節目の手前まで）:",
        "置換レーン順:",
        "置換サイド順（14Keysの設定）:"
    ]
    entries = []

    # プルダウンメニューの選択肢（レーン表と定義元を共有する）
    lane_order_options = bms_core.LANE_ORDER_OPTIONS
    side_order_options = bms_core.SIDE_ORDER_OPTIONS

    for i, label_text in enumerate(labels):
        tk.Label(root, text=label_text).grid(row=i, column=0, padx=10, pady=10, sticky="w")
        if label_text == "置換レーン順:":
            var = tk.StringVar(value=lane_order_options[0])  # 初期値設定
            entry = ttk.OptionMenu(root, var, lane_order_options[0], *lane_order_options)
            entry.grid(row=i, column=1, padx=10, pady=10, sticky="ew")
            entries.append(var)
        elif label_text == "置換サイド順（14Keysの設定）:":
            var = tk.StringVar(value=side_order_options[0])  # 初期値設定
            entry = ttk.OptionMenu(root, var, side_order_options[0], *side_order_options)
            entry.grid(row=i, column=1, padx=10, pady=10, sticky="ew")
            entries.append(var)
        else:
            entry = tk.Entry(root, width=50)
            entry.grid(row=i, column=1, padx=10, pady=10)
            entries.append(entry)

    # 参照ボタン
    browse_button = tk.Button(root, text="参照", command=lambda: browse_file(entries[0]))
    browse_button.grid(row=0, column=2, padx=10, pady=10)

    # 置換実行ボタン
    run_button = tk.Button(root, text="置換実行", command=run_main)
    run_button.grid(row=len(labels), column=1, pady=20)

    # root オブジェクトへの動的な属性追加。tkinter.Tk は entries 属性を持たないため
    # pyright が reportAttributeAccessIssue を出すが、GUI 内で entries を受け渡す
    # 既存の設計上の意図的なハックであり、このブランチのスコープ外（TODO.md 参照）。
    root.entries = entries  # pyright: ignore[reportAttributeAccessIssue]
    root.mainloop()

# 処理0-2: ファイル参照
def browse_file(entry):
    file_path = filedialog.askopenfilename(
        filetypes=[
            ("bms,bme,bml files", "*.bms;*.bme;*.bml"),
            ("All files", "*.*")
        ]
    )
    if file_path:
        entry.delete(0, tk.END)
        entry.insert(0, file_path)

# 処理0-3: ドラッグ・アンド・ドロップ
def drop_file(event, entry):
    file_path = event.data
    if file_path:
        file_path = bms_core.parse_dropped_path(file_path)
        entry.delete(0, tk.END)
        entry.insert(0, file_path)

# 処理0-4: メイン処理の実行
def run_main():
    # tkinter モジュールは _default_root を公開 API として型付けしていないため
    # pyright が reportAttributeAccessIssue を出すが、実行時には tkinter が
    # 内部的に維持しているグローバル状態であり動作上問題ない（TODO.md 参照）。
    entries = tk._default_root.entries  # pyright: ignore[reportAttributeAccessIssue]  # GUIからentriesを取得
    try:
        file_path = entries[0].get().strip()
        max_bgmlanenumber = entries[1].get().strip()
        no_sound_objnumber = entries[2].get().strip()  # 大文字・小文字区別
        start = entries[3].get().strip()
        end = entries[4].get().strip()
        lane_order = entries[5].get()  # プルダウン: 置換レーン順
        side_order = entries[6].get()  # プルダウン: 置換サイド順

        # バリデーション
        max_bgmlanenumber, start, end = bms_core.validate_params(
            file_path, max_bgmlanenumber, no_sound_objnumber, start, end
        )

        # メイン処理の実行
        logging.info(f"処理開始: file_path={file_path}, max_bgmlanenumber={max_bgmlanenumber}, no_sound_objnumber={no_sound_objnumber}, start={start}, end={end}, lane_order={lane_order}, side_order={side_order}")
        output_path, replace_count = bms_core.run_replacement(
            file_path, max_bgmlanenumber, no_sound_objnumber, start, end, lane_order, side_order,
            on_conflict=lambda path: messagebox.askyesno(
                "上書き確認", f"{path} は既に存在します。上書きしますか？"
            ),
        )
        messagebox.showinfo("成功", f"処理が完了しました。\n\n出力ファイル: {output_path}\n\n置換ノーツ数: {replace_count}")

    except ValueError as ve:
        logging.error(f"入力エラー: {str(ve)}")
        messagebox.showerror("入力エラー", f"入力エラー: {str(ve)}")
    except Exception as e:
        logging.error(f"処理中にエラーが発生しました: {str(e)}")
        messagebox.showerror("エラー", f"処理中にエラーが発生しました: {str(e)}")

# プログラム開始
if __name__ == "__main__":
    create_gui()