# Phase 1b Handoff — Kaggle CC0 Data Source (xG, team stats, referees, altitude)

## Goal
Add a **second Track A source** alongside openfootball: the CC0-licensed Kaggle "FIFA World Cup
2026" dataset. openfootball gives results + goals but **no xG**; Kaggle adds expected goals,
per-team match stats, referees, squads, and stadium coordinates/altitude. Normalize the pieces we
need into tidy Parquet tables that join to the existing `matches` table.

## Before you start
Read `CLAUDE.md`. Phase 1 (openfootball collector + daily Action) is done and committed. This
phase **adds a new collector module; it must not change the openfootball collector or its tables.**
Show the plan and diffs before committing.

## The data source — confirm first
- Kaggle dataset: "FIFA World Cup 2026" — a relational CC0 set (CSV files), updated with real
  results. Public-domain (CC0-1.0). Tables include (names to confirm from the actual download):
  teams, venues (with latitude/longitude/elevation), referees, squads/players, matches (with
  home/away xG), match_events, and match_team_stats (possession, shots, corners, etc.).
- **First step: obtain the dataset and inspect the real files and columns before writing anything.**
  Do not assume column names. Options for fetching, in order of preference:
  1. If a `KAGGLE_USERNAME` / `KAGGLE_KEY` is available in the environment, use the `kaggle` CLI /
     API to download it.
  2. Otherwise, the human will download the CSVs manually and place them under
     `data/raw/kaggle_wc2026/` — **ask the human which applies before proceeding.**
- Save whatever is fetched **untouched** under `data/raw/kaggle_wc2026/` (raw is immutable). Note
  the dataset's own version/date if available.

## Scope — keep it tight
Normalize only what unlocks the near-term blog posts. Produce these Parquet tables under
`data/processed/`:
- `team_match_stats.parquet` — one row per team per match: `match_id` (see join note), team,
  xg, possession, shots, shots_on_target, corners, and whatever else is cleanly available.
- `venues.parquet` — one row per venue: name, city, country, latitude, longitude, elevation_m.
- `referees.parquet` — one row per referee: name, country, avg_cards_per_game (if present).

Skip squads/players and event-level Kaggle data for now (out of scope; revisit if a post needs it).

## The hard part — joining to openfootball
The Kaggle set has its **own** match identifiers; our `matches.parquet` keys off openfootball
(`num` for knockout, `date_team1_vs_team2` slug for group). Build a **join/crosswalk** rather than
assuming ids line up:
- Match on `date` + the two team names (normalize team-name spelling differences between sources —
  e.g. "USA"/"United States", "South Korea"/"Korea Republic"; build a small alias map).
- Produce a `match_crosswalk.parquet` (or a resolved `match_id` column on the Kaggle tables) mapping
  Kaggle match → our openfootball `match_id`.
- **Report any matches that fail to join** (print a count + the unmatched rows) rather than silently
  dropping them — we need to see coverage gaps.

## Where the code goes
- `src/fsc/collectors/kaggle_wc2026.py` — loader + normalizers + `run()` + `main()`
  (`python -m fsc.collectors.kaggle_wc2026`).
- Reuse `fsc.utils.paths`. Add a small team-name alias helper (in `utils/` if reusable).

## Tests — `tests/test_kaggle_wc2026.py`
Inline fixtures (no network / no Kaggle download): tiny team-stats + venues frames. Assert the
normalizers produce the expected columns and dtypes (xG float, elevation int), and that the
crosswalk correctly matches a couple of rows including one needing a team-name alias, and flags an
unmatchable row.

## Acceptance criteria
```bash
uv run python -m fsc.collectors.kaggle_wc2026
uv run pytest
uv run ruff check . && uv run ruff format --check .
```
Done when: raw Kaggle files are saved under `data/raw/kaggle_wc2026/`; the three processed tables
+ crosswalk are written; the run prints a summary including **join coverage** (e.g. "88/96 played
matches matched to xG; 8 unmatched: …"); tests pass; ruff clean; openfootball collector unchanged.

## Licensing / attribution
CC0 (public domain) — no attribution legally required, but note the source in the README's data
section for good practice. Do **not** commit the raw Kaggle CSVs if they're large; check size — if
they're small (a few MB) committing is fine and gives history, otherwise git-ignore
`data/raw/kaggle_wc2026/` and document how to fetch. Decide based on actual size and tell the human.

## Out of scope
- FIFA PMSR physical data (a later, separate source).
- Squads/players and Kaggle event data.
- Any charts or posts (Phase 2).

## When done
Summarize, show the join-coverage numbers, and note the raw-data commit decision (size-based).
Stop before committing.