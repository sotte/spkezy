## ADDED Requirements

### Requirement: Optional LLM post-processing

The system SHALL optionally post-process transcripts using an LLM after transcription completes and before output is sent to clipboard or auto-typing.

#### Scenario: Post-processing enabled

- **WHEN** post-processing is enabled in config
- **THEN** the system sends the raw transcript and preferred terms to the LLM and uses the cleaned text for output and stats

#### Scenario: Post-processing disabled

- **WHEN** post-processing is disabled or missing from config
- **THEN** the system uses the raw transcript without calling any LLM

### Requirement: Safe fallback on failure

The system SHALL fall back to the raw transcript when post-processing fails.

#### Scenario: LLM request fails

- **WHEN** the LLM request errors
- **THEN** the system uses the raw transcript and continues without blocking

### Requirement: XDG TOML configuration

The system SHALL read post-processing configuration from `$XDG_CONFIG_HOME/spkezy/config.toml` or `~/.config/spkezy/config.toml`.

#### Scenario: Config file present

- **WHEN** the config file exists
- **THEN** the system loads post-processing settings from it

#### Scenario: Config file missing

- **WHEN** the config file does not exist
- **THEN** the system proceeds with defaults and does not error

### Requirement: Prompt override

The system SHALL allow an optional prompt override in configuration for the LLM post-processing request.

#### Scenario: Prompt override configured

- **WHEN** a prompt override is configured
- **THEN** the system uses the override prompt for the LLM request

#### Scenario: Prompt override not configured

- **WHEN** no prompt override is configured
- **THEN** the system uses the default prompt

### Requirement: OpenAI provider credentials

The system SHALL read the OpenAI API key from the `OPENAI_API_KEY` environment variable.

#### Scenario: API key missing

- **WHEN** post-processing is enabled and `OPENAI_API_KEY` is not set
- **THEN** the system skips post-processing and uses the raw transcript
