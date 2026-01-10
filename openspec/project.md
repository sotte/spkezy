# Project Context

## Purpose
spkezy is a free, open-source local AI dictation tool using NVIDIA NeMo Parakeet TDT 0.6B v3. It provides GPU-accelerated or CPU-only microphone transcription with a clean CLI interface. The project prioritizes privacy (all processing is local), low latency (daemon mode keeps model loaded), and simplicity (single-purpose tool, no complex configuration).

The name "spkezy" stands for "Speakeasy" - because speech should be easy.

**Key Goals:**
- Zero-cost, offline speech-to-text for everyday use
- Fast iteration cycle: hotkey → speak → transcribe → paste
- Integration with existing workflows (clipboard, auto-type, desktop notifications)

## Tech Stack

### Core Technologies
- **Python 3.11+** - Primary language
- **NVIDIA NeMo Toolkit** (`nemo_toolkit[asr]`) - ASR model framework
- **PyTorch** - Backend for inference (CPU or CUDA 12.1 builds)
- **PyAudio** - Microphone access via PortAudio
- **pyperclip** - Clipboard integration (xclip/wl-clipboard backends)
- **structlog** - Structured logging
- **rich** - Terminal UI (spinners, formatted output)

### System Dependencies
- PortAudio 19 - Audio I/O library
- PulseAudio - Linux audio server
- notify-send (libnotify) - Desktop notifications
- xclip/wl-clipboard - X11/Wayland clipboard support

### Build & Development Tools
- **uv** - Fast Python package installer and virtual environment manager
- **ruff** - Linter and formatter (replaces flake8, black, isort)
- **basedpyright** - Type checker
- **Make** - Task automation (Makefile)

## Project Conventions

### Code Style
- **Line length**: 100 characters (configured in pyproject.toml)
- **Target version**: Python 3.11
- **Linting**: Ruff with rules E (pycodestyle errors), F (pyflakes), I (isort), N (pep8-naming), W (warnings), UP (pyupgrade)
- **Type checking**: basedpyright in "standard" mode with relaxed unknown type reporting
- **Formatting**: Ruff formatter (auto-applied via `make fmt`)
- **Function names**: Long and descriptive to make code self-documenting; avoid abbreviations
- **Comments**: Preserve existing comments unless provably false; add new comments only when they add value beyond obvious code behavior; avoid temporal context ("after refactor", "new implementation")
- **Naming**: Evergreen names only (no "new", "improved", "enhanced" prefixes)
- **Bash scripts**: Use `#!/usr/bin/env bash` shebang

### Architecture Patterns

**Operational Modes:**
1. **One-shot mode** (deprecated, removed) - Previously loaded model per invocation
2. **Daemon mode** (`spkezy/daemon.py`, primary) - Long-running process with IPC

**Daemon Architecture:**
- **State machine**: idle → recording → transcribing → idle
- **IPC**: Unix socket at `$XDG_RUNTIME_DIR/spkezy-daemon.sock` (Linux-only, no Windows native support)
- **Protocol**: JSON-based request/response over Unix socket
- **Threading**: Command handler thread + main thread for model operations
- **Output silencing**: Selective stdout/stderr redirection to suppress verbose PyTorch/NeMo logs during normal operation
- **Clipboard workflow**: Transcribe → copy to clipboard → optionally auto-type via xdotool (Linux desktop automation)

**Key Design Principles:**
- YAGNI (You Aren't Gonna Need It) - Build only what's needed now
- Simple over complex - Prefer clear, maintainable solutions over clever optimizations
- Readability counts - Follow Zen of Python
- Local-first - No cloud dependencies, all processing on-device

### Testing Strategy
- **Import testing**: `make test-import` verifies all dependencies load correctly
- **Manual integration testing**: Use `make daemon` + `make toggle` for end-to-end workflow validation
- **Device testing**: `make list-devices` to enumerate audio inputs and test hardware compatibility
- **No unit test framework currently** - Project is early stage, focused on functional correctness

### Git Workflow
- **Commit format**: Conventional Commits (e.g., `feat:`, `fix:`, `chore:`, `refactor:`)
- **Critical rule**: NEVER use `--no-verify` when committing (enforced in global CLAUDE.md)
- **Branching**: Feature branches off main; current development branch is `daemonify`
- **Main branch**: `daemonify` (as indicated by gitStatus)

## Domain Context

### Speech Recognition (ASR)
- **Model**: NVIDIA NeMo Parakeet TDT 0.6B v3 (~1-2GB download, cached at `~/.cache/huggingface/hub`)
- **Audio format**: 16kHz mono PCM (paInt16) - standard for speech recognition
- **Sample rate issues**: Some devices only support 48kHz; requires device selection via `--input-device` or system default change
- **Latency targets**:
  - Cold start (one-shot): ~20-40s CPU, ~5-15s GPU
  - Warm start (daemon): <1s (model pre-loaded)

### Linux Desktop Integration
- **Notification system**: Uses `notify-send` for recording state feedback
- **Clipboard**: Cross-platform via pyperclip (xclip for X11, wl-paste/wl-copy for Wayland)
- **Auto-type**: xdotool simulates keyboard input (X11 only, not Wayland-compatible)
- **Hotkey binding**: Delegates to window manager (e.g., Hyprland with `bind = SUPER, R, exec, ...`)

### IPC Protocol
Commands sent to daemon via Unix socket:
- `start` - Begin recording (idle → recording)
- `stop` - End recording and transcribe (recording → transcribing → idle)
- `toggle` - Start if idle, stop if recording
- `status` - Query current state (idle/recording/transcribing)
- `shutdown` - Gracefully terminate daemon

Responses: JSON with `{"status": "ok"}` or error details

## Important Constraints

### Platform Support
- **Supported**: Linux (Ubuntu/Debian), WSL2 Ubuntu
- **Not supported**: Windows native (no NeMo wheels), macOS (no NeMo wheels), Unix socket IPC is POSIX-only
- **Architecture**: x86_64 only (NeMo/PyTorch wheel availability)

### Hardware Requirements
- **CPU mode**: Any x86_64 CPU, ~2-4GB RAM, slow cold start (~20-40s)
- **GPU mode**: NVIDIA GPU with CUDA 12.1 support, ~4-6GB VRAM, faster cold start (~5-15s)
- **Microphone**: Any PyAudio-compatible input device (USB, built-in, PulseAudio virtual devices)

### Security & Privacy
- **Local processing only**: No network requests during transcription (model downloads from Hugging Face Hub once)
- **No telemetry**: No usage analytics, error reporting, or data collection
- **Audio retention**: Temporary .wav files deleted immediately after transcription

### Development Environment
- **System libraries**: Requires PortAudio, PulseAudio development libraries installed via system package manager
- **Python version**: Locked to 3.11+ (NeMo compatibility)
- **Virtual environment**: Required (uv-managed .venv)

## External Dependencies

### Hugging Face Hub
- **Purpose**: Model download and caching
- **Model ID**: `nvidia/parakeet-tdt-0.6b-v3`
- **Cache location**: `~/.cache/huggingface/hub/`
- **Network requirement**: First run only; offline thereafter

### System Audio Stack
- **PortAudio 19**: Cross-platform audio I/O
- **PulseAudio**: Linux audio server (ALSA plugins for device enumeration)
- **Hardware access**: Requires microphone permissions (usually automatic on desktop Linux)

### Desktop Environment
- **notify-send**: Desktop notifications (optional, degrades gracefully if missing)
- **xclip/wl-clipboard**: Clipboard access (required for primary workflow)
- **xdotool**: Auto-type simulation (optional, X11 only)

### Python Package Indexes
- **PyPI**: Default for most packages
- **PyTorch wheels**: Custom indexes for CPU (`download.pytorch.org/whl/cpu`) and CUDA (`download.pytorch.org/whl/cu121`)
- **Index selection**: Controlled via `pyproject.toml` with uv index configuration
