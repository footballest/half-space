# Phase 2a Handoff — EDA Starter Notebook (Track A)

## Goal
Scaffold an exploratory-analysis notebook that loads our processed tables and seeds a few
candidate story angles — so the human can then explore hands-on and pick what becomes the first
blog post. **You build the runnable scaffold; the human does the actual exploring.** Do NOT
draw conclusions or write a "finding" — set up the ground so exploration is friction-free.

## Before you start
Read `CLAUDE.md`. Phases 1 / 1b are done: we have processed Parquet tables from two sources.
This phase creates ONE notebook. No changes to collectors, package code, or data.

## Where it goes
`notebooks/trackA/01_eda_wc2026.ipynb`

Build it as a real `.ipynb` (so it opens in VS Code / Jupyter). If easier to author as a
`jupytext`-style `.py` percent script and convert, that's fine — final artifact must be the
`.ipynb`, and every cell must run top-to-bottom without error.

## The data (all under `data/processed/`)
- `matches.parquet` — one row per match (openfootball): match_id, round, stage, group, date,
  team1/team2, ft1/ft2, ht/et/p scores, status, is_placeholder, venue.
- `goals.parquet` — one row per goal: match_id, team, side, scorer, minute, penalty, owngoal.
- `team_match_stats.parquet` — one row per team per match (Kaggle): match_id, team, side, xg,
  possession, shots, shots_on_target, corners, fouls, offsides, saves.
- `venues.parquet` — name, city, country, capacity, latitude, longitude, elevation_m.
- `referees.parquet` — name, country, avg_cards_per_game.
- `match_crosswalk.parquet` — kaggle_match_id <-> our match_id.

Join key throughout is our `match_id`. `team_match_stats` already carries it.

## Notebook structure (sections as markdown+code cells)

### 0. Setup
Imports (pandas, numpy, matplotlib; use `fsc.utils.paths.PROCESSED` for paths — no hardcoded
paths). A small `load(name)` helper that reads a processed parquet by name. Load all six tables
and print shape + `.head()` + dtypes for each so the human sees what's there.

### 1. Data health / sanity
Quick orientation, not analysis: how many matches played vs scheduled; goals per match
distribution; any nulls in key columns; confirm `team_match_stats` has 2 rows per played match;
list the distinct `round` values so knockout vs group is clear.

### 2-5. Candidate angles — one section each
For EACH angle: a short markdown cell stating the question + which columns it uses, then 1-2
code cells that compute the starter view and make ONE simple plot. Leave it open-ended — end
each section with a markdown "Explore further:" list of 2-3 follow-up questions, NOT a conclusion.

Seed these four:

**A. xG justice table (over/under-performance).** Per team, sum xg vs actual goals across their
matches; who most over/under-performed their xG. Bar chart of (goals - xG). Caveat in markdown:
this dataset's xG is directionally reliable but not identical to other providers' models — frame
as "chance quality", not canonical xG.

**B. Altitude angle.** Join matches -> venues via venue/stadium to attach `elevation_m` per match.
Mexico City ~2200m vs most venues near sea level. Starter views: goals-per-match and total shots
by elevation bucket; second-half vs first-half goal share by elevation (does scoring fade at
altitude?). Scatter elevation vs goals. Flag small-sample caution (few high-altitude matches).

**C. Referee card patterns.** From referees + (if joinable) match assignments: distribution of
avg_cards_per_game; if match-referee links exist, cards/fouls by referee. Keep exploratory.

**D. Efficiency: possession vs xG vs result.** Does more possession mean more xG? Do high-possession
teams win? Scatter possession vs xg, colored by win/draw/loss.

### 6. Scratch
An empty section header for the human to take over.

## Constraints
- Every cell runs clean top-to-bottom. Restart-and-run-all before you're done.
- Plots simple (matplotlib defaults fine) — this is EDA, not design.
- No new dependencies beyond what's installed (pandas, numpy, matplotlib are in base+dev... 
  confirm matplotlib is available; it's in the `viz` extra — if not present, either add a
  `uv sync --extra viz` note at the top or keep plots to pandas `.plot()`).
- Do NOT write blog prose or declare a "winning" angle. The human decides after exploring.

## When done
Print/confirm the notebook runs clean end-to-end (e.g. `uv run jupyter nbconvert --to notebook
--execute --inplace notebooks/trackA/01_eda_wc2026.ipynb` succeeds). Summarize the four seeded
angles in one line each and STOP. Don't commit — the human will explore first, then commit.