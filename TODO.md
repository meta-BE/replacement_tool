# TODO

テスト基盤の導入（2026-08-04）中に見つかった既知の問題。いずれも未修正。

## 既知バグ

1. **`replace_notes` がデータ部の空な行で `IndexError` になる**
   `bms_core.py` の `obj_str = ...split()[0]` は、コロン以降が空の行（`#00111:`）で
   `IndexError: list index out of range` を送出する。キー側・BGM側の両方に同じ問題がある。

2. **「BGMレーン最大位置」に `0` を入れると黙って何も置換されない**
   `collect_bgm_lane` の `len(lane_bgm) < max_bgmlanenumber` により BGM 行を1本も収集せず、
   `process_single_bar` の `if lane_bgm:` が偽になって置換が0件で終わる。
   `validate_params` は `0` を許可しているため、エラーも警告も出ない。

3. **編集した行の行末の空白が失われる**
   `collect_bgm_lane` / `collect_key_lanes` が `line.strip()` で収集し、`update_content` が
   それを書き戻すため、置換対象になった行に限り行末の空白が消える。

4. **`validate_params` の `no_sound_objnumber.lower()` が無意味**
   正規表現 `^[0-9A-Za-z]{2}$` が大文字・小文字の両方を含むため、`.lower()` は結果を変えない。
   現行の振る舞いを維持するために残している。

5. **LN（`#LNOBJ`）が未対応**
   `#LNOBJ` 方式の LN は終点オブジェクトを RDM 用チャンネルではなく通常のキーチャンネル
   `11`-`29` に直接配置するため、無音ノーツと誤認して移動すると LN が破損し得る。
   RDM 記法（`#LNTYPE 1`、チャンネル `5x`/`6x`）はチャンネル的に編集対象外だが動作は未検証。

## 改善余地

6. `.github/workflows/build-windows.yml` は pip ベースのまま。将来 uv へ寄せる余地がある。
