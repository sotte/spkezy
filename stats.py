"""Stats collection and viewing for parakeet-dictation."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def get_data_dir() -> Path:
    """Get the data directory for stats storage."""
    data_home = os.getenv("XDG_DATA_HOME")
    if data_home:
        base = Path(data_home)
    else:
        base = Path.home() / ".local" / "share"
    return base / "parakeet-dictation"


def record_stats(
    recording_duration_ms: int,
    transcription_duration_ms: int,
    transcript: str,
    device: str,
) -> None:
    """Record a transcription event to daily JSONL files."""
    base_path = get_data_dir()
    stats_dir = base_path / "stats"
    transcripts_dir = base_path / "transcripts"

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = now.strftime("%Y-%m-%d")

    # Ensure directories exist
    stats_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    # Write stats entry
    stats_file = stats_dir / f"{date_str}.jsonl"
    stats_entry = {
        "timestamp": timestamp,
        "recording_duration_ms": recording_duration_ms,
        "transcription_duration_ms": transcription_duration_ms,
        "transcript_chars": len(transcript),
        "transcript_words": len(transcript.split()),
        "device": device,
    }
    with open(stats_file, "a") as f:
        f.write(json.dumps(stats_entry) + "\n")

    # Write transcript entry
    transcript_file = transcripts_dir / f"{date_str}.jsonl"
    transcript_entry = {
        "timestamp": timestamp,
        "text": transcript,
    }
    with open(transcript_file, "a") as f:
        f.write(json.dumps(transcript_entry) + "\n")
