# Change: Add configurable auto-type delay

## Why
Some applications misbehave when auto-typing is too fast. A configurable delay between keystrokes allows users to slow down auto-typing without disabling it.

## What Changes
- Add a new output configuration value to control per-keystroke delay for auto-typing.
- Default the delay to 0ms to preserve current behavior.
- Document the new configuration in the README.

## Impact
- Affected specs: output-control
- Affected code: spkezy/output.py, spkezy/daemon.py, README.md
