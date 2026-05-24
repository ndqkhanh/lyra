.PHONY: help install test lint clean

PY ?= python3
VENV ?= .venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip
PYTEST := $(VENV_BIN)/pytest

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

$(VENV):
	$(PY) -m venv $(VENV)
	$(PIP) install -U pip wheel

install: $(VENV) ## Install harness_core editable with dev deps
	$(PIP) install -e '.[dev]'

test: install ## Run unit tests
	$(PYTEST) -q tests

lint: install ## Lint
	$(VENV_BIN)/ruff check src tests

clean: ## Remove caches and venv
	rm -rf $(VENV) .pytest_cache .ruff_cache .mypy_cache
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

.DEFAULT_GOAL := help
