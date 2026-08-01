# replacement_tool リリース基盤 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** bms-elsa 同型の「git tag=真実」バージョン管理（Makefile）と、タグ push 起点の Windows exe 自動ビルド・Release 公開（GitHub Actions）を replacement_tool に導入する。

**Architecture:** ソースを安定名 `replacement_tool.py` へリネームし、ビルド時に `_version.py` を生成して GUI タイトルへバージョン注入。ローカルは Makefile（mac ネイティブ動作確認＋semver リリース操作）、Windows exe は `v*` タグ push で `windows-latest` の CI が PyInstaller（onefile/console）でビルドし ZIP を Release へ添付する。

**Tech Stack:** Python 3.13, PyInstaller (onefile, console), tkinterdnd2, GNU Make, GitHub Actions (windows-latest), softprops/action-gh-release@v2。

## Global Constraints

以下は全タスク共通の要件（spec からの転記）。各タスクの要件はこれを暗黙に含む。

- Python は CI で **3.13** に固定（現行 exe の `python313.dll` に一致）。
- PyInstaller は **`--onefile --collect-all tkinterdnd2`**、**console**（`--windowed` は使わない）。
- PyInstaller の `--name` は **`無音ノーツ自動置換ツール`**（exe 名固定）。
- Release ZIP 名は **`無音ノーツ自動置換ツール_<tag>.zip`**。
- `VERSION` は **先頭の `v` を保持**（例 `v1.2.0`）。tag 未注入時は `dev`。
- **PyInstaller はクロスコンパイル不可**。ローカルで Windows exe は作らない（CI 専用）。
- アプリ本体のロジック（置換・sjis 入出力等）は変更しない。編集は import 直後の版読込追加と title 行のみ。
- すべての出力・コミットメッセージは**日本語**。各コミット末尾に
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` を付ける。
- 作業ブランチは `release-pipeline`（既に作成済み・spec コミット済み）。

## File Structure

| ファイル | 区分 | 責務 |
|----------|------|------|
| `.gitignore` | 新規 | ビルド生成物（`_version.py`, `build/`, `dist/`, `*.spec`）を除外 |
| `replacement_tool.py` | リネーム+編集 | 旧 `replacement_tool_ver1.1.0.py`。版読込と GUI タイトル表示を追加 |
| `Makefile` | 新規 | `VERSION` 算出・`_gen-version`・`build`・`release-*` |
| `.github/workflows/build-windows.yml` | 新規 | `v*` タグ→windows-latest→PyInstaller→ZIP→Release |
| `CLAUDE.md` | 編集 | コマンド・ファイル名参照・バージョン管理記述の更新 |
| `無音ノーツ自動置換ツール_ver1.1.0.exe` | 削除 | コミット済みバイナリを git から除去 |
| `old_version/ver1.0.0/無音ノーツ自動置換ツール.exe` | 削除 | 同上（`readme.txt` は残す） |

タスク順は各タスクの検証が後続タスクに依存しないよう並べてある（1→5）。

---

### Task 1: `.gitignore` 追加とコミット済みバイナリ削除

**Files:**
- Create: `.gitignore`
- Delete: `無音ノーツ自動置換ツール_ver1.1.0.exe`, `old_version/ver1.0.0/無音ノーツ自動置換ツール.exe`

**Interfaces:**
- Consumes: なし
- Produces: `.gitignore` が `_version.py` を除外する（Task 3 が `_version.py` を生成しても混入しない前提を与える）

- [ ] **Step 1: `.gitignore` を作成**

```
_version.py
build/
dist/
*.spec
```

- [ ] **Step 2: コミット済み exe を git と作業ツリーから削除**

```bash
git rm "無音ノーツ自動置換ツール_ver1.1.0.exe" "old_version/ver1.0.0/無音ノーツ自動置換ツール.exe"
```

- [ ] **Step 3: 検証（exe が追跡外・readme は残存）**

Run:
```bash
git ls-files | grep -E '\.exe$'; echo "exit=$?"; git ls-files old_version/
```
Expected: `.exe` の行が 0 件（`exit=1`）。`old_version/ver1.0.0/readme.txt` は一覧に残る。

- [ ] **Step 4: コミット**

```bash
git add .gitignore
git commit -m "$(cat <<'EOF'
chore: ビルド生成物を gitignore し、コミット済み exe を削除

exe は CI が Release で配布するため、リポジトリでは追跡しない。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: ソースを `replacement_tool.py` へリネームし版注入に対応

**Files:**
- Rename: `replacement_tool_ver1.1.0.py` → `replacement_tool.py`
- Modify: `replacement_tool.py`（import 直後に版読込、`create_gui` の title 行）

**Interfaces:**
- Consumes: `_version.py` の `__version__`（存在すれば）。未生成時は `dev`
- Produces: 実行エントリ `replacement_tool.py`（Makefile / CI が PyInstaller の入力として参照する固定名）

- [ ] **Step 1: `git mv` でリネーム**

```bash
git mv replacement_tool_ver1.1.0.py replacement_tool.py
```

- [ ] **Step 2: import 直後に版読込ブロックを追加**

`replacement_tool.py` の tkinterdnd2 の try/except（`exit(1)` で終わるブロック）の直後、`# ロギングの設定` コメントの前に以下を挿入する。

適用する Edit:
- old_string:
```python
    print("エラー: tkinterdnd2 ライブラリが見つかりません。インストールしてください: pip install tkinterdnd2")
    exit(1)

# ロギングの設定
```
- new_string:
```python
    print("エラー: tkinterdnd2 ライブラリが見つかりません。インストールしてください: pip install tkinterdnd2")
    exit(1)

# バージョン: ビルド時に Makefile / CI が _version.py を生成して注入する。
# ローカルで直接実行するなど未生成の場合は dev にフォールバックする。
try:
    from _version import __version__
except ImportError:
    __version__ = "dev"

# ロギングの設定
```

- [ ] **Step 3: GUI タイトルにバージョンを表示**

適用する Edit:
- old_string: `    root.title("無音ノーツ自動置換ツール")`
- new_string: `    root.title(f"無音ノーツ自動置換ツール {__version__}")`

- [ ] **Step 4: 検証（構文＋挿入内容）**

Run:
```bash
python3 -m py_compile replacement_tool.py && echo "compile-ok"
grep -n '__version__\|from _version' replacement_tool.py
```
Expected: `compile-ok` が出る（構文エラーなし）。grep で版読込ブロック（`from _version import __version__` / `__version__ = "dev"`）と title 行 `f"無音ノーツ自動置換ツール {__version__}"` が表示される。

> 注: GUI 起動や `import replacement_tool` はディスプレイと tkinterdnd2 実体を要し、tkinterdnd2 未導入時は先頭で `exit(1)` するため、検証は `py_compile`＋`grep` の静的チェックとする。

- [ ] **Step 5: コミット**

```bash
git add replacement_tool.py
git commit -m "$(cat <<'EOF'
refactor: 安定名 replacement_tool.py へ変更し版を注入表示

ビルド時生成の _version.py から __version__ を読み、GUI タイトルに表示する。
未生成時は dev にフォールバック。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Makefile 追加（VERSION 算出・build・release-*）

**Files:**
- Create: `Makefile`

**Interfaces:**
- Consumes: `replacement_tool.py`（`build` の PyInstaller 入力）
- Produces: `_version.py`（`_gen-version` が `__version__ = "<VERSION>"` を書き出す。Task 2 の版読込が消費する形式）

- [ ] **Step 1: `Makefile` を作成**

```makefile
.PHONY: build release-patch release-minor release-major _release _gen-version

# VERSION は git tag を真実とする。
# - HEAD に v* tag があればそれ (semver 順でタイ解決)
# - HEAD が tag より進んでいれば <tag>-<n>-g<hash>
# - tag が一切なければ短縮 hash
# - 非 git/エラー時は dev
# dirty 判定は tracked ファイル限定 (git describe --dirty 互換)
VERSION := $(shell \
	DIRTY=$$(if [ -n "$$(git status --porcelain --untracked-files=no 2>/dev/null)" ]; then echo "-dirty"; fi); \
	T_EXACT=$$(git tag --points-at HEAD --list 'v*' --sort=-version:refname 2>/dev/null | head -1); \
	if [ -n "$$T_EXACT" ]; then \
		echo "$$T_EXACT$$DIRTY"; \
	else \
		T_BASE=$$(git tag --merged HEAD --list 'v*' --sort=-version:refname 2>/dev/null | head -1); \
		HASH=$$(git rev-parse --short HEAD 2>/dev/null); \
		if [ -z "$$HASH" ]; then echo dev; \
		elif [ -n "$$T_BASE" ]; then \
			N=$$(git rev-list --count $$T_BASE..HEAD 2>/dev/null); \
			echo "$$T_BASE-$$N-g$$HASH$$DIRTY"; \
		else \
			echo "$$HASH$$DIRTY"; \
		fi; \
	fi)

# _version.py はビルド時生成物 (gitignore)。GUI タイトル表示に使う。
_gen-version:
	@echo '__version__ = "$(VERSION)"' > _version.py

# ローカル (mac ネイティブ) 動作確認用。Windows exe は CI で生成する。
build: _gen-version
	pyinstaller --onefile --collect-all tkinterdnd2 --name "無音ノーツ自動置換ツール" replacement_tool.py

release-patch:
	@$(MAKE) _release BUMP=patch

release-minor:
	@$(MAKE) _release BUMP=minor

release-major:
	@$(MAKE) _release BUMP=major

_release:
	@if [ -n "$$(git log origin/main..HEAD --oneline 2>/dev/null)" ]; then \
		echo "警告: 未プッシュのコミットがあります:"; \
		git log origin/main..HEAD --oneline; \
		echo ""; \
	fi
	@LATEST=$$(git tag --list 'v*' --sort=-version:refname 2>/dev/null | head -1); \
	LATEST=$${LATEST:-v0.0.0}; \
	MAJOR=$$(echo $$LATEST | sed 's/^v//' | cut -d. -f1); \
	MINOR=$$(echo $$LATEST | sed 's/^v//' | cut -d. -f2); \
	PATCH=$$(echo $$LATEST | sed 's/^v//' | cut -d. -f3); \
	if [ "$(BUMP)" = "patch" ]; then \
		PATCH=$$((PATCH + 1)); \
	elif [ "$(BUMP)" = "minor" ]; then \
		MINOR=$$((MINOR + 1)); \
		PATCH=0; \
	elif [ "$(BUMP)" = "major" ]; then \
		MAJOR=$$((MAJOR + 1)); \
		MINOR=0; \
		PATCH=0; \
	fi; \
	NEW_VERSION="v$$MAJOR.$$MINOR.$$PATCH"; \
	echo "$$LATEST → $$NEW_VERSION"; \
	printf "リリースしますか？ [y/N] "; \
	read CONFIRM; \
	if [ "$$CONFIRM" = "y" ] || [ "$$CONFIRM" = "Y" ]; then \
		git tag $$NEW_VERSION && \
		git push origin $$NEW_VERSION && \
		echo "$$NEW_VERSION をpushしました。GitHub Actionsでビルドが開始されます。"; \
	else \
		echo "キャンセルしました。"; \
	fi
```

> 注: レシピ行のインデントは**タブ**（スペース不可）。

- [ ] **Step 2: 検証 A（`_gen-version` が版を書き出す）**

Run:
```bash
make _gen-version && cat _version.py
```
Expected: `_version.py` に `__version__ = "<短縮hash>"`（作業ツリーが未コミット変更を含む間は `<短縮hash>-dirty`）が書かれる。タグ未作成のため hash 形式になる。`_version.py` は gitignore 済みで追跡されない。

- [ ] **Step 3: 検証 B（release のバージョン算出とキャンセルが安全に動く）**

Run:
```bash
printf 'n\n' | make release-patch; echo "tags=[$(git tag --list 'v*')]"
```
Expected: `v0.0.0 → v0.0.1` が表示され、最後に `キャンセルしました。` が出る。`tags=[]`（タグは作成されない）。未プッシュコミットがあれば冒頭に警告が出るのは正常。

- [ ] **Step 4: コミット**

```bash
git add Makefile
git commit -m "$(cat <<'EOF'
build: バージョン管理とリリース用 Makefile を追加

bms-elsa を踏襲し、git tag を真実とする VERSION 算出、_version.py 生成、
mac ネイティブ build、semver 自動 bump による release-patch/minor/major を提供。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: GitHub Actions ワークフロー追加

**Files:**
- Create: `.github/workflows/build-windows.yml`

**Interfaces:**
- Consumes: `replacement_tool.py`, `readme.txt`, タグ名 `github.ref_name`
- Produces: Release アセット `無音ノーツ自動置換ツール_<tag>.zip`

- [ ] **Step 1: ワークフローを作成**

```yaml
name: Build Windows

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: pip install pyinstaller tkinterdnd2

      - name: Generate _version.py
        shell: pwsh
        env:
          TAG: ${{ github.ref_name }}
        run: Set-Content -Path _version.py -Value "__version__ = `"$env:TAG`"" -Encoding utf8

      - name: Build exe
        run: pyinstaller --onefile --collect-all tkinterdnd2 --name "無音ノーツ自動置換ツール" replacement_tool.py

      - name: Copy readme
        shell: pwsh
        run: Copy-Item readme.txt dist/readme.txt

      - name: Create ZIP
        shell: pwsh
        env:
          TAG: ${{ github.ref_name }}
        run: Compress-Archive -Path "dist/無音ノーツ自動置換ツール.exe", "dist/readme.txt" -DestinationPath "dist/無音ノーツ自動置換ツール_$env:TAG.zip"

      - name: Upload to Release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/無音ノーツ自動置換ツール_${{ github.ref_name }}.zip
```

> 設計上の要点: `_version.py` 生成と ZIP 名はタグ名を **env 経由**で渡し、スクリプトインジェクションを避ける。PowerShell 二重引用符内の `` `" `` は内側のダブルクオートのエスケープで、`__version__ = "v1.2.0"` を生成する。

- [ ] **Step 2: 検証（YAML が妥当に解析できる）**

Run:
```bash
python3 -c "import yaml,sys; d=yaml.safe_load(open('.github/workflows/build-windows.yml')); assert d['on']['push']['tags']==['v*']; assert d['jobs']['build']['runs-on']=='windows-latest'; print('yaml-ok')"
```
Expected: `yaml-ok`。

> `PyYAML` 未導入なら `pip install pyyaml` を一時的に行うか、`python3 -c "import yaml"` で不在を確認のうえ、代替として `grep -nE 'runs-on: windows-latest|tags:|action-gh-release' .github/workflows/build-windows.yml` で主要行の存在を確認する。実際のビルド完走はテストタグ push（検証項目、ユーザー判断）で確認する。

- [ ] **Step 3: コミット**

```bash
git add .github/workflows/build-windows.yml
git commit -m "$(cat <<'EOF'
ci: v* タグで Windows exe をビルドし Release へ公開

windows-latest で PyInstaller (onefile/console) により exe を生成し、
readme と共に 無音ノーツ自動置換ツール_<tag>.zip として Release に添付する。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: CLAUDE.md 更新

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: なし
- Produces: なし（ドキュメント整合のみ）

- [ ] **Step 1: コマンド節を更新**

`## コマンド` のコードブロックを次に置換する（実行コマンドを新ファイル名にし、ビルド/リリース手順を追記）。

適用する Edit:
- old_string:
```bash
# 依存ライブラリのインストール（tkinterdnd2 が唯一の外部依存）
pip install tkinterdnd2

# 実行（GUI/ディスプレイが必要）
python replacement_tool_ver1.1.0.py
```
- new_string:
```bash
# 依存ライブラリのインストール（tkinterdnd2 が唯一の外部依存）
pip install tkinterdnd2

# 実行（GUI/ディスプレイが必要）
python replacement_tool.py

# ローカル動作確認ビルド（mac ネイティブ。要 pyinstaller）
make build

# リリース（最新 v* タグを semver bump してタグ push → CI が Windows exe をビルド）
make release-patch   # / release-minor / release-major
```

- [ ] **Step 2: exe とビルドに関する記述を更新**

`## コマンド` 直後の箇条書き（テスト不在・配布 exe に関する 2 行）を次に置換する。

適用する Edit:
- old_string:
```
- テスト・Lint・ビルド設定は存在しない（単一スクリプト構成）。
- 配布用 `.exe`（`無音ノーツ自動置換ツール_ver1.1.0.exe`）は PyInstaller によるビルド成果物。ビルドコマンドはリポジトリに含まれていない。
```
- new_string:
```
- テスト・Lint 設定は存在しない（単一スクリプト構成）。
- 配布用 `.exe` は PyInstaller（onefile/console）でビルドする。`v*` タグ push を起点に GitHub Actions（`.github/workflows/build-windows.yml`, windows-latest）が exe をビルドし、`無音ノーツ自動置換ツール_<tag>.zip` を Release に添付する。exe はリポジトリにコミットしない。
- PyInstaller はクロスコンパイル不可のため、Windows exe の生成は CI 専用。`make build` は mac ネイティブの動作確認用。
```

- [ ] **Step 3: アーキテクチャ節のエントリファイル名を更新**

`replacement_tool_ver1.1.0.py` という参照を全て `replacement_tool.py` に置換する。

適用する Edit（`replace_all: true`）:
- old_string: `replacement_tool_ver1.1.0.py`
- new_string: `replacement_tool.py`

- [ ] **Step 4: バージョン管理の記述を更新**

`## 重要な制約・慣習` の最終行を、tag 駆動の版管理へ改訂する。

適用する Edit:
- old_string: `- バージョン管理は `old_version/verX.Y.Z/` に旧版一式をコピーして残す運用。`
- new_string（2 行の箇条書き。行間は実際の改行）:
```
- バージョンは git tag（`v*`）を真実とし、ビルド時に `_version.py`（`__version__`）を生成して GUI タイトルに表示する。未生成時は `dev`。
- 旧版アーカイブとして `old_version/verX.Y.Z/` にコピーを残す運用は継続する（ただし exe バイナリはコミットしない）。
```

- [ ] **Step 5: 検証（旧名が残っていない・新記述が入っている）**

Run:
```bash
grep -n 'replacement_tool_ver1.1.0.py' CLAUDE.md; echo "old-ref-exit=$?"
grep -n 'make release\|build-windows.yml\|_version.py' CLAUDE.md
```
Expected: 旧名 grep は 0 件（`old-ref-exit=1`）。2 つ目で `make release` / `build-windows.yml` / `_version.py` を含む行が表示される。

- [ ] **Step 6: コミット**

```bash
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: CLAUDE.md を新しいビルド/リリース構成へ更新

実行コマンドを replacement_tool.py に更新し、make build / release-* と
CI による Windows exe リリース、tag 駆動の版管理を反映。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## リリース後の任意検証（ユーザー判断・スコープ外の実行）

- テストタグ（例 `v0.0.1-test`）を push し、Actions が完走して Release に
  `無音ノーツ自動置換ツール_<tag>.zip` が付くこと、ZIP 内 exe が Windows で起動し、
  タイトルにタグ名が表示され、ファイル名が文字化けしないことを確認する。
- 問題（特に日本語ファイル名の文字化け）が出た場合は、`--name` と ZIP 名を
  ASCII（例 `replacement_tool`）へフォールバックする。
