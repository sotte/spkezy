#!/usr/bin/env bash
# Makefile for spk - automatic speech recognition

VENV := .venv
PYTHON := $(VENV)/bin/python
UV := uv

.DEFAULT_GOAL := help

################################################################################
##@ Setup
setup: ## Install dependencies (CPU version)
	$(UV) sync --extra cpu

setup-gpu: ## Install dependencies (GPU/CUDA 12.1)
	$(UV) sync --extra cuda

################################################################################
##@ Daemon Control
daemon: ## Start daemon
	$(PYTHON) daemon.py

daemon-debug: ## Start daemon with debug output
	$(PYTHON) daemon.py --debug

shutdown: ## Shutdown daemon
	$(PYTHON) spk.py shutdown

status: ## Check daemon status
	$(PYTHON) spk.py status

################################################################################
##@ Recording
toggle: ## Toggle recording (start if idle, stop if recording)
	$(PYTHON) spk.py toggle

start: ## Start recording
	$(PYTHON) spk.py start

stop: ## Stop recording and transcribe
	$(PYTHON) spk.py stop

################################################################################
##@ Utilities
.PHONY: help
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "spk - Automatic Speech Recognition\n====================================\n\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

list-devices: ## List available audio input devices
	$(PYTHON) daemon.py --list-devices

test-import: ## Quick test: import all dependencies
	@echo "Testing Python imports..."
	@$(PYTHON) -c "import torch; print('✓ PyTorch:', torch.__version__)"
	@$(PYTHON) -c "import pyaudio; print('✓ PyAudio')"
	@$(PYTHON) -c "import nemo; print('✓ NeMo')"
	@$(PYTHON) -c "import pyperclip; print('✓ Pyperclip')"
	@$(PYTHON) -c "import structlog; print('✓ Structlog')"
	@echo ""
	@echo "✅ All imports successful!"

info: ## Show environment information
	@echo "Environment Information"
	@echo "======================"
	@echo "Python: $(shell python3 --version)"
	@echo "uv: $(shell uv --version)"
	@echo "Venv exists: $(shell [ -d $(VENV) ] && echo 'yes' || echo 'no')"
	@if [ -d "$(VENV)" ]; then \
		echo "PyTorch: $(shell $(PYTHON) -c 'import torch; print(torch.__version__)' 2>/dev/null || echo 'not installed')"; \
		echo "CUDA available: $(shell $(PYTHON) -c 'import torch; print(torch.cuda.is_available())' 2>/dev/null || echo 'N/A')"; \
	fi

clean: ## Remove virtual environment and cache
	rm -rf $(VENV)
	rm -rf __pycache__
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned up!"
