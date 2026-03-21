# spkezy

Free, open-source local AI dictation using NVIDIA NeMo Parakeet TDT 0.6B v3.

## Setup and Usage

```bash
make setup             # Install CPU dependencies

# Daemon mode (recommended)
make daemon            # Start daemon
make shutdown          # Stop daemon

# Control the daemon
make toggle            # Toggle recording on/off
make status            # Check daemon state

# DEV
make chores            # Run all checks, fixes, tests
```

## Architecture

**Core files:**

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

**Key design:**

- State machine: idle → recording → transcribing → idle
- Unix socket IPC at `$XDG_RUNTIME_DIR/spkezy-daemon.sock`
- PipeWire (`pw-record`) captures 16kHz mono PCM audio
- NeMo model transcribes to text
- Output to clipboard (pyperclip) with optional auto-type

**Dependencies:**

- NeMo Toolkit, PyTorch (CPU or CUDA builds)
- pyperclip, structlog, rich
- System: PipeWire (pw-record), notify-send, xclip/wl-clipboard

For comprehensive project context, see `openspec/project.md`.

## Development Notes

- Always run `make chores` (linting, formatting, typechecking, tests) before presenting results to the user
- Use Conventional Commit messages for any commits.
- Use properly typed Python.
- Use `pytest` for tests: mirror folder structure in `spkezy/`; use functions with descriptive names for tests,not classes, not doc-strings;
  - Be aware: we use `pytest-testmon` to cache tests, so we don't always run all the tests.
- Model downloads ~1-2GB on first run (cached at `~/.cache/huggingface/hub`)
- Daemon startup takes a few seconds

<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:

- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:

- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->
**Note:** Always use `bunx @fission-ai/openspec@latest` instead of `openspec`.
