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
chores: fix typecheck test ## Run fixes, typecheck, and unit tests
	@echo ""
	@echo "✅ All checks passed!"

fix: ## Run lint fixes and formatting
	$(UV_RUN) ruff check --fix .
	$(UV_RUN) ruff check --select I --fix .
	$(UV_RUN) ruff format .

typecheck: ## Run basedpyright type checker
	$(UV) run --group dev basedpyright .

test: ## Run unit tests with testmon caching
	$(UV_RUN) --group dev pytest --testmon

test-all: ## Run unit tests without testmon caching
	$(UV_RUN) --group dev pytest

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
