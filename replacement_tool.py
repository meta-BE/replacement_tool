import os
from math import gcd
import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import re

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
        "BGMレーン最大位置:",
        "無音ノーツ定義（大文字・小文字は区別されます）:",
        "置換対象区間の開始位置（～小節目から）:",
        "置換対象区間の終了位置（～小節目の手前まで）:",
        "置換レーン順:",
        "置換サイド順（14Keysの設定）:"
    ]
    entries = []

    # プルダウンメニューの選択肢
    lane_order_options = [
        "1234567（左側レーンから順に置換）",
        "7654321（右側レーンから順に置換）",
        "4352617（中央レーンから順に置換１）",
        "4536271（中央レーンから順に置換２）"
    ]
    side_order_options = ["左レーン→右レーン", "右レーン→左レーン"]

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

    root.entries = entries  # entriesをrootに保持
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
        # 複数ファイルがドロップされた場合、最初のファイルのみ使用
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1].split('} {')[0]
        entry.delete(0, tk.END)
        entry.insert(0, file_path)

# 処理0-4: メイン処理の実行
def run_main():
    entries = tk._default_root.entries  # GUIからentriesを取得
    try:
        file_path = entries[0].get().strip()
        max_bgmlanenumber = entries[1].get().strip()
        no_sound_objnumber = entries[2].get().strip()  # 大文字・小文字区別
        start = entries[3].get().strip()
        end = entries[4].get().strip()
        lane_order = entries[5].get()  # プルダウン: 置換レーン順
        side_order = entries[6].get()  # プルダウン: 置換サイド順

        # バリデーション
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
        if not re.match(r'^[0-9A-Za-z]{2}$', no_sound_objnumber.lower()):
            raise ValueError("無音ノーツ定義は2桁の数字またはアルファベットで入力してください")
        if no_sound_objnumber == "00":
            raise ValueError("無音ノーツ定義に '00' は使用できません")

        # 開始位置と終了位置の関係チェック
        if start >= end:
            raise ValueError("開始位置は終了位置より小さくなければなりません")

        # メイン処理の実行
        logging.info(f"処理開始: file_path={file_path}, max_bgmlanenumber={max_bgmlanenumber}, no_sound_objnumber={no_sound_objnumber}, start={start}, end={end}, lane_order={lane_order}, side_order={side_order}")
        output_path, replace_count = main(file_path, max_bgmlanenumber, no_sound_objnumber, start, end, lane_order, side_order)
        messagebox.showinfo("成功", f"処理が完了しました。\n\n出力ファイル: {output_path}\n\n置換ノーツ数: {replace_count}")

    except ValueError as ve:
        logging.error(f"入力エラー: {str(ve)}")
        messagebox.showerror("入力エラー", f"入力エラー: {str(ve)}")
    except Exception as e:
        logging.error(f"処理中にエラーが発生しました: {str(e)}")
        messagebox.showerror("エラー", f"処理中にエラーが発生しました: {str(e)}")

# 処理1-1: メイン処理
def main(file_path, max_bgmlanenumber, no_sound_objnumber, start, end, lane_order, side_order):
    content, content_replaced = load_file(file_path)
    replace_count = process_bars(content, content_replaced, start, end, max_bgmlanenumber, no_sound_objnumber, lane_order, side_order)
    output_path = save_file(content_replaced, file_path, replace_count)
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
def save_file(content_replaced, file_path, replace_count):
    output_path = os.path.splitext(file_path)[0] + "_replaced" + os.path.splitext(file_path)[1]
    logging.info(f"ファイル出力開始: {output_path}")
    
    if os.path.exists(output_path):
        response = messagebox.askyesno("上書き確認", f"{output_path} は既に存在します。上書きしますか？")
        if not response:
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

# ノーツ置換
def replace_notes(lane_keys, lane_bgm, no_sound_objnumber):
    replace_count = 0  # 置換回数のカウンタ
    for key_idx, (lane_key_single, key_line_idx) in enumerate(lane_keys):
        lane_key_single_replaced = lane_key_single
        colon_idx = lane_key_single_replaced.index(':')
        obj_str = lane_key_single_replaced[colon_idx+1:].split()[0].split('%')[0].split('*')[0]
        if len(obj_str) % 2 != 0:
            logging.error(f"キーオブジェクト数が2で割り切れません: {lane_key_single}")
            raise Exception("キーオブジェクト数が2で割り切れません")
        lane_key_cutsize = len(obj_str) // 2
        logging.debug(f"キーオブジェクト数: {lane_key_cutsize} ({lane_key_single})")
        
        for i in range(lane_key_cutsize):
            key_objnumber = lane_key_single_replaced[colon_idx + (i*2)+1:colon_idx + (i*2)+3]
            if key_objnumber == no_sound_objnumber:
                a, b = i, lane_key_cutsize
                gcd_ab = gcd(a, b)
                a, b = a // gcd_ab, b // gcd_ab
                logging.debug(f"無音ノーツ検出: {key_objnumber} at position {i}")
                for bgm_idx, (lane_bgm_single, bgm_line_idx) in enumerate(lane_bgm):
                    lane_bgm_single_replaced = lane_bgm_single
                    colon_idx_bgm = lane_bgm_single_replaced.index(':')
                    bgm_obj_str = lane_bgm_single_replaced[colon_idx_bgm+1:].split()[0].split('%')[0].split('*')[0]
                    if len(bgm_obj_str) % 2 != 0:
                        logging.error(f"BGMオブジェクト数が2で割り切れません: {lane_bgm_single}")
                        raise Exception("BGMオブジェクト数が2で割り切れません")
                    lane_bgm_cutsize = len(bgm_obj_str) // 2
                    logging.debug(f"BGMオブジェクト数: {lane_bgm_cutsize} ({lane_bgm_single})")
                    for j in range(lane_bgm_cutsize):
                        bgm_objnumber = lane_bgm_single_replaced[colon_idx_bgm + (j*2)+1:colon_idx_bgm + (j*2)+3]
                        if bgm_objnumber != "00":
                            logging.debug(f"BGMノーツ検出: {bgm_objnumber} at position {j}")
                            c, d = j, lane_bgm_cutsize
                            gcd_cd = gcd(c, d)
                            c, d = c // gcd_cd, d // gcd_cd
                            if a == c and b == d:
                                key_pos_ratio = i / lane_key_cutsize
                                bgm_pos_ratio = j / lane_bgm_cutsize
                                logging.info(f"置換実行: キー位置{i}({key_objnumber}, {key_pos_ratio:.3f}) <-> BGM位置{j}({bgm_objnumber}, {bgm_pos_ratio:.3f})")
                                lane_key_single_replaced = (
                                    lane_key_single_replaced[:colon_idx + (i*2)+1] + 
                                    bgm_objnumber + 
                                    lane_key_single_replaced[colon_idx + (i*2)+3:]
                                )
                                replace_count += 1  # 置換が行われたらカウントを増やす
                                lane_bgm_single_replaced = (
                                    lane_bgm_single_replaced[:colon_idx_bgm + (j*2)+1] + 
                                    "00" + 
                                    lane_bgm_single_replaced[colon_idx_bgm + (j*2)+3:]
                                )
                                lane_bgm[bgm_idx] = (lane_bgm_single_replaced, bgm_line_idx)
                                break
                    else:
                        continue
                    break
        
        lane_keys[key_idx] = (lane_key_single_replaced, key_line_idx)
    
    return lane_keys, lane_bgm, replace_count

# コンテンツ更新
def update_content(content_replaced, lane_keys, lane_bgm):
    for set_key_single, key_index in lane_keys:
        content_replaced[key_index] = set_key_single + '\n'
        logging.debug(f"キー行更新: 行 {key_index}")
    for set_bgm_single, bgm_index in lane_bgm:
        content_replaced[bgm_index] = set_bgm_single + '\n'
        logging.debug(f"BGM行更新: 行 {bgm_index}")

# プログラム開始
if __name__ == "__main__":
    create_gui()