# Rebrand to spkezy

## Why

The current name "Parakeet Dictation" is verbose and references the underlying AI model rather than establishing a distinct project identity. Rebranding to "spkezy" (short for Speakeasy) creates a memorable, concise name that's easier to type and distinguish from the NVIDIA model.

## What Changes

- **Documentation**: Update README.md, CLAUDE.md, openspec/project.md to use "spkezy" branding; delete BACKLOG.md
- **Configuration**: Change pyproject.toml package name to "spkezy"
- **Python modules**: Rename daemon.py → spkezy_daemon.py, spk.py → spkezy.py, stats.py → spkezy_stats.py
- **Code references**: Update socket path from `spk-daemon.sock` to `spkezy-daemon.sock`
- **Build system**: Update Makefile to reference new filenames

## Impact

- Affected specs: branding (new capability)
- Affected code: All Python modules, Makefile, documentation files
- **BREAKING**: Socket path changes, module filenames change (affects user hotkey bindings)

## Summary

The current name "Parakeet Dictation" is verbose and references the underlying model (NVIDIA NeMo Parakeet) rather than establishing a distinct identity. The new name "spkezy" provides:

1. **Brevity**: Shorter, easier to type in commands and documentation
2. **Distinct identity**: Separates the project name from the underlying AI model
3. **Memorability**: Unique name that's easier to search for and reference
4. **Consistency**: Already partially adopted (socket named `spk-daemon.sock`, Makefile refers to `spk`)

## Scope

This change affects:

- **Documentation**: README.md, CLAUDE.md, openspec/project.md, BACKLOG.md
- **Configuration**: pyproject.toml (package name and description)
- **Python modules**: Rename daemon.py → spkezy-daemon.py, spk.py → spkezy.py, stats.py → spkezy-stats.py
- **Code references**: Socket path, help text, comments, docstrings
- **Build system**: Makefile variable references

**Out of scope:**

- Repository directory name (remains `parakeet-dictation` for now)
- Git history (no rewriting commits)
- Hugging Face model references (still uses `nvidia/parakeet-tdt-0.6b-v3`)

## User Impact

**Breaking changes:**

- Users will need to update their hotkey bindings to use new filenames (e.g., `spkezy.py` instead of `spk.py`)
- Socket path changes from `spk-daemon.sock` to `spkezy-daemon.sock`
- PyPI package name changes (if published)

**Migration path:**

- Update documentation with clear before/after examples
- Include migration notes in README for existing users
- Update example Hyprland configuration

## Implementation Notes

All text replacements should be case-sensitive:

- "Parakeet Dictation" → "spkezy"
- "parakeet-dictation" → "spkezy"
- "parakeet" (standalone) → "spkezy" (context-dependent, preserve model references)

The branding should mention what "spkezy" stands for (Speakeasy) in the README for clarity.

## Related Changes

None (standalone rebrand)

## Success Criteria

- [x] All user-facing documentation uses "spkezy" branding
- [x] Python modules renamed and all imports updated
- [x] Socket path uses `spkezy-daemon.sock`
- [x] Makefile commands reference correct filenames
- [x] No broken references or import errors
- [x] `make chores` passes (lint, format, typecheck)
- [x] Daemon starts successfully with new socket path
- [x] README explains "spkezy" stands for "Speakeasy"
