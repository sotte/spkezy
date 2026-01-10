## ADDED Requirements

### Requirement: Pytest unit testing framework
The project SHALL use pytest to run unit tests for internal logic.

#### Scenario: Running unit tests
- **WHEN** a developer runs the unit test command
- **THEN** pytest executes the unit tests in the repository

### Requirement: Testmon caching enabled
The unit test suite SHALL support pytest-testmon caching for faster incremental runs.

#### Scenario: Cached unit test run
- **WHEN** a developer runs pytest with testmon enabled
- **THEN** unchanged tests are skipped based on dependency tracking

### Requirement: Unit test style conventions
Unit tests SHALL be function-based with long, descriptive names, and SHALL NOT use test classes or docstrings.

#### Scenario: Writing a new unit test
- **WHEN** a developer adds a unit test
- **THEN** the test is a standalone function with a descriptive name and no docstring

### Requirement: File-level unit markers
Unit test files SHALL apply a pytest `unit` marker at the file level, and the marker SHALL be registered in `pytest.ini`.

#### Scenario: Selecting unit tests
- **WHEN** a developer runs pytest with `-m unit`
- **THEN** the unit test files are included

### Requirement: Unit test focus
Unit tests SHALL target pure logic and isolated behaviors, avoiding external services and hardware.

#### Scenario: Testing logic without external dependencies
- **WHEN** a unit test covers configuration parsing or stats aggregation
- **THEN** the test isolates external interactions via mocks or temporary paths

### Requirement: Development-only test dependencies
Pytest and pytest-testmon SHALL be added as development dependencies, not runtime dependencies.

#### Scenario: Installing runtime dependencies
- **WHEN** runtime dependencies are installed
- **THEN** pytest and pytest-testmon are not included

### Requirement: Test layout uses module-focused files
Unit tests SHALL live under `tests/` in module-focused files (for example, `tests/test_stats.py`).

#### Scenario: Locating tests for a module
- **WHEN** a developer needs tests for `spkezy/stats.py`
- **THEN** they can find them under `tests/test_stats.py`

### Requirement: Test execution via Makefile
The Makefile SHALL provide `test` (with pytest-testmon caching) and `test-all` (without caching) targets.

#### Scenario: Running tests without caching
- **WHEN** a developer runs `make test-all`
- **THEN** pytest executes without testmon caching

#### Scenario: Running tests with caching
- **WHEN** a developer runs `make test`
- **THEN** pytest executes with testmon caching enabled
