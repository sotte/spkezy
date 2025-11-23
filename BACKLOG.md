# Backlog

This file contains things to do for this repo.

## TODO

- Try with more modern python: 3.13

## DONE

- Basic daemon implementation
- Add notifications: on model load; on start recording; on stop recording
- Add `parakeet-ctl.py toggle` to toggle recording
- Make daemon output more informative: show config early (CPU/GPU, socket path, model name), progress indicators, and clear status messages
- Add audio feedback: play sound.mp3 on recording start/stop
- Add auto-type functionality: automatically type transcript using wtype (Wayland) instead of just copying to clipboard
- Add ruff linting: configure and fix all style issues (bare excepts, unnecessary f-strings, intentional late imports)
- Switch to uv: use uv projects, not `uv pip`. Put dependencies in pyproject.toml
- use structlog for logging
- Create new and minimal README.md
- Update README.md: simplify, make shorter
- make nix first class citizen (removed as hard dependency)
- Runtime auto-type toggle: add socket commands (autotype-on/off/toggle) to enable/disable auto-typing while daemon is running, update parakeet-ctl.py and add make target
- check: can we get this repo to work without the nix-shell? just pure uv
- cleanup of daemon.py structure
  - rm transriber.py, we only need the daemon and the ctl command
  - currently quite messy, one big file, lot's of code, no structure; could be improved;
  - braindump for structure:
    - cli interface
    - model loader
    - use rich for nicer output, also don't reinvent the wheel
    - maybe socket handling and dispatching
    - keep one file for now
    - heavy imports only when we need them
  - clean up reladed files
- Copy transcript to clipboard first, then auto-type (ensures text is in clipboard history)
- ruff: add make targets to autoformat, fix, and check code
- types: use pyrefly as type checker, add make target, add type annotations where practical
