<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:

- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:

- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

**Note:** Use `bunx @fission-ai/openspec@latest` instead of just `openspec`.

# spkezy

Free, open-source local AI dictation using NVIDIA NeMo Parakeet TDT 0.6B v3.

**Platform**: Linux (Ubuntu/Debian), WSL2 Ubuntu. No Windows native or macOS support.

## Setup

```bash
make setup             # Install CPU dependencies
make setup-gpu         # OR install GPU/CUDA 12.1 dependencies
```

## Usage

```bash
# Daemon mode (recommended)
make daemon            # Start daemon
make shutdown          # Stop daemon

# Control the daemon
make toggle            # Toggle recording on/off
make status            # Check daemon state

# Utilities
make list-devices      # List audio input devices
make stats             # Show usage statistics
make info              # Environment info

# DEV
make check             # Lint and format check
make typecheck         # Type checking
make chores            # Run all checks
```

## Architecture

**Core files:**

- `daemon.py` - Long-running daemon, keeps model loaded in memory
- `spk.py` - CLI client for daemon control (start/stop/toggle/status/shutdown)
- `stats.py` - Usage statistics and activity heatmap

**Key design:**

- State machine: idle → recording → transcribing → idle
- Unix socket IPC at `$XDG_RUNTIME_DIR/spkezy-daemon.sock`
- PyAudio captures 16kHz mono PCM audio
- NeMo model transcribes to text
- Output to clipboard (pyperclip) with optional auto-type (xdotool)

**Dependencies:**

- NeMo Toolkit, PyTorch (CPU or CUDA builds)
- PyAudio, pyperclip, structlog, rich
- System: PortAudio, PulseAudio, notify-send, xclip/wl-clipboard

## Development Notes

- Model downloads ~1-2GB on first run (cached at `~/.cache/huggingface/hub`)
- Startup: ~5-15s GPU, ~20-40s CPU (daemon eliminates this after initial load)
- Ruff for linting/formatting (100 char lines), basedpyright for type checking
- No unit tests currently - use `make test-import` and manual testing

For comprehensive project context, see `openspec/project.md`.
