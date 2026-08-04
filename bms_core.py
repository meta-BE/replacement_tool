"""BMS 譜面の無音ノーツ置換ロジック。GUI には依存しない。"""

import logging
import os
from math import gcd


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
    key_lanes = KEY_LANE_TABLE[(lane_order, side_order)]

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
