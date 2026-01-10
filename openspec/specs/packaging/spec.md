# packaging Specification

## Purpose
TBD - created by archiving change refactor-python-package. Update Purpose after archive.
## Requirements
### Requirement: Package layout
The project SHALL ship a `spkezy` Python package containing the runtime modules.

#### Scenario: Package layout exists
- **WHEN** the source tree is inspected
- **THEN** runtime modules are located under `spkezy/`

### Requirement: CLI entrypoint module
The package SHALL expose a CLI through `spkezy/__main__.py`.

#### Scenario: Module execution
- **WHEN** a user runs `python -m spkezy`
- **THEN** the CLI executes using the package entrypoint

### Requirement: Console scripts
The package SHALL define console scripts for the client and daemon commands.

#### Scenario: Installed scripts
- **WHEN** the package is installed
- **THEN** `spkezy` and `spkezy-daemon` commands are available

### Requirement: Shared socket path helper
The client and daemon SHALL use the same socket path helper to avoid drift.

#### Scenario: Socket path consistency
- **WHEN** the client and daemon resolve the default socket path
- **THEN** both use the same helper and compute the same path

