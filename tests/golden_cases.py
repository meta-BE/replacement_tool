"""golden テストの入力と実行パラメータの定義。テストと再生成スクリプトで共有する。"""

from pathlib import Path

import bms_core

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
INPUT_DIR = FIXTURE_DIR / "input"
EXPECTED_DIR = FIXTURE_DIR / "expected"

LANE_1234567 = bms_core.LANE_ORDER_OPTIONS[0]
LEFT_FIRST = bms_core.SIDE_ORDER_OPTIONS[0]
RIGHT_FIRST = bms_core.SIDE_ORDER_OPTIONS[1]

_BASE = dict(
    max_bgmlanenumber=8,
    no_sound_objnumber="ZZ",
    start=1,
    end=2,
    lane_order=LANE_1234567,
    side_order=LEFT_FIRST,
)

# (ケース名, 入力ファイル名, run_replacement のキーワード引数)
# 期待ファイルは expected/<ケース名>.bms
GOLDEN_CASES = [
    ("basic_7k", "basic_7k.bms", dict(_BASE)),
    ("resolution_mix", "resolution_mix.bms", dict(_BASE)),
    ("passthrough", "passthrough.bms", dict(_BASE)),
    ("14k_left_first", "14k.bms", dict(_BASE)),
    ("14k_right_first", "14k.bms", {**_BASE, "side_order": RIGHT_FIRST}),
    ("sjis_crlf", "sjis_crlf.bms", dict(_BASE)),
]
