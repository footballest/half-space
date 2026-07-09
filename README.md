# Half-Space

3D space-control visualizations and analytics for football, starting with the World Cup.

The project runs as two parallel tracks that converge:

- **Track A — Live World Cup 2026:** collect event-level data now, publish fast analytical blog posts.
- **Track B — Space-Control Engine:** build a pitch-control model, render it as interactive 3D surfaces and animations, first on the 2022 World Cup (where tracking data is free), then on 2026 when data is released.

See [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) for the full phased plan.

## Repository layout

```
half-space/
├── src/fsc/            # the installable package ("football space control")
│   ├── collectors/     # Track A: openfootball, Kaggle, FIFA PMSR
│   ├── data/           # loaders + kloppy adapters
│   ├── pitchcontrol/   # Track B: Voronoi baseline + Spearman PPCF
│   ├── viz/            # mplsoccer 2D, Plotly 3D, ffmpeg animation
│   └── utils/
├── data/
│   ├── raw/            # immutable snapshots (never overwritten)
│   ├── interim/        # cleaned parquet / sqlite (regenerable)
│   └── processed/      # analysis-ready (regenerable)
├── notebooks/          # trackA/ and trackB/ exploration + analysis
├── site/               # Quarto blog + website
├── scripts/            # CLI entry points
├── tests/
├── docs/
└── .github/workflows/  # daily data collector (added in Phase 1)
```

Folders are filled in just-in-time, one phase at a time. Empty ones hold a `.gitkeep`.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11 (uv can install it for you).

```bash
# 1. Install the base + dev dependencies into a local .venv
uv sync

# 2. Sanity-check that the package imports
uv run python -c "import fsc; print('fsc ok')"
```

Track B's heavier libraries are installed later, per phase:

```bash
uv sync --extra viz --extra tracking   # from Phase 3 onward
```

### Site (Quarto)

Quarto is a separate CLI tool, not a Python package — install it from
<https://quarto.org/docs/get-started/>, then:

```bash
quarto preview site   # build + live-preview the placeholder site
```

## Automation

A GitHub Action ([`.github/workflows/collect-wc2026.yml`](.github/workflows/collect-wc2026.yml))
runs the openfootball collector once a day at **06:00 UTC**. Each run fetches the feed, writes
that day's raw snapshot under `data/raw/openfootball/`, and — only if the snapshot changed —
commits it back to the repo (as `github-actions[bot]`). The regenerable `data/processed/*.parquet`
tables are not committed. A day with no new data ends cleanly without a commit; a failed fetch
fails the run so a broken feed is visible.

To run it by hand: open the repo's **Actions** tab → **Collect WC2026 (openfootball)** →
**Run workflow**.

## Status

- **Phase 0 — Project setup:** ✅ this scaffold.
- **Phase 1 — Live data collector + daily automation:** ✅ done.
- **Phase 1b — Kaggle CC0 + FIFA PMSR data sources:** next.

## Data sources & attribution

- **openfootball** — public domain match/results data (Track A backbone).
- **Kaggle FIFA World Cup 2026 dataset** — CC0, events/xG/stats.
- **StatsBomb Open Data** — free event + 360 data; **attribution required** (credit StatsBomb).
- **PFF FC 2022 World Cup** — free tracking + event data (request via their form).

Blog content is built from data and our own charts, not broadcast footage.
