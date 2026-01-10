# Change: Add optional LLM post-processing for transcripts

## Why

Users want an optional cleanup step that lightly fixes dictation errors and prefers domain terms. This enables cleaner output without changing the core transcription model.

## What Changes

- Add an optional LLM post-processing step that runs after transcription
- Add XDG-based TOML configuration with provider, model, prompt override, and preferred terms
- Default to disabled with safe fallback to raw transcript on failure

## Impact

- Affected specs: transcript-postprocess
- Affected code: spkezy_daemon.py, new config loader and LLM client module
