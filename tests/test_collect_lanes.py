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
