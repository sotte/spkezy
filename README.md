# `spkezy` - automatic speech recognition (ASR) for Linux on your computer

**spkezy** stands for **speakeasy**, it is an open-source local automatic speech recognition tool using [NVIDIA NeMo Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3).

> This project is [home cooked software](https://www.robinsloan.com/notes/home-cooked-app/).
> But of course, you are free to use it as you wish.
> You might even like it.

**Features**:

- 🚀 Fast speech-to-text with Parakeet on CPU or GPU
- 🧠 Always-ready daemon keeps the model warm for low latency
- ⌨️ One-command start/stop toggle for quick dictation
- 📋 Copies transcripts to your clipboard (optional auto-type)
- 🧽 Optional LLM cleanup for smoother text
- 📊 Lightweight usage stats and activity heatmap
- 📝 Configurable transcript storage for easy retrieval

## Getting Started

```bash
# Install dependencies
uv sync

# Run via uv
uv run spkezy-daemon

# Start recording
uv run spkezy toggle
# End recording, start transcription, and copy result to clipboard
uv run spkezy toggle
```

## Details

### Config File

Location: `$XDG_CONFIG_HOME/spkezy/config.toml` (or `~/.config/spkezy/config.toml`)

```toml
[audio]                         # See "Audio Input" section
input_device = "auto"          # "auto" | "default" | exact device name | numeric id

[output]                        # See "Output Behavior" section
post_clipboard_action = "none"  # "none" | "autotype" (see Output Behavior)
autotype_delay_ms = 0           # Keystroke delay in ms for autotype

[postprocess_llm]               # See "LLM Post-Processing" section
enabled = false
provider = "openai"
model = "gpt-4o-mini"
preferred_terms = ["foo", "bar"]
prompt_override = "Translate to German."
```

### Audio Input

`spkezy` captures audio via PipeWire (`pw-record`), which automatically uses the system default
audio source. When you change the default mic in your system settings (e.g. pavucontrol),
`spkezy` follows the change — no restart needed.

```toml
# $XDG_CONFIG_HOME/spkezy/config.toml
[audio]
input_device = "auto" # "auto" | "default" | PipeWire source name
```

You can inspect available sources with:

```bash
spkezy-daemon --list-devices
```

The output shows PipeWire audio sources and marks the current system default with `*`.

To use a specific source instead of the system default, set `input_device` to the full PipeWire
source name shown by `--list-devices` (e.g. `alsa_input.usb-FIFINE_Microphones-00.iec958-stereo`).

**Requires PipeWire.** The daemon checks for `pw-record` at startup and fails with a clear error
if it is not available.

### Output Behavior

`spkezy` always copies transcripts to the clipboard.
Optionally, it can autotype the transcript.

```toml
# $XDG_CONFIG_HOME/spkezy/config.toml
[output]
post_clipboard_action = "none" # "none" | "autotype"
autotype_delay_ms = 0          # Keystroke delay in ms for autotype
```

Notes: `autotype` is Wayland-only and requires `wtype`.
Set `autotype_delay_ms` to add a per-keystroke delay; `0` keeps current speed. Some applications can't handle a delay of 0.

### LLM Post-Processing of Transcripts

`spkezy` can optionally clean up transcripts using an LLM after transcription.
This is disabled by default.
When enabled, the daemon sends the raw transcript to OpenAI, applies a light cleanup, and returns the cleaned text for clipboard/auto-typing.
If the request fails or the API key is missing, `spkezy` falls back to the raw transcript.

```toml
# $XDG_CONFIG_HOME/spkezy/config.toml
[postprocess_llm]
enabled = true
provider = "openai"
model = "gpt-4o-mini"
# preferred_terms are soft-bias terms the model should prefer when ambiguous (not forced replacements)
preferred_terms = ["Parakeet", "custom glossary"]
# prompt_override is optional; omit it to use the default prompt
prompt_override = "Turn the following transcript into pirate-speak."
```

Note: Set your `OPENAI_API_KEY` API key in the environment to use this feature.

### Stats

Location: `$XDG_DATA_HOME/spkezy/stats/` (or `~/.local/share/spkezy/stats/`)

Daily JSONL files track each transcription: recording duration, transcription time, word count,
compute device, and audio input device.
The `spkezy stats` command displays a GitHub-style activity heatmap and summary table (today/week/month/all-time) with streak tracking.

```bash
spkezy stats          # Show heatmap and summary (last 3 months)
spkezy stats -n 6     # Show last 6 months
spkezy stats --json   # Export all stats as JSON
spkezy stats --clear  # Delete all stats and transcripts
```

### Transcripts

Location: `$XDG_DATA_HOME/spkezy/transcripts/` (or `~/.local/share/spkezy/transcripts/`)

By default, every transcription is automatically saved to daily JSONL files with timestamp and full text.

To keep stats without saving transcript text, disable transcript storage:

```toml
# $XDG_CONFIG_HOME/spkezy/config.toml
[stats]
store_transcripts = false
```

### Hyprland Integration

Add to your `~/.config/hypr/hyprland.conf`:

```bash
bind = $mainMod SHIFT CONTROL ALT, R, exec, uv run --project /path/to/spkezy spkezy toggle
```

Replace `/path/to/spkezy` with your installation directory.

## Development

```folder-structure
.
├── spkezy/
│   ├── __init__.py         # Package marker (empty)
│   ├── __main__.py         # CLI entrypoint (client + daemon wrapper)
│   ├── audio.py            # Audio input configuration
│   ├── capture.py          # PipeWire audio capture (pw-record subprocess)
│   ├── daemon.py           # Daemon loop, recording, transcription
│   ├── io.py               # Unix socket server + client send logic
│   ├── output.py           # Output config + clipboard/autotype helpers
│   ├── postprocess.py      # LLM post-processing config + client
│   ├── runtime.py          # XDG paths + socket/config helpers
│   ├── stats.py            # Stats recording + rendering
│   └── sound.mp3           # UI feedback sound
├── Makefile                # Dev shortcuts (run, fix, typecheck)
├── pyproject.toml          # Packaging + tooling config
└── README.md               # Project overview + usage
```

## Attribution

This project is a heavily modified fork of [edxeth/parakeet-dictation](https://github.com/edxeth/parakeet-dictation). Thanks to edxeth for the original work!
