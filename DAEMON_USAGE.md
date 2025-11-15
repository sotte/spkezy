# Daemon Mode Usage Guide

## What is Daemon Mode?

Daemon mode keeps the AI model loaded in memory, eliminating the 10-30 second startup time. You send commands via Unix socket to start/stop recording.

## Quick Start

```bash
# 1. Enter nix-shell
nix-shell

# 2. Start the daemon (model loads once, stays in memory)
make daemon

# Wait for model to load... you'll see:
# 🚀 PARAKEET TDT 0.6B V3 - DAEMON MODE
# Device: cpu
# ============================================================
# 📡 Listening on: /run/user/1000/parakeet-daemon.sock
#    Send 'start' to begin recording
#    Send 'stop' to transcribe
#    Ctrl+C to exit
# ============================================================
```

## Testing the Daemon (Manual Control)

In a separate terminal (also inside `nix-shell`):

```bash
# Check daemon status
make daemon-status
# Output: ✅ Daemon status: idle

# Option 1: Use toggle (recommended - simpler!)
make toggle
# Output: ✅ Toggle: started recording. State: recording
# Speak your text...
make toggle
# Output: ✅ Toggle: stopped recording. State: transcribing
# (text will appear in daemon terminal and be copied to clipboard)

# Option 2: Use explicit start/stop
make start
# Output: ✅ Command 'start' sent successfully. State: recording
# Speak your text...
make stop
# Output: ✅ Command 'stop' sent successfully. State: transcribing

# Shutdown daemon
make daemon-stop
```

## Available Make Commands

| Command | Description |
|---------|-------------|
| `make daemon` | Start daemon in foreground |
| `make daemon-debug` | Start daemon with debug output |
| `make daemon-status` | Check if daemon is running and its state |
| `make daemon-stop` | Shutdown the daemon |
| `make toggle` | **Toggle recording (recommended!)** |
| `make start` | Send 'start' command (begin recording) |
| `make stop` | Send 'stop' command (stop & transcribe) |

## Daemon States

- **idle** - Ready, waiting for start command
- **recording** - Currently recording audio
- **transcribing** - Processing audio to text

## Socket Location

The daemon creates a Unix socket at:
- `/run/user/$UID/parakeet-daemon.sock` (if XDG_RUNTIME_DIR is set)
- `/tmp/parakeet-daemon.sock` (fallback)

## Next Steps: Hyprland Integration

To trigger recording with a hotkey:

### 1. Create a wrapper script

```bash
# tools/hotkey-toggle.sh
#!/usr/bin/env bash
cd /home/stefan/coding/parakeet-dictation
nix-shell --run "make toggle"
```

Make it executable:
```bash
chmod +x tools/hotkey-toggle.sh
```

### 2. Add to Hyprland config

Edit `~/.config/hypr/hyprland.conf`:

```bash
# Parakeet dictation - single key toggle
bind = SUPER, R, exec, /home/stefan/coding/parakeet-dictation/tools/hotkey-toggle.sh
```

Then reload Hyprland: `hyprctl reload`

### 3. Usage

1. Start daemon: `make daemon` (in terminal, leave running)
2. Press `Super+R` → recording starts (notification shows)
3. Speak your text
4. Press `Super+R` again → transcription happens, text copied to clipboard
5. Paste with `Ctrl+V`

**Note:** Much simpler than before - no need for `bind`/`bindr` combo!

## Troubleshooting

**Daemon won't start: "Daemon already running"**
```bash
# Check if socket exists
ls -la /run/user/$(id -u)/parakeet-daemon.sock

# If it's stale, remove it
rm /run/user/$(id -u)/parakeet-daemon.sock

# Try starting again
make daemon
```

**Can't connect to daemon**
```bash
# Make sure you're in nix-shell
nix-shell

# Make sure daemon is actually running
make daemon-status
```

**Model takes too long to load**
- First run: Downloads ~1-2GB model (one time only)
- Subsequent runs: Loads from cache (~20-40 seconds on CPU)
- GPU mode would be much faster (~5-15 seconds)

## GPU vs CPU

Current setup: **CPU mode**

To switch to GPU (faster transcription):
```bash
make clean
make setup-gpu
make daemon  # Will use GPU automatically
```

GPU benefits:
- Faster model loading (~5-15s vs ~20-40s)
- Faster transcription (~0.5-2s vs ~2-5s per recording)
