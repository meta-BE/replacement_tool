# replacement_tool リリース基盤 設計ドキュメント

- 日付: 2026-08-02
- 対象リポジトリ: `meta-BE/replacement_tool`
- 踏襲元: `meta-BE/bms-elsa`（Go/Wails）のバージョン管理（Makefile）と GitHub Actions ワークフロー

## 1. 目的

`replacement_tool`（Python/PyInstaller 製の GUI ツール）に、`bms-elsa` と同型の
「git tag を唯一の真実とするバージョン管理」と「タグ push を起点とした Windows exe の
自動ビルド・Release 公開」を導入する。現状はバージョンをファイル名に埋め込み、exe を
手動ビルドしてリポジトリにコミットしている運用を、tag 駆動の CI リリースへ移行する。

## 2. 踏襲元（bms-elsa）の要点

- **git tag が唯一の真実**。バージョンはソースにハードコードせず、ビルド時に注入
  （Go では `-ldflags "-X main.version=<tag>"`）。未注入時は `dev`。アプリ内タイトルに表示。
- **Makefile**: `VERSION` を git から算出（exact tag / `<tag>-<n>-g<hash>` / hash / `dev`、
  tracked 限定の `-dirty` 付き）。`build` に加え、`release-patch|minor|major` が
  「最新 `v*` を semver bump → 未push警告 → 確認プロンプト → `git tag` + `git push`」を実行。
- **GitHub Actions**（`.github/workflows/build-windows.yml`）: `v*` タグ push で起動 →
  `windows-latest` → ビルド → exe リネーム → 補助ファイル同梱 → ZIP 化 →
  `softprops/action-gh-release@v2` で Release にアップロード。

## 3. 制約・前提

- **PyInstaller はホスト OS 向けにしかビルドできない（クロスコンパイル不可）**。
  そのため Windows `.exe` の生成は CI（`windows-latest`）専用とし、ローカルの
  `make build` は mac ネイティブ（動作確認用）に限定する。bms-elsa の `build-windows`
  に相当するローカル Windows ビルドは提供しない。
- 依存は `tkinterdnd2`（唯一の外部依存）。PyInstaller では tkinterdnd2 が同梱する
  `tkdnd` バイナリを取り込むため `--collect-all tkinterdnd2` が必須。
- 現行 exe は Python 3.13（`python313.dll`）・console サブシステム・onefile 構成。
  CI もこれに合わせる。
- BMS ファイル入出力は Shift-JIS だが、本タスクはビルド/リリース基盤のみを対象とし
  アプリのロジックには手を入れない。

## 4. 決定事項（ユーザー承認済み）

1. **バージョン管理モデル**: tag=真実へ完全踏襲。ソースを安定名へリネームし、ビルド時に
   `_version.py` を生成して注入、GUI タイトルにバージョン表示、exe 名は固定。
2. **起動形式**: console（現行踏襲）。`--windowed` は使わない。
3. **Release アセット名**: バージョン入り ZIP 名（`無音ノーツ自動置換ツール_<tag>.zip`）。
4. **ローカル Windows ビルド**: 提供しない（CI 専用）。
5. **既存のコミット済み `.exe`**: git から削除する。
6. **`old_version/verX.Y.Z/` 運用**: 現状維持（今回は変更しない）。ただし配下の
   バイナリ（exe）は削除対象、`readme.txt` は残す。

## 5. コンポーネント設計

### 5.1 ソース構成（`replacement_tool.py`）

- `replacement_tool_ver1.1.0.py` を `replacement_tool.py` へ `git mv` でリネーム。
- import 群（現状 1〜13 行目）の直後に、バージョン読込を追加:

  ```python
  try:
      from _version import __version__
  except ImportError:
      __version__ = "dev"  # ビルド時に _version.py 未生成なら dev
  ```

- GUI タイトル（現状 21 行目 `root.title("無音ノーツ自動置換ツール")`）を変更:

  ```python
  root.title(f"無音ノーツ自動置換ツール {__version__}")
  ```

- `_version.py` はビルド時生成物であり、リポジトリにはコミットしない（`.gitignore`）。

### 5.2 Makefile

bms-elsa の Makefile を Python/PyInstaller 向けに翻訳する。

- **`VERSION`**: bms-elsa と同一ロジック（HEAD の `v*` exact tag →
  `<tag>-<n>-g<hash>` → 短縮 hash → `dev`、tracked 限定の `-dirty` サフィックス）。
  先頭の `v` は保持する（例 `v1.2.0`）。
- **`_gen-version`**（内部ターゲット）: `__version__ = "$(VERSION)"` を `_version.py` に書き出す。
- **`build`**: `_gen-version` に依存。ローカル（mac ネイティブ）動作確認用。
  `pyinstaller --onefile --collect-all tkinterdnd2 --name "無音ノーツ自動置換ツール" replacement_tool.py`
  （console）。
- **`release-patch` / `release-minor` / `release-major`**: bms-elsa と完全同型。
  内部 `_release` が最新 `v*` tag を semver bump、未 push コミットを警告、確認プロンプト
  （`[y/N]`）の後に `git tag <new>` + `git push origin <new>`。git 操作のみのため mac で動作。
- `.PHONY` に全ターゲットを登録。

### 5.3 GitHub Actions（`.github/workflows/build-windows.yml`）

- **トリガー**: `on.push.tags: ['v*']`
- **権限**: `permissions.contents: write`
- **ランナー**: `windows-latest`
- **ステップ**:
  1. `actions/checkout@v4`
  2. `actions/setup-python@v5`（`python-version: '3.13'`＝現行 exe に一致）
  3. `pip install pyinstaller tkinterdnd2`
  4. `_version.py` を `${{ github.ref_name }}` から生成（PowerShell で書き出し）
  5. `pyinstaller --onefile --collect-all tkinterdnd2 --name "無音ノーツ自動置換ツール" replacement_tool.py`
     → `dist/無音ノーツ自動置換ツール.exe`
  6. `readme.txt` を `dist/` へコピー
  7. `Compress-Archive` で `無音ノーツ自動置換ツール_${{ github.ref_name }}.zip`
     を作成（exe + readme.txt を同梱）
  8. `softprops/action-gh-release@v2` の `files` で ZIP を Release にアップロード

### 5.4 `.gitignore`（新規）

```
_version.py
build/
dist/
*.spec
```

### 5.5 既存バイナリの削除

- `git rm` 対象:
  - `無音ノーツ自動置換ツール_ver1.1.0.exe`
  - `old_version/ver1.0.0/無音ノーツ自動置換ツール.exe`
- `old_version/ver1.0.0/readme.txt` は残す。

### 5.6 `CLAUDE.md` 更新

- コマンド節: 実行コマンドを `python replacement_tool.py` に更新。ビルド/リリース手順
  （`make build` / `make release-patch|minor|major` / tag push → CI）を追記。
- ファイル名参照（`replacement_tool_ver1.1.0.py` → `replacement_tool.py`）を全面更新。
- バージョン管理の記述を「ファイル名埋め込み＋`old_version/` コピー」から
  「git tag=真実＋ビルド時 `_version.py` 注入」へ改訂。`old_version/` 運用は維持する旨を残す。

## 6. データフロー（リリース時）

```
make release-patch
  → 最新 tag を bump（例 v1.1.0 → v1.1.1）
  → 確認プロンプト [y/N]
  → git tag v1.1.1 && git push origin v1.1.1
      → GitHub Actions（build-windows.yml）起動
          → _version.py 生成（__version__ = "v1.1.1"）
          → pyinstaller で 無音ノーツ自動置換ツール.exe を生成（GUIタイトルに v1.1.1）
          → 無音ノーツ自動置換ツール_v1.1.1.zip（exe + readme.txt）
          → Release v1.1.1 にアセットとしてアップロード
```

## 7. エラーハンドリング・リスク

- **`_version.py` 未生成時**: import 失敗を `except ImportError` で捕捉し `dev` にフォールバック。
  `wails dev` 相当（ローカルで生成せず直接 `python replacement_tool.py`）でも起動可能。
- **日本語ファイル名（要検証）**: PyInstaller `--name` と `Compress-Archive` の ZIP 名に
  日本語を使う。windows-latest 上で文字化け・失敗しないか **検証項目**とする。問題が出た
  場合は ASCII 名（例 `replacement_tool`）へフォールバックする。
- **Python バージョン差異**: CI を 3.13 に固定して現行 exe と揃える。
- **未 push コミット時のリリース**: `_release` が警告表示（bms-elsa 同様、続行は可能）。

## 8. 検証項目

- `make build`（mac）で `_version.py` が生成され、GUI タイトルにバージョンが出ること。
- tag 未生成状態で `python replacement_tool.py` を起動し、タイトルが `dev` になること。
- `make release-patch` のバージョン算出・確認プロンプトが期待通り動くこと（push は任意）。
- テストタグ（例 `v0.0.1-test`）push で Actions が完走し、Release に
  `無音ノーツ自動置換ツール_<tag>.zip` が付き、中の exe が Windows で起動すること。
- ZIP 内 exe / readme.txt のファイル名が文字化けしないこと。

## 9. スコープ外

- アプリ本体のロジック（置換アルゴリズム、sjis 入出力、LN 対応等）の変更。
- `--windowed` 化などの起動形式変更。
- `old_version/` 運用そのものの見直し。
- macOS 向け配布物（`.app` / DMG）の作成。
