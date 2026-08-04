"""改行コードの保持を検証する。バイト単位で比較する。"""

from pathlib import Path

import bms_core

PARAMS = dict(
    max_bgmlanenumber=8,
    no_sound_objnumber="ZZ",
    start=1,
    end=2,
    lane_order=bms_core.LANE_ORDER_OPTIONS[0],
    side_order=bms_core.SIDE_ORDER_OPTIONS[0],
)


def _run(tmp_path, raw):
    src = tmp_path / "t.bms"
    src.write_bytes(raw)
    output_path, _ = bms_core.run_replacement(file_path=str(src), **PARAMS)
    return Path(output_path).read_bytes()


def test_crlf_is_preserved(tmp_path):
    result = _run(tmp_path, b"#00101:0102\r\n#00111:ZZ00\r\n")

    assert result == b"#00101:0002\r\n#00111:0100\r\n"


def test_lf_is_preserved(tmp_path):
    result = _run(tmp_path, b"#00101:0102\n#00111:ZZ00\n")

    assert result == b"#00101:0002\n#00111:0100\n"


def test_missing_trailing_newline_is_preserved(tmp_path):
    result = _run(tmp_path, b"#00101:0102\n#00111:ZZ00")

    assert result == b"#00101:0002\n#00111:0100"


def test_untouched_lines_keep_their_newline(tmp_path):
    """置換対象外の行も改行が変わらないこと。"""
    result = _run(tmp_path, b"#TITLE T\r\n#00101:0102\r\n#00111:ZZ00\r\n")

    assert result == b"#TITLE T\r\n#00101:0002\r\n#00111:0100\r\n"


def test_cr_only_is_preserved(tmp_path):
    """旧 Mac 形式（CR 単独）の改行も保持されること。"""
    result = _run(tmp_path, b"#00101:0102\r#00111:ZZ00\r")

    assert result == b"#00101:0002\r#00111:0100\r"


def test_line_ending_helper_covers_all_cases():
    """_line_ending の全分岐（CRLF/LF/CR/改行なし）を直接検証する。"""
    assert bms_core._line_ending("#00101:0102\r\n") == "\r\n"
    assert bms_core._line_ending("#00101:0102\n") == "\n"
    assert bms_core._line_ending("#00101:0102\r") == "\r"
    assert bms_core._line_ending("#00101:0102") == ""
