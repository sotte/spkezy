# Branding and Naming Conventions

## ADDED Requirements

### Requirement: Project name must be "spkezy"

All user-facing documentation, configuration files, and code comments SHALL refer to the project as "spkezy" (lowercase) rather than "Parakeet Dictation".

#### Scenario: User reads README.md

```markdown
# spkezy - automatic speech recognition (ASR) for Linux

> **spkezy** stands for **Speakeasy** - because speech should be easy

Free, open-source local AI dictation using NVIDIA NeMo Parakeet TDT 0.6B v3.
```

**Expected**: Title uses "spkezy", includes explanation of name origin, preserves model reference

#### Scenario: Developer reads pyproject.toml

```toml
[project]
name = "spkezy"
description = "spkezy - free, open-source local AI dictation using NVIDIA NeMo Parakeet TDT 0.6B v3"
```

**Expected**: Package name is "spkezy", description includes both project name and model reference

### Requirement: Module filenames must use "spkezy" prefix

All Python modules SHALL use "spkezy" or "spkezy_*" naming pattern (with underscores) for consistency and clarity.

#### Scenario: User lists Python files in project root

```bash
$ ls *.py
spkezy_daemon.py  spkezy.py  spkezy_stats.py
```

**Expected**: All modules use spkezy prefix with underscores

#### Scenario: Developer imports stats module in spkezy.py

```python
# In spkezy.py, line 57
from spkezy_stats import clear_stats, export_stats_json, show_stats
```

**Expected**: Import uses module name matching filename (spkezy_stats for spkezy_stats.py)

### Requirement: IPC socket must use "spkezy-daemon.sock" naming

The Unix socket for daemon communication SHALL be named `spkezy-daemon.sock` to match project branding.

#### Scenario: Daemon starts and creates socket

```python
# In spkezy_daemon.py
def get_socket_path(args_socket_path: str | None) -> Path:
    if args_socket_path:
        return Path(args_socket_path)
    runtime_dir = os.getenv("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / "spkezy-daemon.sock"
    return Path("/tmp") / "spkezy-daemon.sock"
```

**Expected**: Socket path uses `spkezy-daemon.sock` in both runtime and temp fallback locations

#### Scenario: Client connects to daemon

```python
# In spkezy.py
def get_socket_path():
    runtime_dir = os.getenv("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / "spkezy-daemon.sock"
    else:
        return Path("/tmp") / "spkezy-daemon.sock"
```

**Expected**: Client uses identical socket path logic to daemon

### Requirement: AI model references must remain "Parakeet TDT"

References to the underlying NVIDIA NeMo model SHALL preserve "Parakeet" naming since that's the official model identifier.

#### Scenario: Documentation mentions the AI model

```markdown
Free, open-source local AI dictation using NVIDIA NeMo Parakeet TDT 0.6B v3.
```

**Expected**: Model name "Parakeet TDT 0.6B v3" is preserved

#### Scenario: Code downloads model from Hugging Face

```python
# Model ID in code
model_id = "nvidia/parakeet-tdt-0.6b-v3"
```

**Expected**: Model ID remains unchanged (external dependency, not our branding)

### Requirement: Makefile commands must reference correct filenames

All Makefile targets SHALL invoke renamed Python modules with correct paths.

#### Scenario: User runs "make daemon"

```makefile
daemon: ## Start daemon
 $(PYTHON) spkezy_daemon.py
```

**Expected**: Executes spkezy_daemon.py

#### Scenario: User runs "make toggle"

```makefile
toggle: ## Toggle recording (start if idle, stop if recording)
 $(PYTHON) spkezy.py toggle
```

**Expected**: Executes spkezy.py with toggle argument

#### Scenario: User runs "make stats"

```makefile
stats: ## Show usage statistics and activity heatmap
 $(PYTHON) spkezy.py stats
```

**Expected**: Executes spkezy.py (which imports from spkezy_stats)

### Requirement: README must explain name origin

The README SHALL clearly state that "spkezy" stands for "Speakeasy" to avoid confusion.

#### Scenario: New user reads README for first time

```markdown
# spkezy - automatic speech recognition (ASR) for Linux

> **spkezy** stands for **Speakeasy** - because speech should be easy
```

**Expected**: Name explanation appears prominently at top of README

### Requirement: Example configurations must use realistic paths

Documentation examples SHALL NOT hardcode specific user paths like `/home/stefan/coding/parakeet-dictation`.

#### Scenario: User reads Hyprland integration example

```markdown
## Hyprland Integration

Add to your `~/.config/hypr/hyprland.conf`:

```bash
bind = $mainMod SHIFT CONTROL ALT, R, exec, make -C /path/to/spkezy toggle
```

Replace `/path/to/spkezy` with your installation directory.

```

**Expected**: Generic path placeholder with clear instruction to customize

## MODIFIED Requirements

None (this is a new project, no existing branding requirements to modify)

## REMOVED Requirements

None (additive change only)
