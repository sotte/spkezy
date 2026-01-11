## ADDED Requirements

### Requirement: Configurable transcript storage

The system SHALL read a transcript storage setting from `config.toml` under `[stats] store_transcripts`, defaulting to `true` when unset.

#### Scenario: Storage enabled by default

- **WHEN** the config file is missing or `[stats] store_transcripts` is `true`
- **THEN** the system writes transcript JSONL entries (timestamp + text) under the transcripts data directory

#### Scenario: Storage disabled

- **WHEN** `[stats] store_transcripts` is `false`
- **THEN** the system does not write transcript JSONL files and still records stats entries for the transcription
