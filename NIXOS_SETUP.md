# NixOS Setup Guide for Parakeet Dictation

This project has been configured to run on NixOS using `nix-shell` for system dependencies and `uv` for Python package management.

## Quick Start

```bash
# Enter the development environment
nix-shell

# Set up Python environment with CPU support (first time only)
make setup

# List available audio input devices
make list-devices

# Run dictation
make run

# See all available commands
make help
```

## How It Works

### System Dependencies (nix-shell)

The `shell.nix` provides:
- Python 3.11
- PortAudio (for PyAudio/microphone access)
- ALSA libraries
- PulseAudio libraries
- wl-clipboard (for Wayland clipboard support)
- Build tools (gcc, stdenv)

**Important**: Always run commands inside `nix-shell`. The shell sets up `LD_LIBRARY_PATH` so PyAudio can find the system libraries.

### Python Dependencies (uv)

The Makefile handles creating a `.venv` and installing:
- PyTorch (CPU or GPU version)
- NVIDIA NeMo Toolkit (ASR)
- PyAudio
- Pyperclip
- Supporting libraries

## GPU Support

To switch from CPU to GPU:

```bash
# Clean up CPU installation
make clean

# Set up with GPU support (CUDA 12.1)
make setup-gpu

# Run (will auto-detect and use GPU)
make run
```

**Note**: The GPU version uses PyTorch with CUDA 12.1 support, which is compatible with your CUDA 12.8 drivers.

### Verify GPU is Working

```bash
# Run with debug output
make run-debug

# Look for these lines in the output:
# - "Model device: cuda:0" (should NOT be "cpu")
# - "GPU alloc (MiB) after load: XXX.XX" (should show memory usage)
```

## Available Make Commands

- `make setup` - Set up with CPU support
- `make setup-gpu` - Set up with GPU (CUDA) support
- `make run` - Run dictation (auto-detects CPU/GPU)
- `make run-cpu` - Force CPU mode even if GPU available
- `make run-debug` - Run with verbose debug output
- `make list-devices` - List audio input devices
- `make test-import` - Quick test that all packages import correctly
- `make info` - Show environment information
- `make clean` - Remove venv and cache files
- `make help` - Show all commands

## Audio Device Selection

If the default microphone isn't working:

1. List devices: `make list-devices`
2. Note the `id=X` of your preferred device
3. Run with specific device: `nix-shell --run ".venv/bin/python transcriber.py --input-device X"`

## Troubleshooting

### ALSA Warnings

Warnings like "Unknown PCM cards.pcm.rear" or "unable to open slave" are normal and harmless on NixOS. They don't affect functionality.

### JACK Warnings

"jack server is not running" warnings are also normal if you're not using JACK audio. PyAudio tries multiple backends.

### PyAudio Can't Find PortAudio

Make sure you're inside `nix-shell`. The shell sets up library paths automatically.

### Clipboard Not Working

For Wayland (Hyprland), make sure `wl-clipboard` is available. It's included in `shell.nix`, but verify with:
```bash
which wl-copy
```

If clipboard fails, you can disable it:
```bash
nix-shell --run ".venv/bin/python transcriber.py --no-clipboard"
```

## Model Cache

On first run, the Parakeet model (1-2GB) will be downloaded and cached in:
- `~/.cache/huggingface/hub`

Subsequent runs load from cache instantly.

## Workflow

Typical workflow for using this tool:

```bash
# Start development environment
nix-shell

# Run dictation
make run

# Wait for model to load (only slow on first run)
# Press ENTER to start recording
# Speak your message
# Press ENTER to stop
# Text is transcribed and copied to clipboard
# Press ENTER again to record more, or Ctrl+C to exit
```

## Performance Notes

### CPU Mode
- Model load: ~10-30 seconds (first time with download)
- Inference: ~2-5 seconds per recording
- Memory: ~2-3 GB RAM

### GPU Mode (GTX 1080 Ti)
- Model load: ~5-15 seconds (first time with download)
- Inference: ~0.5-2 seconds per recording
- VRAM: ~2-3 GB
- Much faster for repeated transcriptions

## Not Using nix-shell

If you want to add these dependencies to your system configuration instead:

```nix
environment.systemPackages = with pkgs; [
  portaudio
  alsa-lib
  alsa-plugins
  pulseaudio
  wl-clipboard
];
```

Then you can use `uv` directly without `nix-shell`:
```bash
uv venv
source .venv/bin/activate
make setup  # or make setup-gpu
```

However, using `nix-shell` is recommended for project isolation.
