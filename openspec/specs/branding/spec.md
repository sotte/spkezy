# branding Specification

## Purpose
TBD - created by archiving change rebrand-to-spkezy. Update Purpose after archive.
## Requirements
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

### Requirement: Modules must live under the "spkezy" package

All Python runtime modules SHALL live under the `spkezy/` package directory for consistency and clarity.

#### Scenario: User lists Python package files

```bash
$ ls spkezy
__init__.py  __main__.py  daemon.py  io.py  output.py  postprocess.py  runtime.py  stats.py
```

**Expected**: Runtime modules are contained within the spkezy package

#### Scenario: Developer imports stats module in __main__.py

```python
# In spkezy/__main__.py
from spkezy.stats import clear_stats, export_stats_json, show_stats
```

**Expected**: Import uses the spkezy package namespace

### Requirement: IPC socket must use "spkezy-daemon.sock" naming

The Unix socket for daemon communication SHALL be named `spkezy-daemon.sock` to match project branding.

#### Scenario: Daemon starts and creates socket

```python
# In spkezy/runtime.py
def get_socket_path(override: str | None = None) -> Path:
    if override:
        return Path(override)
    runtime_dir = os.getenv("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / "spkezy-daemon.sock"
    return Path("/tmp") / "spkezy-daemon.sock"
```

**Expected**: Socket path uses `spkezy-daemon.sock` in both runtime and temp fallback locations

#### Scenario: Client connects to daemon

```python
# In spkezy/__main__.py
socket_path = get_socket_path()
```

**Expected**: Client uses the shared socket path helper

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
 $(UV_RUN) spkezy-daemon
```

**Expected**: Executes spkezy-daemon

#### Scenario: User runs "make toggle"

```makefile
toggle: ## Toggle recording (start if idle, stop if recording)
 $(UV_RUN) spkezy toggle
```

**Expected**: Executes spkezy with toggle argument

#### Scenario: User runs "make stats"

```makefile
stats: ## Show usage statistics and activity heatmap
 $(UV_RUN) spkezy stats
```

**Expected**: Executes spkezy stats

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
