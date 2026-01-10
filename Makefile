#!/usr/bin/env bash
# Makefile for spkezy - automatic speech recognition

UV := uv
UV_RUN := $(UV) run

.DEFAULT_GOAL := help

################################################################################
##@ Setup
setup: ## Install dependencies (CPU version)
	$(UV) sync

setup-gpu: ## Install dependencies (GPU/CUDA 12.1)
	$(UV) sync --extra cuda

################################################################################
##@ Daemon Control
daemon: ## Start daemon
	$(UV_RUN) spkezy-daemon

daemon-debug: ## Start daemon with debug output
	$(UV_RUN) spkezy-daemon --debug

shutdown: ## Shutdown daemon
	$(UV_RUN) spkezy shutdown

status: ## Check daemon status
	$(UV_RUN) spkezy status

################################################################################
##@ Recording
toggle: ## Toggle recording (start if idle, stop if recording)
	$(UV_RUN) spkezy toggle

start: ## Start recording
	$(UV_RUN) spkezy start

stop: ## Stop recording and transcribe
	$(UV_RUN) spkezy stop

stats: ## Show usage statistics and activity heatmap
	$(UV_RUN) spkezy stats

################################################################################
##@ Code Quality
lint: ## Run ruff linter (check only)
	$(UV_RUN) ruff check .

format: ## Run ruff formatter (check only)
	$(UV_RUN) ruff format --check .

fix: ## Run ruff linter and apply fixes
	$(UV_RUN) ruff check --fix .

fmt: ## Run ruff formatter and apply changes
	$(UV_RUN) ruff format .

check: ## Run all checks (lint + format check)
	$(UV_RUN) ruff check .
	$(UV_RUN) ruff format --check .

typecheck: ## Run basedpyright type checker
	$(UV) run --group dev basedpyright .

chores: check typecheck ## Run all code quality checks (lint, format, typecheck)
	@echo ""
	@echo "✅ All checks passed!"

################################################################################
##@ Utilities
.PHONY: help
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "spkezy - Automatic Speech Recognition\n====================================\n\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

list-devices: ## List available audio input devices
	$(UV_RUN) spkezy-daemon --list-devices

clean: ## Remove virtual environment and cache
	rm -rf .venv
	rm -rf __pycache__
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned up!"
