# Phase 1b Handoff — Daily Collector Automation (GitHub Action)

## Goal
Automate the Phase 1 collector: a scheduled GitHub Action that runs once daily, executes
`fsc.collectors.openfootball`, and commits any new/changed raw snapshot back to the repo. This
is the "automate once it works by hand" step — the collector already works, so this only wires
the schedule.

## Before you start
Read `CLAUDE.md`. Phase 1 is committed and green. This phase adds **one workflow file** plus a
tiny amount of glue; it must not change collector logic.

## Context that matters
- The tournament is in its final stretch (quarter-finals now, final 2026-07-19), so the point of
  this is to capture the remaining knockout matches automatically.
- Only `data/raw/openfootball/worldcup_YYYY-MM-DD.json` is committed. `data/processed/*.parquet`
  is git-ignored and regenerable, so the Action does **not** commit it.
- The collector writes one snapshot file per UTC day and overwrites it if re-run the same day.

## What to build

### 1. Workflow — `.github/workflows/collect-wc2026.yml`
- **Triggers:** a daily `schedule` (cron) **and** `workflow_dispatch` (so you can run it manually
  to test). Pick a cron time a few hours after typical match completion — suggest once daily around
  06:00 UTC; put the chosen time in a comment.
- **Permissions:** `contents: write` (needed to push the commit).
- **Concurrency:** a `concurrency` group so overlapping runs can't collide.
- **Steps:**
  1. `actions/checkout`.
  2. Install uv (`astral-sh/setup-uv`), enable its cache.
  3. `uv sync` (base + dev only — no `--extra`; the collector needs only base deps).
  4. Run the collector: `uv run python -m fsc.collectors.openfootball`.
  5. Commit the snapshot **only if it changed**: stage `data/raw/openfootball/`, and if
     `git diff --cached --quiet` reports changes, commit with a dated message
     (e.g. `data: openfootball snapshot <date>`) and push; otherwise print "no changes" and exit 0.
     Use a bot identity (`github-actions[bot]`). Do not fail the run when there's nothing to commit.

### 2. Guard rails
- The job must **exit non-zero if the fetch fails** (so a broken feed surfaces), but must **not**
  fail merely because there's nothing new to commit.
- Do not commit `data/processed/` or anything else — stage only `data/raw/openfootball/`.

### 3. Docs
- Add a short "Automation" section to `README.md`: what the Action does, its schedule, and how to
  trigger it manually from the Actions tab.

## Acceptance criteria
- The workflow validates (no YAML/syntax errors) and appears under the repo's Actions tab.
- A manual `workflow_dispatch` run: fetches, writes the snapshot, and either commits a changed
  snapshot or cleanly reports "no changes".
- No `.parquet` files appear in the commit.
- The collector code is unchanged from Phase 1.

## Out of scope
- Kaggle and FIFA PMSR sources (next).
- Any charts or posts (Phase 2).
- Rendering `processed/` artifacts in CI.

## When done
Summarize, show the workflow file, and note the exact steps for the human to (a) confirm the
Action is enabled and (b) trigger a manual test run. Stop before committing; the human commits and
watches the first manual run in the Actions tab.