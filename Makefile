#!/usr/bin/env bash
# Makefile for spkezy - automatic speech recognition

UV := uv
UV_RUN := $(UV) run
INPUT_DEVICE ?=
DAEMON_INPUT_ARG := $(if $(INPUT_DEVICE),--input-device $(INPUT_DEVICE),)

.DEFAULT_GOAL := help

################################################################################
##@ Setup
setup: ## Install dependencies (CPU version)
	@if [ "$$(uname -s)" = "Darwin" ]; then \
		if ! command -v brew >/dev/null 2>&1; then \
			echo "❌ Homebrew is required on macOS. Install from https://brew.sh"; \
			exit 1; \
		fi; \
		echo "🍺 Installing macOS dependencies (portaudio, Maccy, Hammerspoon)..."; \
		brew install portaudio; \
		brew install --cask maccy hammerspoon; \
		UV_BIN="$$(command -v uv || echo uv)"; \
		mkdir -p "$$HOME/.hammerspoon"; \
		sed -e "s|__SPKEZY_PATH__|$$(pwd)|g" -e "s|__UV_BIN__|$$UV_BIN|g" docs/macos-hammerspoon.lua > "$$HOME/.hammerspoon/init.lua"; \
		echo ""; \
		echo "✅ macOS setup complete."; \
		echo "Next steps:"; \
		echo "  1) Open Hammerspoon and click Reload Config"; \
		echo "  2) Grant Accessibility permission to Hammerspoon"; \
		echo "  3) Start daemon with built-in mic: make daemon-mac"; \
		echo "  4) Use hotkey Ctrl+Option+' to start/stop dictation and auto-paste."; \
		echo ""; \
	fi
	$(UV) sync

setup-gpu: ## Install dependencies (GPU/CUDA 12.1)
	$(UV) sync --extra cuda

################################################################################
##@ Daemon Control
daemon: ## Start daemon
	$(UV_RUN) spkezy-daemon $(DAEMON_INPUT_ARG)

daemon-debug: ## Start daemon with debug output
	$(UV_RUN) spkezy-daemon --debug $(DAEMON_INPUT_ARG)

daemon-mac: ## Start daemon with MacBook Air microphone (device id 3)
	$(UV_RUN) spkezy-daemon --input-device 3

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

typecheck: ## Run ty type checker
	$(UV) run --group dev ty check

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
