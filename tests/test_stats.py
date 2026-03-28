import json
from datetime import UTC, datetime, timedelta

import pytest
from spkezy import stats

pytestmark = pytest.mark.unit


def test_record_stats_writes_stats_and_transcript_entries(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    stats.record_stats(
        recording_duration_ms=1200,
        transcription_duration_ms=3400,
        transcript="hello world",
        compute_device="cpu",
        audio_input_device="sysdefault",
    )

    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    stats_file = tmp_path / "spkezy" / "stats" / f"{date_str}.jsonl"
    transcript_file = tmp_path / "spkezy" / "transcripts" / f"{date_str}.jsonl"

    assert stats_file.exists()
    assert transcript_file.exists()

    stats_entry = json.loads(stats_file.read_text(encoding="utf-8").splitlines()[0])
    transcript_entry = json.loads(transcript_file.read_text(encoding="utf-8").splitlines()[0])

    assert stats_entry["recording_duration_ms"] == 1200
    assert stats_entry["transcription_duration_ms"] == 3400
    assert stats_entry["transcript_chars"] == len("hello world")
    assert stats_entry["transcript_words"] == 2
    assert stats_entry["compute_device"] == "cpu"
    assert stats_entry["audio_input_device"] == "sysdefault"
    assert transcript_entry["text"] == "hello world"


def test_record_stats_skips_transcript_write_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    config_home = tmp_path / "config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    config_dir = config_home / "spkezy"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text(
        "[stats]\nstore_transcripts = false\n",
        encoding="utf-8",
    )

    stats.record_stats(
        recording_duration_ms=1200,
        transcription_duration_ms=3400,
        transcript="hello world",
        compute_device="cpu",
        audio_input_device="sysdefault",
    )

    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    stats_file = tmp_path / "spkezy" / "stats" / f"{date_str}.jsonl"
    transcript_file = tmp_path / "spkezy" / "transcripts" / f"{date_str}.jsonl"

    assert stats_file.exists()
    assert not transcript_file.exists()


def test_load_all_stats_skips_invalid_json_lines(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    stats_dir = tmp_path / "spkezy" / "stats"
    stats_dir.mkdir(parents=True)
    file_path = stats_dir / "2024-01-01.jsonl"
    valid_entry = {"timestamp": "2024-01-01T00:00:00Z", "recording_duration_ms": 1}
    file_path.write_text(
        json.dumps(valid_entry) + "\n" + "not-json\n" + json.dumps(valid_entry) + "\n",
        encoding="utf-8",
    )

    entries = stats.load_all_stats()

    assert len(entries) == 2


def test_aggregate_by_day_sums_counts_and_words():
    entries = [
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "recording_duration_ms": 100,
            "transcript_words": 3,
        },
        {
            "timestamp": "2024-01-01T12:00:00Z",
            "recording_duration_ms": 200,
            "transcript_words": 5,
        },
        {
            "timestamp": "2024-01-02T09:00:00Z",
            "recording_duration_ms": 50,
            "transcript_words": 2,
        },
    ]

    by_day = stats.aggregate_by_day(entries)

    assert by_day["2024-01-01"].count == 2
    assert by_day["2024-01-01"].recording_ms == 300
    assert by_day["2024-01-01"].words == 8
    assert by_day["2024-01-02"].count == 1


def test_calculate_streaks_handles_empty_activity_set():
    current, longest = stats.calculate_streaks(set())

    assert (current, longest) == (0, 0)


def test_calculate_streaks_tracks_current_and_longest_streaks():
    today = datetime.now(UTC).date()
    dates_with_activity = {
        today.strftime("%Y-%m-%d"),
        (today - timedelta(days=1)).strftime("%Y-%m-%d"),
        (today - timedelta(days=2)).strftime("%Y-%m-%d"),
        (today - timedelta(days=4)).strftime("%Y-%m-%d"),
    }

    current, longest = stats.calculate_streaks(dates_with_activity)

    assert (current, longest) == (3, 3)


@pytest.mark.parametrize(
    "milliseconds, expected",
    [
        (59_000, "59s"),
        (61_000, "1m 1s"),
        (3_600_000, "1h 0m"),
    ],
)
def test_format_duration_outputs_human_readable_strings(milliseconds, expected):
    assert stats.format_duration(milliseconds) == expected


def test_load_transcripts_returns_recent_entries_first(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    transcripts_dir = tmp_path / "spkezy" / "transcripts"
    transcripts_dir.mkdir(parents=True)

    day1 = transcripts_dir / "2024-01-01.jsonl"
    day2 = transcripts_dir / "2024-01-02.jsonl"
    day1.write_text(
        json.dumps({"timestamp": "2024-01-01T09:00:00Z", "text": "first"})
        + "\n"
        + json.dumps({"timestamp": "2024-01-01T10:00:00Z", "text": "second"})
        + "\n",
        encoding="utf-8",
    )
    day2.write_text(
        json.dumps({"timestamp": "2024-01-02T08:00:00Z", "text": "third"}) + "\n",
        encoding="utf-8",
    )

    result = stats.load_transcripts(limit=50)

    assert len(result) == 3
    assert result[0]["text"] == "third"
    assert result[1]["text"] == "second"
    assert result[2]["text"] == "first"


def test_load_transcripts_respects_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    transcripts_dir = tmp_path / "spkezy" / "transcripts"
    transcripts_dir.mkdir(parents=True)

    file = transcripts_dir / "2024-01-01.jsonl"
    lines = [
        json.dumps({"timestamp": f"2024-01-01T{h:02d}:00:00Z", "text": f"entry {h}"})
        for h in range(10)
    ]
    file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = stats.load_transcripts(limit=3)

    assert len(result) == 3
    assert result[0]["text"] == "entry 9"


def test_load_transcripts_returns_empty_when_no_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    result = stats.load_transcripts()

    assert result == []


def test_export_stats_json_returns_serialized_entries(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    stats_dir = tmp_path / "spkezy" / "stats"
    stats_dir.mkdir(parents=True)
    file_path = stats_dir / "2024-01-01.jsonl"
    entry = {"timestamp": "2024-01-01T00:00:00Z", "recording_duration_ms": 1}
    file_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    payload = stats.export_stats_json()

    decoded = json.loads(payload)
    assert decoded == [entry]
