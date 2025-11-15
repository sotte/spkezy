# Backlog

This file contains things to do for this repo.

## TODO

- Switch to uv
- Clean up python code
  - add type annotations, use `pyrefly` as type checker
  - add `ruff`
- Try with more modern python: 3.13
- Update README.md: simplify, make shorter
- make nix first class citizen

## DONE

- Basic daemon implementation
- Add notifications: on model load; on start recording; on stop recording
- Add `parakeet-ctl.py toggle` to toggle recording
- Make daemon output more informative: show config early (CPU/GPU, socket path, model name), progress indicators, and clear status messages
