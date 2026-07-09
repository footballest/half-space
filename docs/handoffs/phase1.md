# Phase 1 Handoff — Live Data Collector (openfootball)

## Goal
Build the Track A backbone: a runnable collector that snapshots the openfootball
World Cup 2026 feed and normalizes it into tidy **Parquet** tables. **openfootball only**
for this increment. **No GitHub Action yet** — we automate after the script works by hand.

## Before you start
Read `CLAUDE.md` and `docs/PROJECT_PLAN.md`. The conventions there apply: `data/raw/` is
immutable, `data/interim/` and `data/processed/` are regenerable, the package is `fsc` under
`src/`, and we build just-in-time. Show the human your plan and your diffs before committing.

## Data source
- URL: `https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json`
- Public domain. A single JSON file containing all 104 matches.
- **First step: fetch it once and print the real structure before writing the normalizer.**
  The shape below is from prior research — confirm field names against the live file,
  especially any extra-time / penalty-shootout encoding, which is uncertain.

### Known shape
```json
{
  "name": "World Cup 2026",
  "matches": [
    { "round": "Matchday 1", "date": "2026-06-11", "time": "13:00 UTC-6",
      "team1": "Mexico", "team2": "South Africa",
      "score": { "ft": [2, 0], "ht": [1, 0] },
      "goals1": [{ "name": "Julián Quiñones", "minute": "9" }],
      "goals2": [], "group": "Group A", "ground": "Mexico City" },

    { "round": "Round of 32", "num": 73, "date": "2026-06-28",
      "team1": "2A", "team2": "2B", "ground": "Los Angeles (Inglewood)" }
  ]
}
```

### Quirks to handle
- `score` is **absent for unplayed matches** → `status = "scheduled"`; present → `"played"`.
- Knockout matches carry `num` (73–104); group matches do **not**.
- Knockout `team1`/`team2` may be **placeholders** (`"2A"` = Group A runner-up, `"W73"` =
  winner of match 73) until they resolve. Flag these rows.
- `group` (e.g. `"Group A"`) is present only for the group stage. For knockout, the stage is
  in `round` (`"Round of 32"`, `"Round of 16"`, `"Quarter-finals"`, `"Semi-finals"`,
  `"Match for third place"`, `"Final"`) — confirm the exact strings from the live data.
- Goals are `{name, minute}` and may include `penalty: true` / `owngoal: true`. `minute` can
  be a string like `"90+9"` — keep the raw string and also parse a numeric base minute.
- Extra time / penalties: inspect `score` for keys such as `et` or `p`/`pen` and handle them
  if present.

## What to build

### 1. Path helper — `src/fsc/utils/paths.py`
A small module resolving repo-root-relative data dirs (`RAW`, `INTERIM`, `PROCESSED`) so no
path is hardcoded to an absolute location. Find the repo root by walking up to the directory
that contains `pyproject.toml`.

### 2. Collector — `src/fsc/collectors/openfootball.py`
Functions:
- `fetch_raw(year=2026, timeout=30) -> dict` — GET the URL with a User-Agent header, a
  timeout, and one retry on failure; return parsed JSON.
- `save_snapshot(raw, snapshot_date=None) -> Path` — write to
  `data/raw/openfootball/worldcup_YYYY-MM-DD.json` (UTC date). One file per day; re-running
  the same day updates that day's file. (Immutability is *across* days; the cron will run once
  daily.)
- `normalize_matches(raw, snapshot_date) -> pd.DataFrame`
- `normalize_goals(raw, snapshot_date) -> pd.DataFrame`
- `run(year=2026)` — orchestrate: fetch → save raw → normalize → write
  `data/processed/matches.parquet` and `data/processed/goals.parquet` → print a one-line
  summary.
- `main()` and `if __name__ == "__main__": main()` so `python -m fsc.collectors.openfootball`
  runs it.

`processed/` is regenerated from the newest snapshot each run (it represents the current
tournament state; `raw/` preserves the daily history).

#### `matches.parquet` — one row per match
`match_id, round, stage (group|knockout), group, date, time, team1, team2, ft1, ft2, ht1,
ht2, status (played|scheduled), is_placeholder (bool), venue, snapshot_date`.
Add extra-time / penalty columns only if those fields exist in the live data.
- `match_id`: use `num` for knockout matches; for group matches synthesize a stable id from
  `date + team1 + team2` (group teams are fixed from the start, so this is stable).

#### `goals.parquet` — one row per goal
`match_id, team (team1|team2), scorer, minute_raw, minute (numeric base), penalty (bool),
owngoal (bool), snapshot_date`.

### 3. Tests — `tests/test_openfootball.py`
Unit tests against a small **inline fixture dict** (no network): one played group match with
two goals (one a penalty), and one unplayed knockout placeholder match. Assert:
- `normalize_matches`: correct row count and columns; `status` derived correctly;
  `is_placeholder` True for the `"2A"`/`"W73"` row; `ft1`/`ft2` null for the unplayed match.
- `normalize_goals`: one row per goal; `penalty` flag parsed; `minute` parsing handles
  `"90+9"`.

## Run / acceptance criteria
```bash
uv run python -m fsc.collectors.openfootball
uv run pytest
uv run ruff check . && uv run ruff format --check .
```
Done when:
- A dated raw JSON exists under `data/raw/openfootball/`.
- `data/processed/matches.parquet` and `goals.parquet` are written.
- The run prints a summary like:
  `Snapshot 2026-07-09: 104 matches (88 played), 241 goals -> data/processed/…`
- `pytest` passes and `ruff` is clean.
- Sanity check reads back sensibly:
  ```bash
  uv run python -c "import pandas as pd; m=pd.read_parquet('data/processed/matches.parquet'); print(m['status'].value_counts()); g=pd.read_parquet('data/processed/goals.parquet'); print(g['scorer'].value_counts().head())"
  ```

## Out of scope (do NOT build yet)
- GitHub Action / cron — the next step, once this runs cleanly by hand.
- Kaggle and FIFA PMSR sources — Phase 1b.
- Any charts or blog posts — Phase 2.

## When done
Summarize what you built and show the diffs. The human commits after review with something
like `git commit -m "Phase 1: openfootball live collector"`, then updates the status line in
`CLAUDE.md` (Phase 1 ✅, Phase 1b next).