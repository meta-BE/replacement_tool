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


# --- 以下は brief 記載のケースに加えて追加したテスト ---
#
# replace_notes 内の BGM 探索は「BGM 行を先頭から順に走査し、各行内も位置0から
# 順に走査して、最初に見つかった一致候補を採用する」という for-else による
# 二重ループ制御になっている（bms_core.py 185-220行目）。この走査順の性質は
# brief の既存10ケースでは直接検証されていない。
# （test_consumed_bgm_note_is_not_reused は「消費済みなので次の行に移る」ケースだが、
# 　1本目の行が既に "00" のみで候補自体が存在しない状況であり、
# 　「候補はあるが分数が一致しないため走査を継続する」経路は通っていない。）
# 実装が誤って最後の一致を採用する、または行をまたいだ継続走査が壊れる、
# といった変更が入っても既存10ケースでは検知できない可能性があるため、
# その2つの経路を明示的に固定する。


def test_first_matching_bgm_line_wins_when_multiple_lines_match():
    # BGM 行1・行2 とも位置0 (0/1) に非ゼロノーツを持つ。
    # 走査は bgm_idx=0 から順に行われるため、行1が採用され行2は変更されない。
    keys, bgm, count = _run(
        ["#00111:ZZ00"],
        ["#00101:0100", "#00102:0200"],
    )

    assert keys == ["#00111:0100"]
    assert bgm == ["#00101:0000", "#00102:0200"]
    assert count == 1


def test_scan_continues_past_non_matching_candidate_to_next_bgm_line():
    # BGM 行1の位置1 (1/2) には非ゼロノーツ "01" があるが、
    # キーが求めるのは位置0 (0/1) なので分数不一致でスキップされ、
    # 行1を最後まで走査したのち行2 (位置0, 0/1) で一致する。
    keys, bgm, count = _run(
        ["#00111:ZZ00"],
        ["#00101:0001", "#00102:0200"],
    )

    assert keys == ["#00111:0200"]
    assert bgm == ["#00101:0001", "#00102:0000"]
    assert count == 1
