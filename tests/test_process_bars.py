"""置換対象区間の境界のテスト。

区間は「開始位置 ≦ 小節 ≦ 終了位置」の閉区間で、終了位置の小節も処理対象に含む。
"""

import bms_core

# 小節1・小節2それぞれに BGM(ch01) とキー(ch11) の無音ノーツを1つずつ持つ譜面。
TWO_BARS = [
    "#00101:0100\n",
    "#00111:ZZ00\n",
    "#00201:0200\n",
    "#00211:ZZ00\n",
]


def _process(content, start, end):
    """content を処理し、(置換後の content, 置換件数) を返す。"""
    content_replaced = list(content)
    count = bms_core.process_bars(
        content,
        content_replaced,
        start,
        end,
        max_bgmlanenumber=8,
        no_sound_objnumber="ZZ",
        lane_order=bms_core.LANE_ORDER_OPTIONS[0],
        side_order=bms_core.SIDE_ORDER_OPTIONS[0],
    )
    return content_replaced, count


def test_end_bar_is_included():
    """終了位置の小節も処理される（閉区間）。"""
    replaced, count = _process(TWO_BARS, start=1, end=2)

    assert count == 2
    assert replaced == ["#00101:0000\n", "#00111:0100\n", "#00201:0000\n", "#00211:0200\n"]


def test_start_equal_to_end_processes_that_single_bar():
    """開始位置と終了位置が同じ場合、その1小節だけを処理する。"""
    replaced, count = _process(TWO_BARS, start=2, end=2)

    assert count == 1
    # 小節1は区間外なので変更されない
    assert replaced[:2] == ["#00101:0100\n", "#00111:ZZ00\n"]
    assert replaced[2:] == ["#00201:0000\n", "#00211:0200\n"]


def test_bars_outside_the_range_are_untouched():
    replaced, count = _process(TWO_BARS, start=1, end=1)

    assert count == 1
    assert replaced[2:] == ["#00201:0200\n", "#00211:ZZ00\n"]


def test_bar_999_can_be_processed():
    """小節999 は BMS の最大小節番号。閉区間なので end=999 で処理対象に入る。"""
    content = ["#99901:0100\n", "#99911:ZZ00\n"]

    replaced, count = _process(content, start=999, end=999)

    assert count == 1
    assert replaced == ["#99901:0000\n", "#99911:0100\n"]
