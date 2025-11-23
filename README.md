# `spk` - automatic speech recognition (ASR) for Linux

Local AI dictation using NVIDIA NeMo Parakeet TDT 0.6B v3.

## Quick Start

```bash
# Setup
make setup        # CPU
make setup-gpu    # GPU (CUDA 12.1)

# Run
make daemon       # Start daemon
make toggle       # Start/stop recording
```

## Hyprland Integration

Add to your `~/.config/hypr/hyprland.conf`:

```bash
bind = $mainMod SHIFT CONTROL ALT, R, exec, make -C /home/stefan/coding/parakeet-dictation toggle
```

Replace `/home/stefan/coding/parakeet-dictation` with your installation path.
