# spkezy - automatic speech recognition (ASR) for Linux

> **spkezy** stands for **Speakeasy** - because speech should be easy

Free, open-source local AI dictation using NVIDIA NeMo Parakeet TDT 0.6B v3.

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
bind = $mainMod SHIFT CONTROL ALT, R, exec, make -C /path/to/spkezy toggle
```

Replace `/path/to/spkezy` with your installation directory.

---

**Note:** This project is a heavily modified fork of [edxeth/parakeet-dictation](https://github.com/edxeth/parakeet-dictation). Thanks to edxeth for the original work!
