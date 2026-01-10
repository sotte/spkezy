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

## Hyprland Integration

Add to your `~/.config/hypr/hyprland.conf`:

```bash
bind = $mainMod SHIFT CONTROL ALT, R, exec, make -C /path/to/spkezy toggle
```

Replace `/path/to/spkezy` with your installation directory.

---

**Note:** This project is a heavily modified fork of [edxeth/parakeet-dictation](https://github.com/edxeth/parakeet-dictation). Thanks to edxeth for the original work!
