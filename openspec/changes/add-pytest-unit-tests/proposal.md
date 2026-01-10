# Change: Add pytest-based unit tests with testmon caching

## Why
The codebase has multiple pure-logic helpers and configuration parsing paths that are easy to regress without fast feedback. A lightweight unit test layer improves confidence without requiring audio hardware or a running daemon.

## What Changes
- Add pytest and pytest-testmon as development dependencies for unit testing with optional cached runs.
- Establish a unit test structure under `tests/` with module-focused files.
- Add initial unit tests for configuration parsing, runtime paths, stats aggregation, and daemon command dispatch logic.
- Keep tests as functions with long, descriptive names; no test classes or docstrings.
- Add Makefile entry points (`test` with testmon, `test-all` without) to run tests.
- Prefer minimal mocking, using pytest parametrization when it improves clarity.
- Apply pytest markers at the file level for unit tests, registered in `pytest.ini`.

## Test Outline
- `spkezy/runtime.py`: XDG path resolution, config load behavior on missing/invalid TOML.
- `spkezy/output.py`: output config validation and Wayland detection.
- `spkezy/postprocess.py`: postprocess config parsing, prompt composition, and early-exit behavior.
- `spkezy/stats.py`: aggregation, streak calculation, duration formatting, and JSON export.
- `spkezy/io.py`: state manager transitions and command dispatch responses.

## Impact
- Affected specs: new `testing` capability.
- Affected code: `pyproject.toml`, new `tests/` tree, pytest config (e.g., `pytest.ini`), `Makefile`.
