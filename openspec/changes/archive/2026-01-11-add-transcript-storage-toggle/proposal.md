# Change: Add configurable transcript storage

## Why

Some users want to keep stats without retaining full transcript text for privacy. A config toggle lets them opt out of transcript storage while keeping the rest of the workflow intact.

## What Changes

- Add a config option to enable/disable transcript text storage (default: enabled).
- When disabled, transcripts are not written to JSONL files, while stats still record durations and counts.
- Update README with the new config option and behavior.

## Impact

- Affected specs: stats
- Affected code: spkezy/runtime.py, spkezy/stats.py, README.md
