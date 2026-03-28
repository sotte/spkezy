"""Interactive stats TUI built with Textual."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from statistics import mean, median
from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Footer, Header, RichLog, Sparkline, Static, TabbedContent, TabPane

from spkezy.stats import (
    DayStats,
    aggregate_by_day,
    calculate_streaks,
    format_duration,
    load_all_stats,
    load_transcripts,
)

if TYPE_CHECKING:
    from rich.console import ConsoleRenderable


HEATMAP_INTENSITY_CHARS = [" ", "░", "▒", "▓", "█"]
HEATMAP_INTENSITY_COLORS = [
    "bright_black",
    "dim green",
    "green",
    "bright_green",
    "bold bright_green",
]
BAR_WIDTH = 40
DURATION_BUCKETS = [
    ("0-5s", 0, 5_000),
    ("5-15s", 5_000, 15_000),
    ("15-30s", 15_000, 30_000),
    ("30-60s", 30_000, 60_000),
    ("60s+", 60_000, None),
]
WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"


def _get_heatmap_thresholds(max_count: int) -> list[int]:
    if max_count <= 4:
        return [1, 2, 3, 4]

    step = max_count / 4
    return [
        max(1, round(step)),
        max(2, round(step * 2)),
        max(3, round(step * 3)),
        max_count,
    ]


def _get_heatmap_intensity(count: int, thresholds: list[int]) -> int:
    if count == 0:
        return 0
    for level, threshold in enumerate(thresholds, start=1):
        if count <= threshold:
            return level
    return 4


def _get_bar_color(value: int, max_value: int) -> str:
    if value <= 0 or max_value <= 0:
        return "bright_black"

    ratio = value / max_value
    if ratio <= 0.25:
        return HEATMAP_INTENSITY_COLORS[1]
    if ratio <= 0.5:
        return HEATMAP_INTENSITY_COLORS[2]
    if ratio <= 0.75:
        return HEATMAP_INTENSITY_COLORS[3]
    return HEATMAP_INTENSITY_COLORS[4]


def _render_bar_row(
    label: str,
    value: int,
    max_value: int,
    *,
    label_width: int,
    marker: str | None = None,
) -> Text:
    row = Text()
    row.append(f"  {label:<{label_width}} ", style="dim")

    if value <= 0:
        row.append(" " * BAR_WIDTH)
    else:
        bar_len = max(1, round(value / max_value * BAR_WIDTH))
        row.append("█" * bar_len, style=_get_bar_color(value, max_value))
        row.append(" " * (BAR_WIDTH - bar_len))

    row.append("  ")
    row.append(f"{value:>4}", style="dim" if value > 0 else "bright_black")
    if marker:
        row.append(f" {marker}", style="bold bright_green")
    return row


def _parse_entry_date(entry: dict) -> str | None:
    timestamp = entry.get("timestamp", "")
    if not isinstance(timestamp, str) or len(timestamp) < 10:
        return None
    return timestamp[:10]


def _get_duration_ms(entry: dict) -> int | None:
    duration = entry.get("recording_duration_ms")
    if isinstance(duration, int) and duration >= 0:
        return duration
    return None


def _get_word_count(entry: dict) -> int:
    words = entry.get("transcript_words")
    if isinstance(words, int) and words >= 0:
        return words
    return 0


def _build_sparkline(values: list[float]) -> str:
    if not values:
        return ""

    low = min(values)
    high = max(values)
    if high <= 0:
        return SPARKLINE_CHARS[0] * len(values)
    if high == low:
        return SPARKLINE_CHARS[-1] * len(values)

    blocks: list[str] = []
    for value in values:
        ratio = (value - low) / (high - low)
        index = min(len(SPARKLINE_CHARS) - 1, round(ratio * (len(SPARKLINE_CHARS) - 1)))
        blocks.append(SPARKLINE_CHARS[index])
    return "".join(blocks)


def _rolling_average(values: list[int], window: int) -> list[float]:
    averaged: list[float] = []
    running_total = 0

    for index, value in enumerate(values):
        running_total += value
        if index >= window:
            running_total -= values[index - window]
        divisor = min(index + 1, window)
        averaged.append(running_total / divisor)

    return averaged


def _format_period_change(
    current: int,
    previous: int,
    formatter: Callable[[int], str] = str,
) -> str:
    current_display = formatter(current)
    previous_display = formatter(previous)

    if previous == 0:
        if current == 0:
            return f"flat ({current_display} vs {previous_display})"
        return f"new ({current_display} vs {previous_display})"

    change = ((current - previous) / previous) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.0f}% ({current_display} vs {previous_display})"


def render_heatmap(
    by_day: dict[str, DayStats],
    num_months: int = 3,
) -> ConsoleRenderable:
    """Render the GitHub-style activity heatmap as a Rich renderable."""
    from rich.console import Group

    parts: list[Text] = []

    if not by_day:
        parts.append(Text("No stats recorded yet. Start dictating!", style="dim"))
        return Group(*parts)

    parts.append(Text(""))
    parts.append(Text("spkezy Activity", style="bold"))
    parts.append(Text(""))

    today = datetime.now(UTC).date()
    start_month = today.month - (num_months - 1)
    start_year = today.year
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    grid_start_date = datetime(start_year, start_month, 1).date()
    days_to_sunday = (grid_start_date.weekday() + 1) % 7
    grid_start = grid_start_date - timedelta(days=days_to_sunday)
    days_since_sunday = (today.weekday() + 1) % 7
    end_of_week = today + timedelta(days=6 - days_since_sunday)
    days_total = (end_of_week - grid_start).days
    num_weeks = (days_total // 7) + 3

    max_count = 0
    day_offsets = [1, 2, 3, 4, 5, 6, 0]  # Mon..Sun relative to Sunday-aligned grid
    for week in range(num_weeks):
        for day_idx in range(7):
            day_date = grid_start + timedelta(weeks=week, days=day_offsets[day_idx])
            if day_date > today:
                continue
            date_str = day_date.strftime("%Y-%m-%d")
            count = by_day.get(date_str, DayStats(date_str)).count
            if count > max_count:
                max_count = count

    thresholds = _get_heatmap_thresholds(max_count)

    month_names = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    month_positions: list[tuple[int, str]] = []
    last_month = -1
    for week in range(num_weeks):
        week_date = grid_start + timedelta(weeks=week, days=1)
        month = week_date.month
        if month != last_month:
            month_positions.append((week, month_names[month - 1]))
            last_month = month

    month_chars = [" "] * num_weeks
    last_end = -1
    for pos, name in month_positions:
        if pos > last_end and pos + len(name) <= num_weeks:
            for i, char in enumerate(name):
                month_chars[pos + i] = char
            last_end = pos + len(name)

    month_row = Text()
    month_row.append("    ", style="dim")
    month_row.append("".join(month_chars), style="dim")
    parts.append(month_row)

    for day_idx, day_label in enumerate(WEEKDAY_LABELS):
        row = Text()
        row.append(f"{day_label:3} ", style="dim")
        for week in range(num_weeks):
            day_date = grid_start + timedelta(weeks=week, days=day_offsets[day_idx])
            if day_date > today:
                row.append(" ")
            else:
                date_str = day_date.strftime("%Y-%m-%d")
                count = by_day.get(date_str, DayStats(date_str)).count
                intensity = _get_heatmap_intensity(count, thresholds)
                row.append(
                    HEATMAP_INTENSITY_CHARS[intensity],
                    style=HEATMAP_INTENSITY_COLORS[intensity],
                )
        parts.append(row)

    parts.append(Text(""))
    legend = Text()
    legend.append("Legend:   ", style="dim")
    legend.append("none", style=HEATMAP_INTENSITY_COLORS[0])
    prev = 0
    for index, threshold in enumerate(thresholds, start=1):
        low = prev + 1
        range_label = f"{low}" if low == threshold else f"{low}-{threshold}"
        legend.append("  ", style="dim")
        legend.append(HEATMAP_INTENSITY_CHARS[index], style=HEATMAP_INTENSITY_COLORS[index])
        legend.append(f" {range_label}", style="dim")
        prev = threshold
    parts.append(legend)

    return Group(*parts)


def render_summary(by_day: dict[str, DayStats]) -> ConsoleRenderable:
    """Render the summary table with period breakdowns and streaks."""
    from rich.console import Group
    from rich.table import Table

    parts: list[ConsoleRenderable] = []

    if not by_day:
        return Text("No stats recorded yet. Start dictating!", style="dim")

    today = datetime.now(UTC).date()
    today_str = today.strftime("%Y-%m-%d")
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")

    today_stats = by_day.get(today_str, DayStats(today_str))
    week_stats = DayStats("week")
    month_stats = DayStats("month")
    all_stats = DayStats("all")

    for date, day in by_day.items():
        all_stats.count += day.count
        all_stats.recording_ms += day.recording_ms
        all_stats.words += day.words
        if date >= week_ago:
            week_stats.count += day.count
            week_stats.recording_ms += day.recording_ms
            week_stats.words += day.words
        if date >= month_ago:
            month_stats.count += day.count
            month_stats.recording_ms += day.recording_ms
            month_stats.words += day.words

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Period", style="dim")
    table.add_column("Recordings", justify="right")
    table.add_column("Audio", justify="right")
    table.add_column("Words", justify="right")

    for label, stats in [
        ("Today", today_stats),
        ("This week", week_stats),
        ("This month", month_stats),
        ("All time", all_stats),
    ]:
        table.add_row(
            label,
            str(stats.count),
            format_duration(stats.recording_ms),
            f"{stats.words:,}",
        )

    parts.append(Text(""))
    parts.append(Text("Summary", style="bold"))
    parts.append(table)
    parts.append(Text(""))

    current_streak, longest_streak = calculate_streaks(set(by_day.keys()))
    streak_text = Text()
    streak_text.append("Current streak: ", style="bold")
    streak_text.append(f"{current_streak} days")
    parts.append(streak_text)
    longest_text = Text()
    longest_text.append("Longest streak: ", style="bold")
    longest_text.append(f"{longest_streak} days")
    parts.append(longest_text)

    return Group(*parts)


def calculate_hourly_counts(entries: list[dict]) -> list[int]:
    """Aggregate activity counts by hour of day."""
    hourly_counts = [0] * 24
    for entry in entries:
        timestamp = entry.get("timestamp", "")
        try:
            hour = int(timestamp[11:13])
        except (ValueError, IndexError):
            continue
        if 0 <= hour < 24:
            hourly_counts[hour] += 1
    return hourly_counts


def render_hourly(entries: list[dict]) -> ConsoleRenderable:
    """Render a horizontal bar chart of activity by hour-of-day."""
    from rich.console import Group

    parts: list[Text] = []
    parts.append(Text(""))
    parts.append(Text("Hourly Activity", style="bold"))
    parts.append(Text(""))

    if not entries:
        parts.append(Text("No stats recorded yet. Start dictating!", style="dim"))
        return Group(*parts)

    hourly_counts = calculate_hourly_counts(entries)
    max_count = max(hourly_counts) if hourly_counts else 0
    if max_count == 0:
        parts.append(Text("No activity data.", style="dim"))
        return Group(*parts)

    peak_hour = max(range(24), key=lambda hour: hourly_counts[hour])

    for hour, count in enumerate(hourly_counts):
        marker = "peak" if hour == peak_hour and count > 0 else None
        parts.append(
            _render_bar_row(
                f"{hour:02d}:00",
                count,
                max_count,
                label_width=5,
                marker=marker,
            )
        )

    return Group(*parts)


def render_hourly_summary(entries: list[dict]) -> Text:
    """Render a compact hourly activity summary."""
    counts = calculate_hourly_counts(entries)
    total = sum(counts)
    if total == 0:
        return Text("No activity data yet.", style="dim")

    peak_hour = max(range(24), key=lambda hour: counts[hour])
    active_hours = sum(1 for count in counts if count > 0)
    busiest_hours = [
        hour
        for hour in sorted(range(24), key=lambda hour: counts[hour], reverse=True)
        if counts[hour]
    ]

    summary = Text()
    summary.append("Peak hour: ", style="bold")
    summary.append(f"{peak_hour:02d}:00 ({counts[peak_hour]} recordings)")
    summary.append("  •  ")
    summary.append("Active hours: ", style="bold")
    summary.append(str(active_hours))
    if busiest_hours:
        top_hours = ", ".join(f"{hour:02d}:00 ({counts[hour]})" for hour in busiest_hours[:3])
        summary.append("  •  ")
        summary.append("Top slots: ", style="bold")
        summary.append(top_hours)
    return summary


def calculate_duration_distribution(entries: list[dict]) -> tuple[list[tuple[str, int]], list[int]]:
    """Bucket recordings by duration."""
    counts = [0] * len(DURATION_BUCKETS)
    durations: list[int] = []

    for entry in entries:
        duration = _get_duration_ms(entry)
        if duration is None:
            continue
        durations.append(duration)
        for index, (_, start_ms, end_ms) in enumerate(DURATION_BUCKETS):
            if duration < start_ms:
                continue
            if end_ms is None or duration < end_ms:
                counts[index] += 1
                break

    buckets = [(label, counts[index]) for index, (label, _, _) in enumerate(DURATION_BUCKETS)]
    return buckets, durations


def render_duration_distribution(entries: list[dict]) -> ConsoleRenderable:
    """Render a histogram of recording lengths."""
    from rich.console import Group

    parts: list[Text] = []
    parts.append(Text(""))
    parts.append(Text("Recording Length", style="bold"))
    parts.append(Text(""))

    buckets, durations = calculate_duration_distribution(entries)
    if not durations:
        parts.append(Text("No stats recorded yet. Start dictating!", style="dim"))
        return Group(*parts)

    max_count = max(count for _, count in buckets)
    peak_label = max(buckets, key=lambda bucket: bucket[1])[0]
    label_width = max(len(label) for label, _ in buckets)

    for label, count in buckets:
        marker = "peak" if count > 0 and label == peak_label else None
        parts.append(
            _render_bar_row(
                label,
                count,
                max_count,
                label_width=label_width,
                marker=marker,
            )
        )

    parts.append(Text(""))
    summary = Text()
    summary.append("Median: ", style="bold")
    summary.append(format_duration(int(median(durations))))
    summary.append("  •  ")
    summary.append("Average: ", style="bold")
    summary.append(format_duration(int(mean(durations))))
    summary.append("  •  ")
    summary.append("Longest: ", style="bold")
    summary.append(format_duration(max(durations)))
    parts.append(summary)

    return Group(*parts)


def calculate_weekday_counts(entries: list[dict]) -> list[int]:
    """Aggregate activity counts by weekday."""
    counts = [0] * 7
    for entry in entries:
        date_str = _parse_entry_date(entry)
        if date_str is None:
            continue
        try:
            weekday = datetime.strptime(date_str, "%Y-%m-%d").weekday()
        except ValueError:
            continue
        counts[weekday] += 1
    return counts


def render_weekday_profile(entries: list[dict]) -> ConsoleRenderable:
    """Render activity counts by weekday."""
    from rich.console import Group

    parts: list[Text] = []
    parts.append(Text(""))
    parts.append(Text("Weekday Profile", style="bold"))
    parts.append(Text(""))

    counts = calculate_weekday_counts(entries)
    total = sum(counts)
    if total == 0:
        parts.append(Text("No stats recorded yet. Start dictating!", style="dim"))
        return Group(*parts)

    peak_day = max(range(7), key=lambda index: counts[index])
    max_count = max(counts)

    for index, label in enumerate(WEEKDAY_LABELS):
        marker = "best" if index == peak_day and counts[index] > 0 else None
        parts.append(
            _render_bar_row(
                label,
                counts[index],
                max_count,
                label_width=3,
                marker=marker,
            )
        )

    weekend_total = counts[5] + counts[6]
    weekend_share = (weekend_total / total) * 100 if total else 0
    parts.append(Text(""))
    summary = Text()
    summary.append("Best day: ", style="bold")
    summary.append(WEEKDAY_LABELS[peak_day])
    summary.append("  •  ")
    summary.append("Weekend share: ", style="bold")
    summary.append(f"{weekend_share:.0f}%")
    parts.append(summary)

    return Group(*parts)


def calculate_rolling_trend(
    entries: list[dict],
    *,
    days: int = 28,
    window: int = 7,
) -> dict[str, list[int]]:
    """Build per-day recordings, word, and audio series for the trailing window."""
    today = datetime.now(UTC).date()
    start_day = today - timedelta(days=days - 1)

    recordings = [0] * days
    words = [0] * days
    audio_ms = [0] * days

    for entry in entries:
        date_str = _parse_entry_date(entry)
        if date_str is None:
            continue
        try:
            entry_day = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if entry_day < start_day or entry_day > today:
            continue

        index = (entry_day - start_day).days
        recordings[index] += 1
        words[index] += _get_word_count(entry)
        duration = _get_duration_ms(entry)
        if duration is not None:
            audio_ms[index] += duration

    result = {
        "recordings": recordings,
        "words": words,
        "audio_ms": audio_ms,
    }
    result["recordings_rolling"] = [int(value) for value in _rolling_average(recordings, window)]
    result["words_rolling"] = [int(value) for value in _rolling_average(words, window)]
    result["audio_ms_rolling"] = [int(value) for value in _rolling_average(audio_ms, window)]
    return result


def render_rolling_trend(
    entries: list[dict],
    *,
    days: int = 28,
    window: int = 7,
) -> ConsoleRenderable:
    """Render rolling usage trends across the trailing window."""
    from rich.console import Group

    parts: list[Text] = []
    parts.append(Text(""))
    parts.append(Text("Rolling Trend", style="bold"))
    parts.append(Text(f"Last {days} days · {window}-day rolling average", style="dim"))
    parts.append(Text(""))

    trends = calculate_rolling_trend(entries, days=days, window=window)
    if sum(trends["recordings"]) == 0:
        parts.append(Text("No stats recorded yet. Start dictating!", style="dim"))
        return Group(*parts)

    for label, rolling_key, totals_key, formatter in [
        ("Recordings", "recordings_rolling", "recordings", str),
        ("Words", "words_rolling", "words", str),
        ("Audio", "audio_ms_rolling", "audio_ms", format_duration),
    ]:
        line = Text()
        line.append(f"  {label:<11}", style="bold")
        sparkline = _build_sparkline([float(value) for value in trends[rolling_key]])
        line.append(sparkline, style="bright_green")
        line.append("  ")
        line.append(f"{window}d: ", style="bold")
        line.append(formatter(sum(trends[totals_key][-window:])))
        parts.append(line)

    parts.append(Text(""))
    parts.append(Text(f"This {window}d vs previous {window}d", style="bold"))

    for label, values, formatter in [
        ("Recordings", trends["recordings"], str),
        ("Words", trends["words"], str),
        ("Audio", trends["audio_ms"], format_duration),
    ]:
        current = sum(values[-window:])
        previous = sum(values[-window * 2 : -window])
        line = Text()
        line.append(f"  {label:<11}", style="dim")
        line.append(_format_period_change(current, previous, formatter))
        parts.append(line)

    return Group(*parts)


class SpkezyStatsApp(App[None]):
    """Textual app for browsing spkezy stats."""

    TITLE = "spkezy stats"
    SUB_TITLE = "Usage dashboard"
    CSS = """
    Screen {
        layout: vertical;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 1 2;
    }

    VerticalScroll {
        height: 1fr;
    }

    #transcripts-pane {
        height: 1fr;
    }

    #transcripts-log {
        height: 1fr;
        border: round $surface;
        padding: 0 1;
    }

    #hourly-sparkline {
        height: 4;
        margin: 1 0;
    }

    .pane-title {
        text-style: bold;
        margin-bottom: 1;
    }
    """
    BINDINGS = [
        ("h", "show_view('heatmap')", "Heatmap"),
        ("s", "show_view('summary')", "Summary"),
        ("a", "show_view('hourly')", "Hourly"),
        ("d", "show_view('duration')", "Duration"),
        ("w", "show_view('weekday')", "Weekday"),
        ("r", "show_view('trend')", "Trend"),
        ("t", "show_view('transcripts')", "Transcripts"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        *,
        entries: list[dict],
        transcripts: list[dict],
        num_months: int = 3,
    ) -> None:
        super().__init__()
        self.entries = entries
        self.transcripts = transcripts
        self.by_day = aggregate_by_day(entries)
        self.num_months = num_months

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="heatmap", id="views"):
            with TabPane("Heatmap", id="heatmap"):
                with VerticalScroll():
                    yield Static(id="heatmap-view")
            with TabPane("Summary", id="summary"):
                with VerticalScroll():
                    yield Static(id="summary-view")
            with TabPane("Hourly", id="hourly"):
                with VerticalScroll():
                    yield Static(id="hourly-summary")
                    yield Sparkline(id="hourly-sparkline")
                    yield Static(id="hourly-view")
            with TabPane("Duration", id="duration"):
                with VerticalScroll():
                    yield Static(id="duration-view")
            with TabPane("Weekday", id="weekday"):
                with VerticalScroll():
                    yield Static(id="weekday-view")
            with TabPane("Trend", id="trend"):
                with VerticalScroll():
                    yield Static(id="trend-view")
            with TabPane("Transcripts", id="transcripts"):
                with Vertical(id="transcripts-pane"):
                    yield Static("Recent Transcripts", classes="pane-title")
                    yield RichLog(id="transcripts-log", wrap=True, auto_scroll=True)
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = f"{len(self.entries):,} recordings"
        self.query_one("#heatmap-view", Static).update(render_heatmap(self.by_day, self.num_months))
        self.query_one("#summary-view", Static).update(render_summary(self.by_day))
        self.query_one("#hourly-summary", Static).update(render_hourly_summary(self.entries))
        self.query_one("#hourly-sparkline", Sparkline).data = calculate_hourly_counts(self.entries)
        self.query_one("#hourly-view", Static).update(render_hourly(self.entries))
        self.query_one("#duration-view", Static).update(render_duration_distribution(self.entries))
        self.query_one("#weekday-view", Static).update(render_weekday_profile(self.entries))
        self.query_one("#trend-view", Static).update(render_rolling_trend(self.entries))
        self._populate_transcripts_log()
        self.query_one(TabbedContent).focus()

    def action_show_view(self, view: str) -> None:
        """Switch the active tab."""
        self.query_one(TabbedContent).active = view

    def _populate_transcripts_log(self) -> None:
        log = self.query_one("#transcripts-log", RichLog)
        log.clear()

        if not self.transcripts:
            log.write(Text("No transcripts stored yet.", style="dim"))
            return

        for entry in reversed(self.transcripts):
            timestamp = entry.get("timestamp", "")
            transcript = entry.get("text", "")
            line = Text()
            line.append(timestamp or "unknown time", style="dim")
            line.append("  ")
            line.append(transcript)
            log.write(line)


def run_tui(num_months: int = 3) -> None:
    """Run the interactive stats TUI."""
    app = SpkezyStatsApp(
        entries=load_all_stats(),
        transcripts=load_transcripts(limit=200),
        num_months=num_months,
    )
    app.run()
