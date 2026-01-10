# Change: Refactor into a Python package

## Why

The codebase has grown beyond a couple of scripts, and the current flat layout duplicates shared logic
(e.g., socket paths). A package layout improves cohesion, reduces drift, and makes distribution clearer.

## What Changes

- Introduce a `spkezy` package directory and move runtime modules under it.
- Add `spkezy/__main__.py` as the CLI entrypoint.
- Centralize socket path + XDG path helpers for reuse by client and daemon.
- Update packaging metadata, lint/typecheck paths, and README usage.

## Impact

- Affected specs: packaging
- Affected code: Python modules, `pyproject.toml`, `README.md`
