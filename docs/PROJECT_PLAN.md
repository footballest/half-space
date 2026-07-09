# Half-Space — Project Plan

Two tracks running in parallel, converging at the end.

- **Track A — Live World Cup 2026:** lightweight event data, fast blog posts. Builds the site, audience, and data pipeline now.
- **Track B — Space-Control Engine:** the depth. Model → 3D → animation, on 2022 World Cup data, ready to receive 2026 data when released.

Phases are ordered by dependency, not strictly by time — several run concurrently. Each phase ends in a small, working, committed increment. Every file is reviewed before it's committed.

## Locked decisions

- **Repo:** single monorepo, `half-space`.
- **Site:** Quarto (notebook-driven, Python-native, embeds Plotly HTML). Static for now; a dynamic app (Streamlit / custom) only if server-side rendering is needed later.
- **Language / env:** Python 3.11, managed with `uv`.
- **Data:** `raw` is immutable; `interim`/`processed` are regenerable. Tiny openfootball snapshots committed; bulky tracking data git-ignored.

## Deferred decisions

- Hosting platform (GitHub Pages / Cloudflare / Vercel).
- Storage format for the collector (SQLite vs parquet vs both).
- License posture (non-commercial + attributed for now).

## Phases

### Phase 0 — Project setup ✅
Repo, folder structure, Python env, dependency list, Quarto site scaffold. Deliverable: an empty-but-runnable project.

### Phase 1 — Live data collector (Track A)
Python script + free GitHub Action (cron) that snapshots openfootball daily, preserves raw snapshots untouched, and normalizes into a tidy store. Layer in the Kaggle CC0 dataset and FIFA PMSR physical data. Deliverable: a growing, versioned WC2026 dataset, flowing automatically.

### Phase 2 — First blog posts (Track A)
Quick wins: xG race / results-timeline charts, the stadium-altitude angle, "48-team format by the numbers" vs 2014–2022. Validates the publish pipeline. Deliverable: 2–3 live posts.

### Phase 3 — Space-control foundations (Track B)
Metrica sample data; set up kloppy, mplsoccer, Plotly; work through the pitch-control tutorial. Deliverable: load tracking data and plot a pitch with players.

### Phase 4 — Pitch control model (Track B)
Implement Spearman's Potential Pitch Control Field, with a Voronoi baseline as the stepping stone. Validate against known implementations. Deliverable: a 2D control surface for any frame.

### Phase 5 — 3D visualization (Track B)
Render the control probability as an interactive 3D Plotly surface (z = control, colored by team). Deliverable: the first showcase visual.

### Phase 6 — Animation pipeline (Track B)
Clips → GIF/MP4 via ffmpeg, vectorized with NumPy/numba. Built for 10–30s key sequences, not full 160k-frame matches. Deliverable: a reusable "make a clip from a moment" tool.

### Phase 7 — Scale to the 2022 World Cup (Track B)
Load the PFF FC dataset via kloppy, produce Round-of-16 / knockout space-control visuals. Deliverable: World Cup space-control posts + the showcase piece.

### Phase 8 — Converge on WC2026
When post-tournament 2026 data is released, slot it in through kloppy. Extend: EPV / xT overlays, pass networks, off-ball runs.
