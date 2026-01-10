# spkezy - automatic speech recognition (ASR) for Linux

> **spkezy** stands for **Speakeasy** - because speech should be easy

Free, open-source local AI dictation using [NVIDIA NeMo Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3).

**Features**:

- 🚀 Fast speech-to-text with Parakeet on CPU or GPU
- 🧠 Always-ready daemon keeps the model warm for low latency
- ⌨️ One-command start/stop toggle for quick dictation
- 📋 Copies transcripts to your clipboard (optional auto-type)
- 🧽 Optional LLM cleanup for smoother text
- 📊 Lightweight usage stats and activity heatmap

## Getting Started

```bash
# Install dependencies
uv sync

# Run via uv
uv run spkezy-daemon
uv run spkezy toggle

```

## Optional LLM Post-Processing (OpenAI)

spkezy can optionally clean up transcripts using an LLM after transcription. This is disabled by default.
When enabled, the daemon sends the raw transcript to OpenAI, applies a light cleanup, and returns the
cleaned text for clipboard/auto-typing. If the request fails or the API key is missing, spkezy falls
back to the raw transcript.

Create `$XDG_CONFIG_HOME/spkezy/config.toml` (or `~/.config/spkezy/config.toml`) and set:

```toml
[postprocess_llm]
enabled = true
provider = "openai"
model = "gpt-4o-mini"
preferred_terms = ["Parakeet", "custom glossary"]
```

Notes:

- `preferred_terms` are soft-bias terms the model should prefer when ambiguous (not forced replacements).
- `prompt_override` is optional; omit it to use the default prompt, or set it to a full prompt string.

Example prompt override:

```toml
prompt_override = "Clean up the transcript lightly, keep tone, and avoid adding new content."
```

Set your API key in the environment:

```bash
export OPENAI_API_KEY="your-key"
```

## Output Behavior

spkezy always copies transcripts to the clipboard. You can configure what happens next.

```toml
[output]
post_clipboard_action = "none" # "none" | "autotype"
```

Notes:

- `autotype` is Wayland-only and requires `wtype`.
- Invalid output values will cause the daemon to exit with an error.

## Hyprland Integration

Add to your `~/.config/hypr/hyprland.conf`:

```bash
bind = $mainMod SHIFT CONTROL ALT, R, exec, uv run --project /path/to/spkezy spkezy toggle
```

Replace `/path/to/spkezy` with your installation directory.

---

**Note:** This project is a heavily modified fork of [edxeth/parakeet-dictation](https://github.com/edxeth/parakeet-dictation). Thanks to edxeth for the original work!

## Developers

```
.
├── spkezy/
│   ├── __init__.py         # Package marker (empty)
│   ├── __main__.py         # CLI entrypoint (client + daemon wrapper)
│   ├── daemon.py           # Daemon loop, recording, transcription
│   ├── io.py               # Unix socket server + client send logic
│   ├── output.py           # Output config + clipboard/autotype helpers
│   ├── postprocess.py      # LLM post-processing config + client
│   ├── runtime.py          # XDG paths + socket/config helpers
│   ├── stats.py            # Stats recording + rendering
│   └── sound.mp3           # UI feedback sound
├── Makefile                # Dev shortcuts (run, lint, typecheck)
├── pyproject.toml          # Packaging + tooling config
└── README.md               # Project overview + usage
```
