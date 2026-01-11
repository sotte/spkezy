"""Stats collection and viewing for spkezy."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from spkezy.runtime import get_data_dir, load_toml_config


@dataclass
class StatsConfig:
    """Configuration for stats storage."""

    store_transcripts: bool = True


def load_stats_config(log: Any | None = None) -> StatsConfig:
    data = load_toml_config(log)
    config = StatsConfig()
    stats_section = data.get("stats")
    if isinstance(stats_section, dict):
        store_transcripts = stats_section.get("store_transcripts")
        if isinstance(store_transcripts, bool):
            config.store_transcripts = store_transcripts
    return config


def record_stats(
    recording_duration_ms: int,
    transcription_duration_ms: int,
    transcript: str,
    device: str,
) -> None:
    """Record a transcription event to daily JSONL files."""
    config = load_stats_config()
    base_path = get_data_dir()
    stats_dir = base_path / "stats"

    now = datetime.now(UTC)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = now.strftime("%Y-%m-%d")

    # Ensure directories exist
    stats_dir.mkdir(parents=True, exist_ok=True)

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

    if config.store_transcripts:
        transcripts_dir = base_path / "transcripts"
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        # Write transcript entry
        transcript_file = transcripts_dir / f"{date_str}.jsonl"
        transcript_entry = {
            "timestamp": timestamp,
            "text": transcript,
        }
        with open(transcript_file, "a") as f:
            f.write(json.dumps(transcript_entry) + "\n")


@dataclass
class DayStats:
    """Aggregated stats for a single day."""

    date: str
    count: int = 0
    recording_ms: int = 0
    words: int = 0


def load_all_stats() -> list[dict]:
    """Load all stats entries from all daily files."""
    stats_dir = get_data_dir() / "stats"
    entries = []
    if not stats_dir.exists():
        return entries

    for file in sorted(stats_dir.glob("*.jsonl")):
        with open(file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return entries


def aggregate_by_day(entries: list[dict]) -> dict[str, DayStats]:
    """Aggregate stats by day."""
    by_day: dict[str, DayStats] = {}

    for entry in entries:
        date = entry["timestamp"][:10]  # YYYY-MM-DD
        if date not in by_day:
            by_day[date] = DayStats(date=date)
        day = by_day[date]
        day.count += 1
        day.recording_ms += entry.get("recording_duration_ms", 0)
        day.words += entry.get("transcript_words", 0)

    return by_day


def calculate_streaks(dates_with_activity: set[str]) -> tuple[int, int]:
    """Calculate current and longest streaks. Returns (current, longest)."""
    if not dates_with_activity:
        return 0, 0

    today = datetime.now(UTC).date()

    # Current streak: count consecutive days backwards from today
    # (or yesterday if today has no activity)
    current = 0
    today_str = today.strftime("%Y-%m-%d")
    check = today if today_str in dates_with_activity else today - timedelta(days=1)
    while check.strftime("%Y-%m-%d") in dates_with_activity:
        current += 1
        check -= timedelta(days=1)

    # Longest streak: scan all dates
    sorted_dates = sorted(datetime.strptime(d, "%Y-%m-%d").date() for d in dates_with_activity)
    longest = 1
    streak = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            streak += 1
            longest = max(longest, streak)
        else:
            streak = 1

    return current, longest


def format_duration(ms: int) -> str:
    """Format milliseconds as human-readable duration."""
    seconds = ms // 1000
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"


def show_stats(num_months: int = 3) -> None:
    """Render the stats display using Rich (late import)."""
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    console = Console()
    entries = load_all_stats()
    by_day = aggregate_by_day(entries)

    if not entries:
        console.print("[dim]No stats recorded yet. Start dictating![/dim]")
        return

    console.print()
    console.print("[bold]spkezy Activity[/bold]")
    console.print()

    # Build n-month heatmap grid
    today = datetime.now(UTC).date()
    # Go back n-1 months: start from the 1st of that month
    start_month = today.month - (num_months - 1)
    start_year = today.year
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    grid_start_date = datetime(start_year, start_month, 1).date()
    # Find the Sunday before or on grid_start_date
    days_to_sunday = (grid_start_date.weekday() + 1) % 7
    grid_start = grid_start_date - timedelta(days=days_to_sunday)
    # Calculate number of weeks from grid_start to end of current week
    # Add 2 extra weeks to ensure the current month label has room to display
    days_since_sunday = (today.weekday() + 1) % 7
    end_of_week = today + timedelta(days=6 - days_since_sunday)
    days_total = (end_of_week - grid_start).days
    num_weeks = (days_total // 7) + 3  # +3 for month label room

    intensity_chars = [" ", "░", "▒", "▓", "█"]
    intensity_colors = ["bright_black", "dim green", "green", "bright_green", "bold bright_green"]

    def get_intensity(count: int) -> int:
        if count == 0:
            return 0
        if count <= 2:
            return 1
        if count <= 5:
            return 2
        if count <= 10:
            return 3
        return 4

    # Build month labels for x-axis
    # Show month name at first week of each month, spaces elsewhere
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
    month_positions: list[tuple[int, str]] = []  # (week_index, month_name)
    last_month = -1
    for week in range(num_weeks):
        week_date = grid_start + timedelta(weeks=week, days=1)
        month = week_date.month
        if month != last_month:
            month_positions.append((week, month_names[month - 1]))
            last_month = month

    # Build the month label string (num_weeks chars, one per week column)
    # Only place label if there's room (no overlap with previous label)
    month_chars = [" "] * num_weeks
    last_end = -1
    for pos, name in month_positions:
        # Only place if no overlap and full name fits
        if pos > last_end and pos + len(name) <= num_weeks:
            for i, char in enumerate(name):
                month_chars[pos + i] = char
            last_end = pos + len(name)

    month_row = Text()
    month_row.append("    ", style="dim")  # Align with day labels (3 chars + space)
    month_row.append("".join(month_chars), style="dim")
    console.print(month_row)

    # Rows: Mon-Sun (0-6), Cols: num_weeks
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for day_idx, day_label in enumerate(day_labels):
        row = Text()
        row.append(f"{day_label:3} ", style="dim")

        for week in range(num_weeks):
            # grid_start is a Sunday, so +1 for Mon, +2 for Tue, etc.
            day_date = grid_start + timedelta(weeks=week, days=day_idx + 1)
            # Don't show future dates
            if day_date > today:
                row.append(" ")
            else:
                date_str = day_date.strftime("%Y-%m-%d")
                count = by_day.get(date_str, DayStats(date_str)).count
                intensity = get_intensity(count)
                row.append(intensity_chars[intensity], style=intensity_colors[intensity])

        console.print(row)

    console.print()
    console.print("[dim]Legend:   none  ░ 1-2  ▒ 3-5  ▓ 6-10  █ 11+[/dim]")
    console.print()

    # Summary table
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

    table.add_row(
        "Today",
        str(today_stats.count),
        format_duration(today_stats.recording_ms),
        f"{today_stats.words:,}",
    )
    table.add_row(
        "This week",
        str(week_stats.count),
        format_duration(week_stats.recording_ms),
        f"{week_stats.words:,}",
    )
    table.add_row(
        "This month",
        str(month_stats.count),
        format_duration(month_stats.recording_ms),
        f"{month_stats.words:,}",
    )
    table.add_row(
        "All time",
        str(all_stats.count),
        format_duration(all_stats.recording_ms),
        f"{all_stats.words:,}",
    )

    console.print("[bold]Summary[/bold]")
    console.print(table)
    console.print()

    # Streaks
    current_streak, longest_streak = calculate_streaks(set(by_day.keys()))
    console.print(f"[bold]Current streak:[/bold] {current_streak} days")
    console.print(f"[bold]Longest streak:[/bold] {longest_streak} days")
    console.print()


def export_stats_json() -> str:
    """Export all stats as JSON."""
    return json.dumps(load_all_stats(), indent=2)


def clear_stats() -> None:
    """Delete all stats and transcript files."""
    import shutil

    base = get_data_dir()
    for subdir in ["stats", "transcripts"]:
        path = base / subdir
        if path.exists():
            shutil.rmtree(path)
