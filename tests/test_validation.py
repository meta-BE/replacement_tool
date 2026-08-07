"""入力バリデーションとドロップパス解析のテスト。"""

import pytest

import bms_core

VALID = dict(
    file_path="/tmp/a.bms",
    max_bgmlanenumber="8",
    no_sound_objnumber="ZZ",
    start="1",
    end="2",
)


def _call(**overrides):
    params = {**VALID, **overrides}
    return bms_core.validate_params(**params)


def test_valid_params_return_ints():
    assert _call() == (8, 1, 2)


@pytest.mark.parametrize("field", ["file_path", "max_bgmlanenumber", "no_sound_objnumber", "start", "end"])
def test_empty_field_is_rejected(field):
    with pytest.raises(ValueError, match="すべての項目を入力してください"):
        _call(**{field: ""})


def test_non_numeric_max_bgmlanenumber_is_rejected():
    with pytest.raises(ValueError, match="BGMレーン最大位置 は整数で入力してください"):
        _call(max_bgmlanenumber="abc")


def test_negative_value_is_rejected_as_non_integer():
    """'-1' は isdigit() が False のため、範囲エラーではなく整数エラーになる。"""
    with pytest.raises(ValueError, match="開始位置 は整数で入力してください"):
        _call(start="-1")


def test_out_of_range_value_is_rejected():
    with pytest.raises(ValueError, match="終了小節 は0～999の範囲で入力してください"):
        _call(end="1000")


@pytest.mark.parametrize("value", ["Z", "ZZZ", "Z-", "あ"])
def test_malformed_silent_note_is_rejected(value):
    with pytest.raises(ValueError, match="無音ノーツ定義は2桁の数字またはアルファベットで入力してください"):
        _call(no_sound_objnumber=value)


def test_silent_note_with_trailing_newline_is_rejected():
    """Python の `$` は文字列末尾の改行の直前にもマッチするため、`re.match` では
    "ZZ\\n" が2桁として受理されてしまう。文字列全体の一致を要求する必要がある。
    """
    with pytest.raises(ValueError, match="無音ノーツ定義は2桁の数字またはアルファベットで入力してください"):
        _call(no_sound_objnumber="ZZ\n")


def test_zero_zero_silent_note_is_rejected():
    with pytest.raises(ValueError, match="無音ノーツ定義に '00' は使用できません"):
        _call(no_sound_objnumber="00")


def test_start_must_be_less_than_end():
    with pytest.raises(ValueError, match="開始位置は終了位置より小さくなければなりません"):
        _call(start="5", end="5")


def test_lowercase_silent_note_is_accepted():
    """62進拡張のため大文字・小文字を区別する。小文字も有効な定義。"""
    assert _call(no_sound_objnumber="zz") == (8, 1, 2)


def test_numeric_silent_note_is_accepted():
    """無音ノーツ定義は英字専用ではなく、'00'以外の数字2桁も有効（brief未カバーの穴を補うテスト）。"""
    assert _call(no_sound_objnumber="12") == (8, 1, 2)


def test_parse_dropped_path_plain():
    assert bms_core.parse_dropped_path("/a/b.bms") == "/a/b.bms"


def test_parse_dropped_path_single_braced():
    """空白を含むパスは中括弧で囲まれて渡される。"""
    assert bms_core.parse_dropped_path("{/a/b c.bms}") == "/a/b c.bms"


def test_parse_dropped_path_takes_first_of_multiple():
    assert bms_core.parse_dropped_path("{/a/1.bms} {/a/2.bms}") == "/a/1.bms"


def test_parse_dropped_path_empty():
    assert bms_core.parse_dropped_path("") == ""
