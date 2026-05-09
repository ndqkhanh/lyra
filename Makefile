# Lyra — make targets.
# `make ci` mirrors CI (lint + typecheck + tests + evals smoke).

PACKAGES := packages/lyra-core \
            packages/lyra-skills \
            packages/lyra-mcp \
            packages/lyra-evals \
            packages/lyra-cli

PYTHON ?= python3

.PHONY: help install install-dev install-bin uninstall-bin binary \
        lint typecheck test test-fast evals ci clean distclean

help:
	@echo "Targets:"
	@echo "  install        Editable install of all packages."
	@echo "  install-dev    Editable install + dev extras (ruff, pyright, pytest)."
	@echo "  install-bin    Install + expose 'lyra' / 'ly' on \$$PATH (calls scripts/install-lyra.sh)."
	@echo "  uninstall-bin  Remove the 'lyra' / 'ly' symlinks from \$$PATH."
	@echo "  binary         Build a standalone single-file binary via PyInstaller (dist/lyra)."
	@echo "  lint           ruff check on all packages."
	@echo "  typecheck      pyright strict on lyra-core + lyra-cli."
	@echo "  test           Full pytest suite across all packages."
	@echo "  test-fast      Stops on first failure (-x)."
	@echo "  evals          Smoke eval over the golden corpus."
	@echo "  ci             lint + typecheck + test + evals (CI mirror)."
	@echo "  clean          Remove pytest/coverage artefacts."
	@echo "  distclean      clean + build artefacts."

install:
	$(PYTHON) -m pip install $(addprefix -e ,$(PACKAGES))

install-dev:
	$(PYTHON) -m pip install ruff pyright pytest pytest-cov PyYAML
	$(PYTHON) -m pip install $(addprefix -e ,$(PACKAGES))

install-bin:
	@PYTHON=$(PYTHON) ./scripts/install-lyra.sh

uninstall-bin:
	@PYTHON=$(PYTHON) ./scripts/install-lyra.sh --uninstall

binary:
	@command -v pyinstaller >/dev/null 2>&1 || $(PYTHON) -m pip install --user pyinstaller
	$(PYTHON) -m PyInstaller \
		--clean --noconfirm \
		--onefile \
		--name lyra \
		--collect-all lyra_cli \
		--collect-all lyra_core \
		--collect-all lyra_skills \
		--collect-all lyra_mcp \
		--collect-all lyra_evals \
		--hidden-import lyra_cli.commands.run \
		--hidden-import lyra_cli.commands.plan \
		--hidden-import lyra_cli.commands.doctor \
		--hidden-import lyra_cli.commands.session \
		--hidden-import lyra_cli.commands.retro \
		--hidden-import lyra_cli.commands.evals \
		--hidden-import lyra_cli.providers.openai_compatible \
		--hidden-import lyra_cli.providers.anthropic \
		--hidden-import lyra_cli.providers.gemini \
		packages/lyra-cli/src/lyra_cli/__main__.py
	@echo "binary built: $$(pwd)/dist/lyra"
	@echo "to install:  cp dist/lyra /opt/homebrew/bin/lyra && ln -sf /opt/homebrew/bin/lyra /opt/homebrew/bin/ly"

lint:
	$(PYTHON) -m ruff check $(PACKAGES)

typecheck:
	@if command -v pyright >/dev/null 2>&1 || $(PYTHON) -c "import pyright" 2>/dev/null; then \
		$(PYTHON) -m pyright \
			packages/lyra-core/src \
			packages/lyra-cli/src \
			packages/lyra-skills/src \
			packages/lyra-mcp/src \
			packages/lyra-evals/src; \
	else \
		echo "(pyright not installed; skipping — install via 'make install-dev')"; \
	fi

test:
	$(PYTHON) -m pytest packages -q

test-fast:
	$(PYTHON) -m pytest packages -q -x

evals:
	lyra evals --corpus golden --drift-gate 0.0

ci: lint typecheck test evals
	@echo "CI ok"

clean:
	rm -rf .pytest_cache .coverage htmlcov
	find . -type d \( -name __pycache__ -o -name "*.egg-info" \) -prune -exec rm -rf {} +

distclean: clean
	find packages -type d -name build -prune -exec rm -rf {} +
	find packages -type d -name dist -prune -exec rm -rf {} +
