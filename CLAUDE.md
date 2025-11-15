# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Parakeet Dictation is a free, open-source local AI dictation tool using NVIDIA NeMo Parakeet TDT 0.6B v3. Runs GPU-accelerated or CPU-only microphone transcription with a clean CLI.

**Supported OS**: Linux (Ubuntu/Debian) and WSL2 Ubuntu. Windows native and macOS are not supported (no NeMo wheels, Unix socket IPC).

## Development Setup

### Initial Setup

```bash
# Enter nix-shell environment (provides PortAudio, Python, etc.)
nix-shell

# Create venv and install CPU dependencies
make setup

# OR for GPU (CUDA 12.1)
make setup-gpu
```

### Common Commands

```bash
# One-shot transcription mode
make run              # Auto-detect GPU/CPU
make run-cpu          # Force CPU
make run-debug        # Debug output to transcriber.debug.log

# Daemon mode (keeps model loaded in memory)
make daemon           # Start daemon (Ctrl+C to exit)
make daemon-debug     # Start with debug output
make toggle           # Toggle recording (start if idle, stop if recording)
make daemon-status    # Check daemon state
make daemon-stop      # Shutdown daemon

# Audio device management
make list-devices     # List input devices

# Testing
make test-import      # Quick test: verify all dependencies import

# Environment info
make info             # Show Python, uv, PyTorch, CUDA status
```

## Architecture

### Core Components

1. **transcriber.py** - One-shot CLI mode
   - Loads model once per invocation (~20-40s CPU, ~5-15s GPU)
   - Interactive: Press Enter to start/stop recording
   - Uses `select()` for non-blocking input (Linux-only)

2. **daemon.py** - Long-running daemon mode
   - Keeps model loaded in memory (eliminates startup time)
   - Unix socket IPC at `$XDG_RUNTIME_DIR/parakeet-daemon.sock` (or `/tmp/parakeet-daemon.sock`)
   - State machine: idle → recording → transcribing → idle
   - Desktop notifications via `notify-send`
   - Thread-safe command handling

3. **parakeet-ctl.py** - Daemon control client
   - Sends commands to daemon via Unix socket
   - Commands: start, stop, toggle, status, shutdown
   - JSON protocol for request/response

### Daemon State Machine

States:
- **idle**: Ready, waiting for start command
- **recording**: Capturing audio from microphone
- **transcribing**: Processing audio with NeMo model

Events (via socket):
- `start`: idle → recording
- `stop`: recording → transcribing (then → idle when done)
- `toggle`: idle → recording OR recording → transcribing
- `status`: Query current state
- `shutdown`: Terminate daemon

### Audio Pipeline

1. PyAudio captures 16kHz mono PCM (paInt16)
2. Save to temporary `.wav` file
3. NeMo ASRModel.transcribe() processes audio
4. Copy transcript to clipboard (via pyperclip)
5. Clean up temp file

### Output Silencing

Both scripts implement selective stdout/stderr silencing to suppress verbose NeMo/PyTorch output:
- `--debug`: All output to file (`transcriber.debug.log`) or stderr
- Normal mode: Stdout/stderr redirected to `/dev/null` during heavy imports and model operations
- Spinner animations write to `sys.__stdout__` (original stream) to avoid interference

### Dependencies

Core:
- **NeMo Toolkit (`nemo_toolkit[asr]`)**: ASR model framework
- **PyTorch**: Backend for inference (CPU or CUDA build)
- **PyAudio**: Microphone access via PortAudio
- **pyperclip**: Clipboard integration

System (via nix-shell):
- PortAudio 19
- PulseAudio
- notify-send (libnotify)
- xclip/wl-clipboard (for clipboard on X11/Wayland)

### NixOS Integration

`shell.nix` provides isolated development environment:
- Python 3.11 with pip, setuptools
- PortAudio development libraries
- Audio stack (PulseAudio, ALSA plugins)
- Clipboard utilities

Quick start script: `.nixos-quickstart`

## Development Notes

### Model Loading

- First run: Downloads ~1-2GB model from Hugging Face Hub (cached at `~/.cache/huggingface/hub`)
- Subsequent runs: Loads from cache
- Model placed on device via `model.to(device)` (cuda or cpu)

### Daemon Socket Lifecycle

1. Check for existing socket; test connection to detect stale sockets
2. Create Unix socket, bind, listen
3. Accept connections in background thread
4. Handle each command in separate thread
5. Cleanup socket file on shutdown

### Testing Strategy

- Import test: `make test-import` verifies all dependencies load
- Manual testing: Use daemon + parakeet-ctl for integration testing
- Device testing: `--list-devices` to enumerate audio inputs

### Common Issues

- **Sample rate mismatch**: Some devices only support 48kHz. Select device via `--input-device` or change system default.
- **Clipboard fails**: Install xclip (X11) or wl-clipboard (Wayland), or use `--no-clipboard`.
- **GPU not detected**: Reinstall CUDA PyTorch build, verify with `make info`.
- **Stale socket**: Remove manually if daemon crashes: `rm /run/user/$UID/parakeet-daemon.sock`

## Hotkey Integration Example

For Hyprland window manager:

```bash
# Create wrapper script
cat > tools/hotkey-toggle.sh <<'EOF'
#!/usr/bin/env bash
cd /home/stefan/coding/parakeet-dictation
nix-shell --run "make toggle"
EOF
chmod +x tools/hotkey-toggle.sh

# Add to ~/.config/hypr/hyprland.conf
# bind = SUPER, R, exec, /home/stefan/coding/parakeet-dictation/tools/hotkey-toggle.sh
```

Usage: Start daemon (`make daemon`), then press Super+R to toggle recording on/off.
