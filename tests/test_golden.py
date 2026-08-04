"""実ファイルを1往復させる golden テスト。

バイト単位で比較することで、文字コード・改行・行数・非対象チャンネルの保持を
1つの assert で同時に検証する。
"""

import shutil
from pathlib import Path

import pytest

import bms_core
from golden_cases import EXPECTED_DIR, GOLDEN_CASES, INPUT_DIR


@pytest.mark.parametrize(
    "name, input_name, params",
    GOLDEN_CASES,
    ids=[case[0] for case in GOLDEN_CASES],
)
def test_golden(name, input_name, params, tmp_path):
    work = tmp_path / input_name
    shutil.copyfile(INPUT_DIR / input_name, work)

    output_path, _ = bms_core.run_replacement(file_path=str(work), **params)

    actual = Path(output_path).read_bytes()
    expected = (EXPECTED_DIR / f"{name}.bms").read_bytes()
    assert actual == expected
