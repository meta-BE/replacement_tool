.PHONY: build release-patch release-minor release-major _release _gen-version test typecheck golden

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
build: .venv _gen-version
	uv run pyinstaller --onefile --collect-all tkinterdnd2 --name "無音ノーツ自動置換ツール" replacement_tool.py

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

.venv: pyproject.toml
	uv sync --extra gui

test: .venv
	uv run pytest

typecheck: .venv
	pyright

golden: .venv
	uv run python tests/regenerate_golden.py
