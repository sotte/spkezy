# output-control Specification

## Purpose
TBD - created by archiving change update-output-mode-config. Update Purpose after archive.
## Requirements
### Requirement: Configured post-clipboard action
The system SHALL always copy transcripts to the clipboard and then execute a post-clipboard action configured in `config.toml`.

#### Scenario: Post-clipboard action set to none
- **WHEN** the post-clipboard action is set to `none`
- **THEN** the system copies the transcript to the clipboard and performs no further action

#### Scenario: Post-clipboard action set to autotype
- **WHEN** the post-clipboard action is set to `autotype`
- **THEN** the system copies the transcript to the clipboard and auto-types the transcript

### Requirement: Wayland-only auto actions
The system SHALL support post-clipboard auto actions only on Wayland using supported tools.

#### Scenario: Auto action requested on unsupported platform
- **WHEN** a post-clipboard auto action is requested on an unsupported platform
- **THEN** the system logs a warning and falls back to clipboard-only behavior

### Requirement: Config default
The system SHALL default the post-clipboard action to `none` when not configured.

#### Scenario: Config missing
- **WHEN** the output configuration is missing
- **THEN** the system uses `none` as the post-clipboard action

