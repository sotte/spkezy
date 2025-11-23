# `spk` - automatic speech recognition (ASR) for linux

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
