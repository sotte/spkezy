# Implementation Tasks

## Phase 1: Rename Python Modules

**Goal**: Rename core Python files and update all internal imports

- [x] 1. **Rename daemon.py → spkezy_daemon.py**
   - Move file with git mv to preserve history
   - Update Makefile references (PYTHON variable usage remains same)
   - Update any import references (none expected, it's a main module)
   - Validation: File exists at new path

- [x] 2. **Rename spk.py → spkezy.py**
   - Move file with git mv
   - Update Makefile references to spkezy.py
   - Update stats.py import if it references spk.py (check)
   - Validation: `python spkezy.py --help` works

- [x] 3. **Rename stats.py → spkezy_stats.py**
   - Move file with git mv
   - Update imports in spkezy.py (line 57: `from stats import ...` → `from spkezy_stats import ...`)
   - Update imports in spkezy_daemon.py (check for references)
   - Validation: `python spkezy.py stats` works

## Phase 2: Update Socket Path

**Goal**: Change socket from `spk-daemon.sock` to `spkezy-daemon.sock`

- [x] 4. **Update socket path in spkezy_daemon.py**
   - Change line 152: `"spk-daemon.sock"` → `"spkezy-daemon.sock"`
   - Change line 154: `"spk-daemon.sock"` → `"spkezy-daemon.sock"`
   - Validation: Grep confirms no `spk-daemon.sock` references remain in code

- [x] 5. **Update socket path in spkezy.py**
   - Change line 15: `"spk-daemon.sock"` → `"spkezy-daemon.sock"`
   - Change line 17: `"spk-daemon.sock"` → `"spkezy-daemon.sock"`
   - Validation: Grep confirms consistency across both files

## Phase 3: Update Configuration Files

**Goal**: Rebrand in project metadata and build configuration

- [x] 6. **Update pyproject.toml**
   - Change line 2: `name = "parakeet-dictation"` → `name = "spkezy"`
   - Change line 4: `description = "Free, open-source local AI dictation using NVIDIA NeMo Parakeet TDT 0.6B v3"` → `description = "spkezy - free, open-source local AI dictation using NVIDIA NeMo Parakeet TDT 0.6B v3"`
   - Validation: `uv sync` succeeds without errors

- [x] 7. **Update Makefile**
   - Change line 2 comment: `# Makefile for spk` → `# Makefile for spkezy`
   - Change line 33: `$(PYTHON) spk.py shutdown` → `$(PYTHON) spkezy.py shutdown`
   - Change line 36: `$(PYTHON) spk.py status` → `$(PYTHON) spkezy.py status`
   - Change line 42: `$(PYTHON) spk.py toggle` → `$(PYTHON) spkezy.py toggle`
   - Change line 44: `$(PYTHON) spk.py start` → `$(PYTHON) spkezy.py start`
   - Change line 47: `$(PYTHON) spk.py stop` → `$(PYTHON) spkezy.py stop`
   - Change line 50: `$(PYTHON) spk.py stats` → `$(PYTHON) spkezy.py stats`
   - Change line 21: `$(PYTHON) daemon.py` → `$(PYTHON) spkezy_daemon.py`
   - Change line 24: `$(PYTHON) daemon.py --debug` → `$(PYTHON) spkezy_daemon.py --debug`
   - Change line 27: `$(PYTHON) daemon.py --no-auto-type` → `$(PYTHON) spkezy_daemon.py --no-auto-type`
   - Change line 30: `$(PYTHON) daemon.py` → `$(PYTHON) spkezy_daemon.py`
   - Change line 81 help header: `"spk - Automatic Speech Recognition"` → `"spkezy - Automatic Speech Recognition"`
   - Change line 86: `$(PYTHON) daemon.py --list-devices` → `$(PYTHON) spkezy_daemon.py --list-devices`
   - Validation: `make help` displays correct branding

## Phase 4: Update Documentation

**Goal**: Rebrand all user-facing documentation

- [x] 8. **Update README.md**
   - Change line 1: `# \`spk\` - automatic speech recognition (ASR) for Linux` → `# spkezy - automatic speech recognition (ASR) for Linux`
   - Add explanation: Insert after line 1: `> **spkezy** stands for **Speakeasy** - because speech should be easy`
   - Change line 3: `Local AI dictation using NVIDIA NeMo Parakeet TDT 0.6B v3.` → `Free, open-source local AI dictation using NVIDIA NeMo Parakeet TDT 0.6B v3.`
   - Change line 22: `make -C /home/stefan/coding/parakeet-dictation toggle` → `make -C /path/to/spkezy toggle`
   - Update line 23: Add note about replacing path with installation directory
   - Validation: README clearly explains branding and usage

- [x] 9. **Update CLAUDE.md**
   - Change line 1: `# Parakeet Dictation` → `# spkezy`
   - Change line 3: `Free, open-source local AI dictation using NVIDIA NeMo Parakeet TDT 0.6B v3.` (keep for context)
   - Change line 68: `$XDG_RUNTIME_DIR/parakeet-daemon.sock` → `$XDG_RUNTIME_DIR/spkezy-daemon.sock`
   - Validation: CLAUDE.md accurately reflects new structure

- [x] 10. **Update openspec/project.md**
    - Change line 4: First sentence `Parakeet Dictation is a free...` → `spkezy is a free, open-source local AI dictation tool using NVIDIA NeMo Parakeet TDT 0.6B v3.`
    - Add context line after: `The name "spkezy" stands for "Speakeasy" - because speech should be easy.`
    - Change line 50: `**Operational Modes:** 1. **One-shot mode** (\`transcriber.py\`, deprecated)` - update if transcriber.py still exists
    - Change line 55: `$XDG_RUNTIME_DIR/parakeet-daemon.sock` → `$XDG_RUNTIME_DIR/spkezy-daemon.sock`
    - Change all references to "Parakeet Dictation" → "spkezy"
    - Keep model references as "NVIDIA NeMo Parakeet TDT 0.6B v3" (that's the AI model, not our project)
    - Validation: Grep shows no remaining "Parakeet Dictation" references

- [x] 11. **Delete BACKLOG.md**
    - Remove BACKLOG.md file (no longer needed)
    - Validation: File no longer exists

## Phase 5: Validation & Testing

**Goal**: Ensure everything works end-to-end

- [x] 12. **Run code quality checks**
    - Execute: `make chores`
    - Validation: All lint, format, and typecheck pass

- [x] 13. **Test daemon functionality**
    - Execute: `make daemon` (starts daemon with new socket path)
    - Execute: `make toggle` (in another terminal)
    - Validation: Recording starts/stops correctly, socket created at `spkezy-daemon.sock`

- [x] 14. **Test import functionality**
    - Execute: `make test-import`
    - Validation: All Python imports work with renamed modules

- [x] 15. **Final grep verification**
    - Search for remaining "parakeet" references: `rg -i "parakeet" --glob "*.{py,md,toml,sh}"`
    - Review results: Keep only AI model references (nvidia/parakeet-tdt-0.6b-v3)
    - Validation: No incorrect references remain

## Dependencies

- Tasks 1-3 can run in parallel (file renames)
- Tasks 4-5 depend on task 2 (need spkezy.py to exist)
- Tasks 6-11 can run in parallel after Phase 1-2 complete
- Tasks 12-15 must run sequentially after all previous phases
