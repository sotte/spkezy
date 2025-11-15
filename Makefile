#!/usr/bin/env bash
# Makefile for Parakeet Dictation
# NOTE: Run inside nix-shell: nix-shell

VENV := .venv
PYTHON := $(VENV)/bin/python
UV := uv

.PHONY: help
help: ## Show this help message
	@echo "Parakeet Dictation - Available Commands"
	@echo "========================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "First time setup: make setup"

.PHONY: setup
setup: ## Create venv and install CPU dependencies
	@echo "🔧 Creating virtual environment..."
	$(UV) venv
	@echo ""
	@echo "📦 Installing PyTorch (CPU version)..."
	$(UV) pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cpu
	@echo ""
	@echo "📦 Installing other dependencies..."
	$(UV) pip install 'nemo_toolkit[asr]' pyaudio 'numpy<2.0' pyperclip
	@echo ""
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next: make run"

.PHONY: setup-gpu
setup-gpu: ## Create venv and install GPU (CUDA 12.1) dependencies
	@echo "🔧 Creating virtual environment..."
	$(UV) venv
	@echo ""
	@echo "📦 Installing PyTorch (CUDA 12.1 version)..."
	$(UV) pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cu121
	@echo ""
	@echo "📦 Installing other dependencies..."
	$(UV) pip install 'nemo_toolkit[asr]' pyaudio 'numpy<2.0' pyperclip
	@echo ""
	@echo "✅ GPU setup complete!"
	@echo ""
	@echo "Next: make run (will use GPU automatically)"

.PHONY: run
run: check-venv ## Run dictation (CPU/GPU auto-detected)
	$(PYTHON) transcriber.py

.PHONY: run-cpu
run-cpu: check-venv ## Force CPU mode
	$(PYTHON) transcriber.py --cpu

.PHONY: run-debug
run-debug: check-venv ## Run with debug output
	$(PYTHON) transcriber.py --debug

.PHONY: daemon
daemon: check-venv ## Start daemon in foreground
	$(PYTHON) daemon.py

.PHONY: daemon-debug
daemon-debug: check-venv ## Start daemon with debug output
	$(PYTHON) daemon.py --debug

.PHONY: daemon-status
daemon-status: check-venv ## Check daemon status
	$(PYTHON) parakeet-ctl.py status

.PHONY: daemon-stop
daemon-stop: check-venv ## Stop/shutdown the daemon
	$(PYTHON) parakeet-ctl.py shutdown

.PHONY: toggle
toggle: check-venv ## Toggle recording (start if idle, stop if recording)
	$(PYTHON) parakeet-ctl.py toggle

.PHONY: start
start: check-venv ## Send 'start' command to daemon (begin recording)
	$(PYTHON) parakeet-ctl.py start

.PHONY: stop
stop: check-venv ## Send 'stop' command to daemon (stop & transcribe)
	$(PYTHON) parakeet-ctl.py stop

.PHONY: list-devices
list-devices: check-venv ## List available audio input devices
	$(PYTHON) transcriber.py --list-devices

.PHONY: test-import
test-import: check-venv ## Quick test: import all dependencies
	@echo "Testing Python imports..."
	@$(PYTHON) -c "import torch; print('✓ PyTorch:', torch.__version__)"
	@$(PYTHON) -c "import pyaudio; print('✓ PyAudio imported')"
	@$(PYTHON) -c "import nemo; print('✓ NeMo imported')"
	@$(PYTHON) -c "import pyperclip; print('✓ Pyperclip imported')"
	@echo ""
	@echo "✅ All imports successful!"

.PHONY: check-venv
check-venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "❌ Virtual environment not found!"; \
		echo "Run 'make setup' first."; \
		exit 1; \
	fi

.PHONY: clean
clean: ## Remove virtual environment and cache
	rm -rf $(VENV)
	rm -rf __pycache__
	rm -f transcriber.debug.log
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned up!"

.PHONY: shell
shell: check-venv ## Open Python shell in venv
	$(PYTHON)

.PHONY: info
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
