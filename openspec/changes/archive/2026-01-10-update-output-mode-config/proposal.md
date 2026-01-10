# Change: Configure post-clipboard output action

## Why
Users want the daemon output behavior to be driven by config rather than CLI flags, with clipboard always enabled and a clear post-clipboard action.

## What Changes
- Add a config-driven post-clipboard action that controls autotype or paste behavior
- Keep clipboard copy always enabled during output
- Limit auto actions to Wayland using existing tooling
- Update README and Makefile to reflect config-driven output behavior

## Impact
- Affected specs: output-control
- Affected code: spkezy_daemon.py, config loader, README.md, Makefile
