## Context

The project currently lacks a unit test framework. We want fast, local-only tests that do not require audio devices, a running daemon, or network access.

## Goals / Non-Goals

- Goals:
  - Add pytest as the unit test runner and pytest-testmon for caching.
  - Establish a unit test layout and naming conventions.
  - Cover core pure-logic modules with unit tests.
  - Prefer real logic over heavy mocking; use pytest parametrization where it clarifies coverage.
  - Mark unit tests at the file level to simplify selection, registering markers in `pytest.ini`.
- Non-Goals:
  - End-to-end audio capture, model inference, or IPC integration tests.
  - Performance benchmarking or load testing.

## Decisions

- Decision: Use pytest with pytest-testmon for cached runs.
  - Alternatives considered: unittest (less ergonomic), no caching (slower feedback).
- Decision: Structure tests under `tests/` with module-focused files.
  - Rationale: Keeps test file location predictable without duplicating package paths.
- Decision: Use function-based tests with long, descriptive names and no docstrings.
  - Rationale: Aligns with existing naming conventions and avoids class-based boilerplate.
- Decision: Provide Makefile targets for pytest runs with and without testmon.
  - Rationale: Makes caching opt-in and keeps test commands discoverable.
  - Target names: `make test` (with testmon), `make test-all` (without).

## Proposed Test Structure

```
tests/
  test_runtime.py
  test_output.py
  test_postprocess.py
  test_stats.py
  test_io.py
```

## File-Level Marker Example

```python
import pytest

pytestmark = pytest.mark.unit
```

## Pytest Marker Registration Example

```ini
[pytest]
markers =
    unit: unit tests
```

## Risks / Trade-offs

- Adding pytest-testmon introduces a new dev dependency; ensure it is optional at runtime.
- Unit tests may require careful mocking to avoid side effects in filesystem or environment variables.

## Migration Plan

1. Add pytest + pytest-testmon to dev dependencies.
2. Add pytest configuration enabling testmon.
3. Add unit test files and fixtures.

## Open Questions

- None.
