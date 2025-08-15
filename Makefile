# -----------------------------------------------------------------------------
# mcp-builder Makefile
# -----------------------------------------------------------------------------
# Usage:
#   make help
#   make venv          # create .venv and install dev+docs extras
#   make install       # install package (editable) into .venv + sanity checks
#   make quality       # run all quality gates (lint + test)
#   make lint fmt lint-fix test  # run individual quality gates
#   make unit integration
#   make docs-serve    # live docs at http://127.0.0.1:8001
#   make build         # build wheel/sdist for PyPI
# -----------------------------------------------------------------------------

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

# --- Variables ---
PY_CMD ?= $(shell command -v python3.11 || command -v python3 || command -v python)
VENV     := .venv
BIN      := $(VENV)/bin
PYTHON   := $(BIN)/python
PIP      := $(BIN)/pip
PYTEST   := $(BIN)/pytest
RUFF     := $(BIN)/ruff
BLACK    := $(BIN)/black
MKDOCS   := $(BIN)/mkdocs

.PHONY: help venv install env-info lint fmt lint-fix unit integration test quality docs-serve docs-build build clean

# ----------------------------------------------------------------------------- #
# Help
# ----------------------------------------------------------------------------- #
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<TARGET>\033[0m\n\nTargets:\n"} /^[a-zA-Z0-9_.-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ----------------------------------------------------------------------------- #
# Environment / Setup
# ----------------------------------------------------------------------------- #
venv: $(VENV)/.installed ## Create .venv and install dev + docs extras

$(VENV)/.installed:
	@echo "🐍 Creating virtual environment..."
	$(PY_CMD) -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip wheel
	# Dev/docs extras for contributors
	$(PIP) install -e '.[dev,docs]'
	# Quick sanity checks
	$(PYTHON) -c "import mcp_builder, sys; print('mcp_builder OK ->', mcp_builder.__file__)"
	$(BIN)/mcp-builder --help >/dev/null
	touch $@
	@echo "✅ .venv ready. Activate with:  source $(VENV)/bin/activate"

# Install (editable) without forcing dev/docs extras again
install: ## Install package into .venv (editable) and verify CLI
	@echo "📦 Installing (editable) into $(VENV)..."
	@if [ ! -d "$(VENV)" ]; then $(MAKE) venv; fi
	$(PIP) install -e .
	# Verify import + console script
	$(PYTHON) -c "import mcp_builder, sys; print('mcp_builder OK ->', mcp_builder.__file__)"
	$(BIN)/mcp-builder --help >/dev/null
	@echo "✅ Installed. Run: . $(VENV)/bin/activate"

env-info: venv ## Print tool versions from the virtualenv
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Pip:    $$($(PIP) --version)"
	@echo "Ruff:   $$($(RUFF) --version || true)"
	@echo "Black:  $$($(BLACK) --version || true)"
	@echo "Pytest: $$($(PYTEST) --version || true)"

# ----------------------------------------------------------------------------- #
# Quality
# ----------------------------------------------------------------------------- #
lint: venv ## Run ruff linter
	@echo " linting with ruff..."
	$(RUFF) check .

fmt: venv ## Format with black
	@echo " auto-formatting with black..."
	$(BLACK) .

lint-fix: venv ## Auto-fix imports/format/pyupgrade via Ruff + Black
	# Reorder/clean imports (I), fix common issues, and modernize types (UP)
	$(RUFF) check . --fix
	# Ensure imports are sorted even inside function scopes
	$(RUFF) check . --select I --fix
	# Final formatting pass
	$(BLACK) .

unit: venv ## Run unit tests (skip if tests/unit missing)
	@echo " running unit tests..."
	@if [ -d tests/unit ]; then \
	  $(PYTEST) -q tests/unit ; \
	else \
	  echo "⚠️  Skipping: no tests/unit directory"; \
	fi

integration: venv ## Run integration tests (skip if tests/integration missing)
	@echo " running integration tests..."
	@if [ -d tests/integration ]; then \
	  $(PYTEST) -q tests/integration ; \
	else \
	  echo "⚠️  Skipping: no tests/integration directory"; \
	fi

test: venv ## Run all tests discovered (both suites if present)
	@echo " running all tests..."
	# If specific dirs exist, run both; otherwise run discovery at repo root
	@if [ -d tests/unit ] || [ -d tests/integration ]; then \
	  if [ -d tests/unit ]; then $(PYTEST) -q tests/unit ; else echo "⚠️  Skipping unit (missing)"; fi ; \
	  if [ -d tests/integration ]; then $(PYTEST) -q tests/integration ; else echo "⚠️  Skipping integration (missing)"; fi ; \
	else \
	  $(PYTEST) -q ; \
	fi

# ----------------------------------------------------------------------------- #
# Docs
# ----------------------------------------------------------------------------- #
docs-serve: venv ## Serve docs locally on :8001
	$(MKDOCS) serve -a 0.0.0.0:8001

docs-build: venv ## Build docs to ./site
	$(MKDOCS) build --strict

# ----------------------------------------------------------------------------- #
# Build & Clean
# ----------------------------------------------------------------------------- #
build: venv ## Build wheel and sdist into ./dist
	$(PYTHON) -m pip install --upgrade build
	$(PYTHON) -m build

clean: ## Remove build artifacts and caches
	@echo "🧹 Cleaning up..."
	rm -rf dist build *.egg-info .pytest_cache .mypy_cache site
	find . -type d -name '__pycache__' -exec rm -rf {} +
