# stats Specification

## Purpose

Usage statistics collection and visualization for spkezy, including activity heatmap and summary metrics.

## ADDED Requirements

### Requirement: Activity heatmap uses block characters

The activity heatmap SHALL use Unicode block characters (`░▒▓█`) to represent daily activity intensity, providing a visually dense and readable grid.

#### Scenario: User views stats with activity

- **WHEN** user runs `make stats` with recorded activity
- **THEN** the heatmap displays filled block characters colored by intensity:
  - Empty cell (space) for days with 0 recordings
  - `░` (light shade) for 1-2 recordings
  - `▒` (medium shade) for 3-5 recordings
  - `▓` (dark shade) for 6-10 recordings
  - `█` (full block) for 11+ recordings

#### Scenario: Legend displays block characters

- **WHEN** user views the heatmap legend
- **THEN** the legend shows: `Legend:   none  ░ 1-2  ▒ 3-5  ▓ 6-10  █ 11+`

### Requirement: Heatmap cells are color-coded by intensity

The heatmap cells SHALL use a green color gradient where higher activity shows brighter/bolder green.

#### Scenario: Color intensity matches activity level

- **WHEN** displaying heatmap cells
- **THEN** colors progress from dim to bright green as activity increases:
  - 0 recordings: no display (empty)
  - 1-2: dim green
  - 3-5: green
  - 6-10: bright green
  - 11+: bold bright green
