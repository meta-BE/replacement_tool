# TODO

テスト基盤の導入（2026-08-04）中に見つかった既知の問題を記録している。

2026-08-07 に方針を変更し、記録済みの項目は原則として修正する運用にした
（それ以前は「記録するが修正しない」方針だった）。以下は規模や性質の都合で
意図的に残している項目。

## 未対応

1. **LN（`#LNOBJ`）が未対応**
   `#LNOBJ` 方式の LN は終点オブジェクトを RDM 用チャンネルではなく通常のキーチャンネル
   `11`-`29` に直接配置するため、無音ノーツと誤認して移動すると LN が破損し得る。
   RDM 記法（`#LNTYPE 1`、チャンネル `5x`/`6x`）はチャンネル的に編集対象外だが動作は未検証。

   対応するには置換アルゴリズムに「LN 終点を識別する」概念の追加が必要で、
   他の修正とは規模が異なるため未着手。readme.txt にも未対応と明記している。

2. **`.github/workflows/build-windows.yml` が pip ベースのまま**
   `test.yml` は uv（`astral-sh/setup-uv`）に寄せてあるが、build-windows.yml は
   `actions/setup-python` + `pip install` のまま。将来 uv へ揃える余地がある。
   バグではなく改善余地。

## 対応済み（2026-08-07）

以下は修正済み。詳細は各コミットを参照。

- `replace_notes` がデータ部の空な行で `IndexError` になる
- 「BGMレーン最大位置」の空欄が入力必須エラーになり、本数無制限にできない
  （`0` は「0本まで」の意味として維持）
- 編集した行の行末の空白が失われる
- `validate_params` の `no_sound_objnumber.lower()` が無意味
- `validate_params` の正規表現 `$` が末尾改行を許す
- 小節 999 が構造的に処理できない（置換対象区間を閉区間に変更して解消）
- `validate_params` の `num < 0` が到達不能
- `replacement_tool.py` の `root.entries` / `tk._default_root` によるグローバル状態
- `build-windows.yml` の artifact 名がスラッシュを含むブランチ名で失敗する
  （あわせて Node 20 ランタイムの action を Node 24 へ更新）
