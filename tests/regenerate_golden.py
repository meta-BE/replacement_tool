"""golden ファイルを再生成する。make golden から呼ぶ。

生成後は必ず git diff を目視で確認すること。golden はレビューされて初めて意味を持つ。
"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bms_core
from golden_cases import EXPECTED_DIR, GOLDEN_CASES, INPUT_DIR


def main():
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    for name, input_name, params in GOLDEN_CASES:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / input_name
            shutil.copyfile(INPUT_DIR / input_name, work)
            output_path, count = bms_core.run_replacement(file_path=str(work), **params)
            (EXPECTED_DIR / f"{name}.bms").write_bytes(Path(output_path).read_bytes())
            print(f"{name}: {count}件置換 -> expected/{name}.bms")


if __name__ == "__main__":
    main()
