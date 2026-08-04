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


def test_key_lane_table_matches_expected_channel_set():
    """各エントリのチャンネル集合が、キーレーンの正しい集合と完全一致すること。

    値の取り違え（例: "18" を無関係な "31" に打ち間違える等）を検出する。
    """
    expected_set = {
        "11", "12", "13", "14", "15", "18", "19",
        "21", "22", "23", "24", "25", "28", "29",
    }
    for key, lanes in bms_core.KEY_LANE_TABLE.items():
        assert set(lanes) == expected_set, key


def test_key_lane_table_matches_label_digit_order():
    """各エントリの並び順が、選択肢ラベル先頭の数字列から機械的に導出できること。

    ラベル（例 "4352617（中央レーンから順に置換１）"）の先頭7文字は 1〜7鍵の
    並び順を表す。鍵番号→チャンネルの対応は 1P: 1→11,2→12,...,7→19、
    2P: 1→21,2→22,...,7→29。SIDE_ORDER_OPTIONS[0]（左レーン→右レーン）なら
    1P7個→2P7個、SIDE_ORDER_OPTIONS[1]（右レーン→左レーン）なら
    2P7個→1P7個の順になる。LANE_ORDER_OPTIONS の値をハードコードした別リ
    ストは作らず、ラベル文字列から都度導出することで重複定義を避ける。
    """
    key_number_to_1p = {
        "1": "11", "2": "12", "3": "13", "4": "14",
        "5": "15", "6": "18", "7": "19",
    }
    key_number_to_2p = {
        "1": "21", "2": "22", "3": "23", "4": "24",
        "5": "25", "6": "28", "7": "29",
    }

    for lane_order in bms_core.LANE_ORDER_OPTIONS:
        digit_order = lane_order[:7]
        assert sorted(digit_order) == list("1234567"), lane_order  # 1〜7の並び替えであることの前提確認

        p1_lanes = [key_number_to_1p[d] for d in digit_order]
        p2_lanes = [key_number_to_2p[d] for d in digit_order]

        expected_left_to_right = p1_lanes + p2_lanes
        expected_right_to_left = p2_lanes + p1_lanes

        assert bms_core.KEY_LANE_TABLE[(lane_order, bms_core.SIDE_ORDER_OPTIONS[0])] == expected_left_to_right, lane_order
        assert bms_core.KEY_LANE_TABLE[(lane_order, bms_core.SIDE_ORDER_OPTIONS[1])] == expected_right_to_left, lane_order


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
