from io import StringIO
from typing import Any, cast

import pytest
from rich.console import Console
from rich.text import Text
from spkezy.stats import DayStats
from spkezy.tui import (
    SpkezyStatsApp,
    calculate_duration_distribution,
    calculate_hourly_counts,
    calculate_rolling_trend,
    calculate_weekday_counts,
    render_duration_distribution,
    render_heatmap,
    render_hourly,
    render_hourly_summary,
    render_rolling_trend,
    render_summary,
    render_weekday_profile,
)
from textual.widgets import RichLog, Sparkline, Static, TabbedContent

pytestmark = pytest.mark.unit


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _render_to_string(renderable) -> str:
    """Render a Rich renderable to a plain string for assertions."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    console.print(renderable)
    return buf.getvalue()


# --- render_heatmap ---


def test_render_heatmap_returns_renderable_with_data():
    by_day = {
        "2024-06-15": DayStats(date="2024-06-15", count=3, recording_ms=5000, words=20),
        "2024-06-16": DayStats(date="2024-06-16", count=1, recording_ms=2000, words=8),
    }
    output = _render_to_string(render_heatmap(by_day, num_months=3))

    assert "spkezy Activity" in output
    assert "Mon" in output
    assert "Sun" in output
    assert "Legend" in output


def test_render_heatmap_empty_shows_message():
    output = _render_to_string(render_heatmap({}, num_months=3))

    assert "No stats recorded yet" in output


def test_render_heatmap_places_sunday_activity_on_sun_row(monkeypatch: pytest.MonkeyPatch):
    from datetime import UTC, datetime

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 6, 19, tzinfo=UTC)

    monkeypatch.setattr("spkezy.tui.datetime", FixedDateTime)

    output = _render_to_string(
        render_heatmap(
            {
                "2024-06-16": DayStats(
                    date="2024-06-16",
                    count=1,
                    recording_ms=1000,
                    words=5,
                )
            },
            num_months=1,
        )
    )

    lines = output.splitlines()
    mon_line = next(line for line in lines if line.startswith("Mon"))
    sun_line = next(line for line in lines if line.startswith("Sun"))
    blocks = {"░", "▒", "▓", "█"}

    assert not any(char in blocks for char in mon_line[4:])
    assert any(char in blocks for char in sun_line[4:])


def test_render_heatmap_legend_uses_heatmap_colors():
    group = render_heatmap(
        {"2024-06-16": DayStats(date="2024-06-16", count=4, recording_ms=2000, words=8)},
        num_months=1,
    )
    legend = cast(Any, group).renderables[-1]

    assert isinstance(legend, Text)
    assert any("green" in str(span.style) for span in legend.spans)


# --- render_summary ---


def test_render_summary_shows_all_periods():
    by_day = {
        "2024-06-15": DayStats(date="2024-06-15", count=5, recording_ms=60000, words=100),
    }
    output = _render_to_string(render_summary(by_day))

    assert "Summary" in output
    assert "All time" in output
    assert "Current streak" in output
    assert "Longest streak" in output


def test_render_summary_with_empty_data():
    output = _render_to_string(render_summary({}))

    assert "No stats recorded yet" in output


# --- hourly ---


def test_calculate_hourly_counts_aggregates_valid_timestamps():
    counts = calculate_hourly_counts(
        [
            {"timestamp": "2024-06-15T09:00:00Z"},
            {"timestamp": "2024-06-15T09:30:00Z"},
            {"timestamp": "2024-06-15T14:00:00Z"},
            {"timestamp": "broken"},
        ]
    )

    assert counts[9] == 2
    assert counts[14] == 1
    assert sum(counts) == 3


def test_render_hourly_shows_bars():
    entries = [
        {"timestamp": "2024-06-15T09:00:00Z"},
        {"timestamp": "2024-06-15T09:30:00Z"},
        {"timestamp": "2024-06-15T14:00:00Z"},
    ]
    output = _render_to_string(render_hourly(entries))

    assert "Hourly Activity" in output
    assert "█" in output
    assert "09:00" in output
    assert "14:00" in output


def test_render_hourly_summary_mentions_peak_and_top_slots():
    summary = render_hourly_summary(
        [
            {"timestamp": "2024-06-15T10:00:00Z"},
            {"timestamp": "2024-06-15T10:15:00Z"},
            {"timestamp": "2024-06-15T15:00:00Z"},
        ]
    )
    output = _render_to_string(summary)

    assert "Peak hour:" in output
    assert "10:00 (2 recordings)" in output
    assert "Top slots:" in output


def test_render_hourly_empty():
    output = _render_to_string(render_hourly([]))

    assert "No stats recorded yet" in output


# --- duration ---


def test_calculate_duration_distribution_buckets_recordings():
    buckets, durations = calculate_duration_distribution(
        [
            {"recording_duration_ms": 4_000},
            {"recording_duration_ms": 8_000},
            {"recording_duration_ms": 22_000},
            {"recording_duration_ms": 80_000},
        ]
    )

    assert buckets == [
        ("0-5s", 1),
        ("5-15s", 1),
        ("15-30s", 1),
        ("30-60s", 0),
        ("60s+", 1),
    ]
    assert durations == [4_000, 8_000, 22_000, 80_000]


def test_render_duration_distribution_shows_summary():
    output = _render_to_string(
        render_duration_distribution(
            [
                {"recording_duration_ms": 4_000},
                {"recording_duration_ms": 8_000},
                {"recording_duration_ms": 22_000},
            ]
        )
    )

    assert "Recording Length" in output
    assert "Median:" in output
    assert "Average:" in output
    assert "Longest:" in output


# --- weekday ---


def test_calculate_weekday_counts_aggregates_by_weekday():
    counts = calculate_weekday_counts(
        [
            {"timestamp": "2024-06-17T09:00:00Z"},  # Mon
            {"timestamp": "2024-06-17T10:00:00Z"},
            {"timestamp": "2024-06-18T09:00:00Z"},  # Tue
            {"timestamp": "2024-06-23T09:00:00Z"},  # Sun
        ]
    )

    assert counts == [2, 1, 0, 0, 0, 0, 1]


def test_render_weekday_profile_shows_weekend_share():
    output = _render_to_string(
        render_weekday_profile(
            [
                {"timestamp": "2024-06-17T09:00:00Z"},
                {"timestamp": "2024-06-18T09:00:00Z"},
                {"timestamp": "2024-06-22T09:00:00Z"},
            ]
        )
    )

    assert "Weekday Profile" in output
    assert "Best day:" in output
    assert "Weekend share:" in output


# --- trend ---


def test_calculate_rolling_trend_builds_daily_series(monkeypatch: pytest.MonkeyPatch):
    from datetime import UTC, datetime

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 6, 28, tzinfo=UTC)

    monkeypatch.setattr("spkezy.tui.datetime", FixedDateTime)

    trend = calculate_rolling_trend(
        [
            {
                "timestamp": "2024-06-26T09:00:00Z",
                "recording_duration_ms": 4_000,
                "transcript_words": 3,
            },
            {
                "timestamp": "2024-06-28T09:00:00Z",
                "recording_duration_ms": 8_000,
                "transcript_words": 5,
            },
        ],
        days=3,
        window=2,
    )

    assert trend["recordings"] == [1, 0, 1]
    assert trend["words"] == [3, 0, 5]
    assert trend["audio_ms"] == [4_000, 0, 8_000]


def test_render_rolling_trend_shows_recent_vs_previous(monkeypatch: pytest.MonkeyPatch):
    from datetime import UTC, datetime

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 6, 28, tzinfo=UTC)

    monkeypatch.setattr("spkezy.tui.datetime", FixedDateTime)

    output = _render_to_string(
        render_rolling_trend(
            [
                {
                    "timestamp": "2024-06-21T09:00:00Z",
                    "recording_duration_ms": 3_000,
                    "transcript_words": 4,
                },
                {
                    "timestamp": "2024-06-27T09:00:00Z",
                    "recording_duration_ms": 6_000,
                    "transcript_words": 7,
                },
                {
                    "timestamp": "2024-06-28T09:00:00Z",
                    "recording_duration_ms": 8_000,
                    "transcript_words": 9,
                },
            ],
            days=14,
            window=7,
        )
    )

    assert "Rolling Trend" in output
    assert "Last 14 days" in output
    assert "Recordings" in output
    assert "This 7d vs previous 7d" in output


# --- Textual app ---


@pytest.mark.anyio
async def test_stats_app_renders_in_small_terminal_size():
    app = SpkezyStatsApp(
        entries=[
            {
                "timestamp": "2024-06-15T09:00:00Z",
                "recording_duration_ms": 1000,
                "transcript_words": 3,
            }
        ],
        transcripts=[{"timestamp": "2024-06-15T09:00:00Z", "text": "hello world"}],
        num_months=3,
    )

    async with app.run_test(size=(70, 20)) as pilot:
        await pilot.pause()
        assert app.query_one(TabbedContent).active == "heatmap"


@pytest.mark.anyio
async def test_stats_app_switches_views_and_populates_widgets():
    entries = [
        {
            "timestamp": "2024-06-15T09:00:00Z",
            "recording_duration_ms": 1000,
            "transcript_words": 3,
        },
        {
            "timestamp": "2024-06-15T10:00:00Z",
            "recording_duration_ms": 2000,
            "transcript_words": 5,
        },
        {
            "timestamp": "2024-06-16T10:30:00Z",
            "recording_duration_ms": 3000,
            "transcript_words": 7,
        },
    ]
    transcripts = [
        {"timestamp": "2024-06-15T09:00:00Z", "text": "hello world"},
        {"timestamp": "2024-06-15T10:00:00Z", "text": "testing one two"},
    ]
    app = SpkezyStatsApp(entries=entries, transcripts=transcripts, num_months=3)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        tabs = app.query_one(TabbedContent)
        assert tabs.active == "heatmap"
        assert app.query_one("#heatmap-view", Static).content is not None

        await pilot.press("s")
        await pilot.pause()
        assert tabs.active == "summary"
        assert app.query_one("#summary-view", Static).content is not None

        await pilot.press("a")
        await pilot.pause()
        assert tabs.active == "hourly"
        assert app.query_one("#hourly-sparkline", Sparkline).data == [0] * 9 + [1, 2] + [0] * 13

        await pilot.press("d")
        await pilot.pause()
        assert tabs.active == "duration"
        assert app.query_one("#duration-view", Static).content is not None

        await pilot.press("w")
        await pilot.pause()
        assert tabs.active == "weekday"
        assert app.query_one("#weekday-view", Static).content is not None

        await pilot.press("r")
        await pilot.pause()
        assert tabs.active == "trend"
        assert app.query_one("#trend-view", Static).content is not None

        await pilot.press("t")
        await pilot.pause()
        assert tabs.active == "transcripts"
        assert len(app.query_one("#transcripts-log", RichLog).lines) > 0
