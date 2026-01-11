## ADDED Requirements
### Requirement: Configured auto-type delay
The system SHALL allow configuring `output.autotype_delay_ms` to control the per-keystroke delay (in milliseconds) when auto-typing transcripts.

#### Scenario: Auto-type delay configured
- **WHEN** `output.autotype_delay_ms` is set to a positive integer and post-clipboard action is `autotype`
- **THEN** the system auto-types the transcript using the configured delay between keystrokes

### Requirement: Auto-type delay default
The system SHALL default `output.autotype_delay_ms` to `0` when the value is not configured.

#### Scenario: Auto-type delay not configured
- **WHEN** `output.autotype_delay_ms` is missing from the output configuration
- **THEN** the system uses a 0ms delay between auto-typed keystrokes
