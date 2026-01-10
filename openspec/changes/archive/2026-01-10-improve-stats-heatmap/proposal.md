# Change: Improve stats heatmap visualization

## Why

The current heatmap uses ASCII characters (`. : + #`) that are hard to see and don't fill the cell space, making the activity grid sparse and difficult to read at a glance.

## What Changes

- Replace ASCII intensity characters with Unicode block characters (`░▒▓█`) that fill the cell
- Add color gradient (green intensity) to blocks based on activity level
- Keep same activity thresholds (0, 1-2, 3-5, 6-10, 11+)
- Update legend to match new symbols

## Impact

- Affected specs: stats (new capability)
- Affected code: `spkezy_stats.py` (~10 lines changed)
