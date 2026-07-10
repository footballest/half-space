# Phase 2b Handoff — Post 1 Analysis: "When an xG Justice Table Mistakes Luck for Finishing"

## Goal
Build the **reproducible analysis + charts** for the first blog post: the own-goal decomposition
of the xG "justice table". **Analysis and figures only — write NO prose / no article.** The human
writes the story around your outputs. Everything must be snapshot-stamped and honest about
uncertainty.

## Before you start
Read `CLAUDE.md`. Phases 1/1b done; processed tables exist. The EDA notebook
`notebooks/trackA/01_eda_wc2026.ipynb` has the exploratory version of this — build a NEW,
clean notebook, don't extend that one.

## Deliverable
`notebooks/trackA/02_post1_own_goals.ipynb` — runs clean top-to-bottom
(`restart & run all`). Charts in **Plotly** (they'll embed in Quarto later). Every figure carries
a caption/stamp: **"FIFA World Cup 2026 — matches completed through July 10, 2026."** Read the
actual snapshot date from the data (`matches.snapshot_date`), don't hardcode it.

## The framing (get the wording exactly right — it's the whole point)
The goals−xG table is NOT arithmetically wrong; it's a *scoreboard* residual often mislabelled a
*finishing* residual. Present two explicitly named quantities, side by side:
- **Scoreboard residual** = (all goals) − xG
- **Finishing residual** = (non-own goals) − xG
Do NOT frame this as "deleting own goals to fix a broken table." Frame it as decomposition:
scoreboard fortune vs finishing.

## TASK 0 (do FIRST — it may change the numbers): audit own-goal xG handling
There are ~14 own goals in `goals.parquet` (`owngoal == True`). Before any correction, determine
how xG relates to them, because it decides what "removing" an own goal does:
- For each own-goal event, inspect the underlying match's xG and shot data (cross-reference the
  raw Kaggle `match_events.csv` / `matches.csv` if needed). Was there an underlying shot with xG
  credited? Is the own goal a deflected shot reclassified, or a cross/pass with no xG?
- **Report what you find** in a markdown cell: does removing an own goal from the goal count leave
  a "dangling" xG (so that sequence becomes negative finishing residual), or is there no
  associated xG? State exactly what the adjustment does. This determines whether the finishing
  residual is a clean subtraction or needs a note. Do not proceed to the chart until this is
  documented.

## TASK 1: the auditable decomposition table
One row per team, sorted by scoreboard residual:
`team | xg | all_goals | own_goals_for | non_own_goals | penalty_goals | scoreboard_residual |
finishing_residual`.
- `own_goals_for` = own goals credited to that team (benefiting team; use `goals.team`).
- Also compute (as a later/optional column) an **open-play finishing residual** = (non-own,
  non-penalty goals) − (non-penalty xG) IF penalty xG is separable; if xG can't be split by
  penalty, note that and skip this column rather than guessing.
- This table is the source of truth behind every chart. Display it in full.

## TASK 2: fix the broken concentration metric
The EDA's `best_share = best_match / net_residual` is invalid (explodes when a team has offsetting
+/− matches; e.g. Canada 6.06). Replace with BOTH:
- **Leave-one-out residual** (headline): `sum(match_diffs) - max(match_diff)` — does the team still
  look like an over-performer after dropping its single best match?
- **Positive-contribution concentration** (support): `max(positive_diff) / sum(positive_diffs)`,
  bounded [0,1] — of all a team's good games, how much rides on the best one?
Compute these on the FINISHING residual (own goals already removed), per team-match.

## TASK 3: Poisson uncertainty funnel
Guard against reading noise as skill on a ~5-match sample:
- Model `goals_i | xG_i ~ Poisson(xG_i)`. Plot accumulated xG (x) vs goals/xG ratio (y), with a
  reference line at 1.0 and 80% / 95% Poisson bands that narrow as xG accumulates.
- Plot teams on it. Low-xG teams sit in wide bands (deviations expected); only sustained deviation
  at high xG is notable.
- Markdown caveat: this is a **reference model to discourage over-interpretation**, NOT a finishing
  -talent estimate. It ignores xG calibration error, within-match dependence, team finishing
  ability, penalties. Do not label any team "clinical"/"wasteful" as proven fact.

## TASK 4: the dumbbell rank-change chart (the money shot)
- Left endpoint: rank by scoreboard residual. Right endpoint: rank by finishing residual.
- One row per team, a line connecting the two ranks; annotate teams that move materially (the USA
  is the headline: ~+3.99 → ~+1.99 after two opponent own goals, roughly rank 1 → ~7 — verify the
  exact adjusted rank from the data).
- Clear, readable Plotly; sensible ordering; snapshot stamp.

## Constraints
- Runs clean end-to-end; use `fsc.utils.paths` (no hardcoded paths).
- Plotly for charts. Requires the `viz` extra — confirm plotly imports; if not, note
  `uv sync --extra viz` at top.
- NO article prose, NO "winner" declarations, NO overselling significance.
- Snapshot date read from data and shown on every figure.

## When done
Confirm the notebook runs top-to-bottom. Summarize: the own-goal audit finding (Task 0), the
adjusted table, and the USA rank movement — as bullet facts, not prose. List anything the data
couldn't support (e.g. penalty-xG split). STOP. The human explores the outputs and writes the post.
Don't commit (notebooks are noisy in git; the human commits after review + output-clearing).