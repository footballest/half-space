# Phase 1b Handoff — Kaggle CC0 Data Source (xG, team stats, referees, altitude)

## Goal
Add a **second Track A source** alongside openfootball: the CC0-licensed Kaggle "FIFA World Cup
2026" dataset by MD Mominul Islam. openfootball gives results + goals but **no xG**; this adds
expected goals, per-team match stats, referees, stadium altitude, and squads. Normalize the
pieces we need into tidy Parquet tables that join to the existing `matches` table.

## Before you start
Read `CLAUDE.md`. Phase 1 (openfootball collector + daily Action) is done and committed. This
phase **adds a new collector module; it must not change the openfootball collector or its tables.**
Show the plan and diffs before committing.

## The data source — pinned
- **Kaggle dataset slug: `mominullptr/fifa-world-cup-2026-dataset`**
  (https://www.kaggle.com/datasets/mominullptr/fifa-world-cup-2026-dataset)
- License: **CC0-1.0** (public domain). Community-maintained, updated daily after matches.
- Fetch via the Kaggle API — the human has a token at `~/.kaggle/kaggle.json`. Use the `kaggle`
  CLI/API:
  ```bash
  uv run --with kaggle kaggle datasets download -d mominullptr/fifa-world-cup-2026-dataset \
      -p data/raw/kaggle_wc2026/ --unzip
  ```
  (Add `kaggle` to the project deps if you prefer, but `--with` keeps it out of the base set.)
- Save the downloaded CSVs **untouched** under `data/raw/kaggle_wc2026/` (raw is immutable).
- **Confirm the real files/columns before writing normalizers** — the schema below is from the
  dataset's README and may have drifted.

### Known files (from the dataset README)
- `matches.csv` — outcomes, dates, times, scores, `home_xg`/`away_xg`, statuses; relational IDs
  (`stage_id`, `venue_id`, `home_team_id`, `away_team_id`, `referee_id`).
- `matches_detailed.csv` — **denormalized** version with human-readable names
  (`home_team_name`, `stadium_name`, `city`, `referee_name`). **Prefer this for joining** —
  it avoids chasing ID foreign keys.
- `match_team_stats.csv` — per-team per-match: possession %, shots, shots on target, corners,
  fouls, offsides, saves (+ `data_source`, `last_updated`).
- `match_events.csv` — minute-level events (goals, assists, cards, VAR) mapped to matches/players.
  NOTE: this is minute-level, NOT coordinate-level event data. In scope only for card/VAR posts.
- `venues.csv` — `stadium_name`, `city`, `country`, `capacity`, `latitude`, `longitude`,
  **`elevation_meters`** (the altitude angle).
- `referees.csv` — `name`, `country`, `avg_cards_per_game`.
- `squads_and_players.csv` — 1,248 players with `market_value_eur`, `position`, `club_team`, caps.

## Scope — keep it tight
Produce these Parquet tables under `data/processed/`:
- `team_match_stats.parquet` — one row per team per match: our `match_id` (see join note), team,
  xg, possession, shots, shots_on_target, corners, fouls, offsides, saves.
- `venues.parquet` — name, city, country, latitude, longitude, elevation_m.
- `referees.parquet` — name, country, avg_cards_per_game.

Skip `squads_and_players` and `match_events` normalization for now (out of scope; revisit when a
post needs market values or card timelines).

## The hard part — joining to openfootball
The Kaggle set has its **own** match ids; our `matches.parquet` keys off openfootball (`num` for
knockout, `date_team1_vs_team2` slug for group). Build a **crosswalk**, don't assume ids align:
- Join on `date` + the two team names, using `matches_detailed.csv` for readable names.
- **Normalize team-name spelling differences** between sources — build a small alias map
  (e.g. "USA"/"United States", "South Korea"/"Korea Republic", "Czechia"/"Czech Republic",
  "Türkiye"/"Turkey", "Côte d'Ivoire"/"Ivory Coast"). openfootball and this set won't spell every
  nation identically.
- Produce `match_crosswalk.parquet` mapping Kaggle match -> our openfootball `match_id`, and add a
  resolved `match_id` column to the processed tables.
- **Report matches that fail to join** (print a count + the unmatched rows) rather than silently
  dropping them — we need to see coverage gaps.

## Data-quality sanity check (do this, report the result)
This is a community dataset; xG is from "verified providers", not official FIFA. Spot-check it:
- Pick ~5 completed matches and compare their `home_xg`/`away_xg` against a public WC2026 xG
  tracker (RealGM: soccer.realgm.com xG tracker; or FotMob WC2026 xG table).
- Report whether values are broadly consistent (same ballpark) or materially off. If they diverge
  a lot, flag it — we may caveat or avoid xG-heavy claims.

## Where the code goes
- `src/fsc/collectors/kaggle_wc2026.py` — loader + normalizers + `run()` + `main()`
  (`python -m fsc.collectors.kaggle_wc2026`).
- Reuse `fsc.utils.paths`. Put the team-name alias map somewhere reusable (e.g.
  `src/fsc/utils/teams.py`) since Track B will need the same aliases later.

## Tests — `tests/test_kaggle_wc2026.py`
Inline fixtures (no network / no Kaggle download): tiny team-stats + venues + detailed-matches
frames. Assert normalizers produce expected columns/dtypes (xg float, elevation_m int), and that
the crosswalk matches rows including one needing a team-name alias and flags an unmatchable row.

## Acceptance criteria
```bash
uv run python -m fsc.collectors.kaggle_wc2026
uv run pytest
uv run ruff check . && uv run ruff format --check .
```
Done when: raw CSVs saved under `data/raw/kaggle_wc2026/`; the three processed tables + crosswalk
written; the run prints a summary INCLUDING **join coverage** (e.g. "90/96 played matches matched
to xG; 6 unmatched: …") and the xG sanity-check result; tests pass; ruff clean; openfootball
collector unchanged.

## Raw-data commit decision (size-based)
Check the downloaded size. If the CSVs are small (a few MB), committing them gives version history
— fine. If large, git-ignore `data/raw/kaggle_wc2026/` and document the fetch command instead.
Report the size and your recommendation.

## Licensing / attribution
CC0 — no attribution legally required, but add the source + author (MD Mominul Islam) to the
README's data-sources section for good practice.

## Out of scope
- StatsBomb-style coordinate-level event data (doesn't exist free for WC2026; that's Track B on
  2018/2022 data later).
- FIFA PMSR physical data (a later, separate source).
- Squads/players and match_events normalization.
- Any charts or posts (Phase 2).

## When done
Summarize, show the join-coverage numbers and the xG sanity-check result, note the raw-data commit
decision, and stop before committing.