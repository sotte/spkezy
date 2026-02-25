# macOS Compatibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `spkezy` installable and usable on macOS with native notification/sound/autotype behavior while preserving Linux behavior.

**Architecture:** Keep all platform-specific behavior in thin helpers within `spkezy/daemon.py`, keyed off `sys.platform`, with graceful fallback logging when optional binaries or permissions are missing. Preserve existing output config shape and daemon flow so only command execution logic changes.

**Tech Stack:** Python (`subprocess`, `sys`), pytest, pyperclip, existing daemon/runtime modules.

---

### Task 1: Add failing tests for platform-specific behavior

**Files:**
- Create: `tests/test_daemon_platform.py`
- Modify: `tests/test_output.py`
- Test: `tests/test_daemon_platform.py`, `tests/test_output.py`

**Step 1: Write the failing test**
- Add tests that assert:
  - macOS notification path uses AppleScript, Linux uses `notify-send`.
  - macOS sound path uses `afplay`, Linux uses `paplay`.
  - macOS autotype path uses AppleScript and does not require Wayland.
  - output action support allows autotype on macOS and Wayland Linux only.

**Step 2: Run test to verify it fails**
Run: `uv run pytest tests/test_daemon_platform.py -v`
Expected: FAIL because current implementation only supports Linux commands and Wayland check.

### Task 2: Implement macOS-compatible daemon command execution

**Files:**
- Modify: `spkezy/daemon.py`
- Test: `tests/test_daemon_platform.py`

**Step 3: Write minimal implementation**
- Add helper(s) for platform detection and command construction:
  - notifications: `osascript -e 'display notification ...'` on macOS, `notify-send` on Linux.
  - sound: `afplay` on macOS, `paplay` on Linux.
  - autotype: AppleScript `System Events` keystroke on macOS, `wtype` on Linux.
- Keep error handling and logging behavior graceful.

**Step 4: Run tests to verify they pass**
Run: `uv run pytest tests/test_daemon_platform.py tests/test_output.py -v`
Expected: PASS.

### Task 3: Update platform support checks and docs

**Files:**
- Modify: `spkezy/output.py`
- Modify: `README.md`
- Test: `tests/test_output.py`

**Step 5: Write minimal implementation**
- Replace Wayland-only helper with helper that supports:
  - macOS autotype support
  - Wayland Linux autotype support
  - unsupported elsewhere
- Update README title/setup/notes for macOS (Apple Silicon) and macOS hotkey options.

**Step 6: Verify**
Run: `uv run pytest tests/test_output.py -v`
Expected: PASS.

### Task 4: Full project verification

**Files:**
- Modify: none
- Test: all checks

**Step 7: Run full checks**
Run: `make chores`
Expected: lint, format, typecheck, tests all pass.

**Step 8: Prepare PR**
Run: `git status -sb` and `git diff --stat`
Expected: only intended files changed for macOS compatibility.
