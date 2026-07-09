# CLAUDE.md — Half-Space

Project context for Claude Code. Read this first, then `docs/PROJECT_PLAN.md`.

## What this is

3D space-control visualizations and analytics for football, starting with the World Cup.
Two parallel tracks that converge:

- **Track A — Live World Cup 2026:** collect event-level data now, publish fast blog posts.
- **Track B — Space-Control Engine:** pitch-control model → interactive 3D → animation, built
  on the 2022 World Cup (free tracking data), ready to receive 2026 data when it's released.

Full phased plan: `docs/PROJECT_PLAN.md` (source of truth for what each phase delivers).

## Locked decisions

- **Repo:** single monorepo, `half-space`.
- **Language / env:** Python 3.11, managed with `uv`.
- **Site:** Quarto (static; notebook-driven; embeds Plotly HTML). A dynamic app comes later
  only if server-side rendering is actually needed.
- **Package:** src-layout, importable as `fsc` (from `src/fsc/`).
- **Data:** `data/raw/` is immutable and never overwritten. `interim/` and `processed/` are
  regenerable and git-ignored. Tiny openfootball snapshots ARE committed; bulky tracking data
  is git-ignored.

## Key commands

```bash
uv sync                                 # base + dev deps
uv sync --extra viz --extra tracking    # Track B libraries (Phase 3+)
uv run python -c "import fsc"            # import sanity check
uv run pytest                           # tests
uv run ruff check . && uv run ruff format .
quarto preview site                     # build + preview the site (Quarto is a separate CLI)
```

## Conventions

- **Just-in-time:** do not scaffold folders, modules, or dependencies until the phase that
  needs them. Empty folders hold a `.gitkeep`. Add Track B deps via the `viz`/`tracking`
  extras, not the base list.
- **One increment per phase:** each phase ends in a small, working, committed state. No
  half-built code left lying around.
- **Raw data is sacred:** collectors write timestamped snapshots to `data/raw/` and never
  overwrite. Everything downstream is regenerable from raw.
- **Package layout:** new code goes under `src/fsc/<area>/`. Areas: `collectors` (Track A
  ingestion), `data` (loaders + kloppy adapters), `pitchcontrol` (Voronoi + Spearman PPCF),
  `viz` (mplsoccer 2D, Plotly 3D, ffmpeg animation), `utils`.
- **Notebooks** live in `notebooks/trackA/` and `notebooks/trackB/`; publishable analysis
  becomes a Quarto post under `site/posts/`.

## Data sources & attribution

- **openfootball** — public domain (Track A backbone).
- **Kaggle FIFA World Cup 2026** — CC0.
- **StatsBomb Open Data** — free; **attribution required** (credit StatsBomb on any chart/post).
- **PFF FC 2022 World Cup** — free tracking + event data (request via their form).
- Blog content is built from data and our own charts, **never broadcast footage**.

## Working style with the human

- The human wants to be aware of every decision — surface choices and trade-offs, don't make
  large or irreversible changes silently.
- Explain as you go: the human has some Python experience, so explain non-obvious code and the
  reasoning behind design choices, but don't over-explain basics.
- Review before commit: prefer showing diffs and getting a nod before committing.

## Current status

- Phase 0 — Project setup: ✅ done.
- Phase 1 — Live data collector (Track A): next. Handoff will live in `docs/handoffs/phase1.md`.