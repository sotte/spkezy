# Backlog

This file contains things to do for this repo.

## TODO

- Runtime auto-type toggle: add socket commands (autotype-on/off/toggle) to enable/disable auto-typing while daemon is running, update parakeet-ctl.py and add make target
- Switch to uv
- Clean up python code
  - add type annotations, use `pyrefly` as type checker
- Try with more modern python: 3.13
- Update README.md: simplify, make shorter
- make nix first class citizen

## DONE

- Basic daemon implementation
- Add notifications: on model load; on start recording; on stop recording
- Add `parakeet-ctl.py toggle` to toggle recording
- Make daemon output more informative: show config early (CPU/GPU, socket path, model name), progress indicators, and clear status messages
- Add audio feedback: play sound.mp3 on recording start/stop
- Add auto-type functionality: automatically type transcript using wtype (Wayland) instead of just copying to clipboard
- Add ruff linting: configure and fix all style issues (bare excepts, unnecessary f-strings, intentional late imports)
