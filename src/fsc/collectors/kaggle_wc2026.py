"""Collector for the Kaggle "FIFA World Cup 2026" dataset (Track A, second source).

openfootball gives results + goals but no expected goals. This CC0 dataset (by
MD Mominul Islam, slug ``mominullptr/fifa-world-cup-2026-dataset``) adds xG,
per-team match stats, referees, and stadium altitude. We normalize the pieces we
need into tidy Parquet tables that join to the openfootball ``matches`` table.

The raw CSVs are downloaded separately (they are immutable once fetched)::

    uv run --with kaggle kaggle datasets download \\
        -d mominullptr/fifa-world-cup-2026-dataset \\
        -p data/raw/kaggle_wc2026/ --unzip

Then normalize the current state into ``data/processed/``::

    uv run python -m fsc.collectors.kaggle_wc2026

Kaggle assigns its own integer match ids, unrelated to openfootball's. We build a
crosswalk on (date + team names, spelling-normalized) so the xG/stats tables key
off *our* ``match_id`` and join straight to ``matches.parquet``.
"""

from __future__ import annotations

import pandas as pd

from fsc.utils import paths
from fsc.utils.teams import canonical

DATASET_SLUG = "mominullptr/fifa-world-cup-2026-dataset"
RAW_KAGGLE = paths.RAW / "kaggle_wc2026"

# CSVs we read. Others in the download (lineups, player_stats, squads,
# match_events, predictions) are out of scope for this phase.
_REQUIRED_CSVS = (
    "matches.csv",
    "matches_detailed.csv",
    "match_team_stats.csv",
    "venues.csv",
    "referees.csv",
    "teams.csv",
)

TEAM_STATS_COLUMNS = [
    "match_id",  # our openfootball match_id (via crosswalk); <NA> if unmatched
    "kaggle_match_id",
    "team",
    "side",  # home | away
    "xg",
    "possession",
    "shots",
    "shots_on_target",
    "corners",
    "fouls",
    "offsides",
    "saves",
]
VENUE_COLUMNS = ["name", "city", "country", "capacity", "latitude", "longitude", "elevation_m"]
REFEREE_COLUMNS = ["name", "country", "avg_cards_per_game"]
CROSSWALK_COLUMNS = ["kaggle_match_id", "match_id", "date", "home_team", "away_team"]


def load_raw() -> dict[str, pd.DataFrame]:
    """Read the required raw CSVs from ``data/raw/kaggle_wc2026/``.

    Raises a helpful error (with the download command) if they're missing — the
    fetch is a separate manual/CI step, not part of normalization.
    """
    missing = [name for name in _REQUIRED_CSVS if not (RAW_KAGGLE / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"missing Kaggle CSVs under {RAW_KAGGLE}: {missing}\n"
            "Download them first:\n"
            f"  uv run --with kaggle kaggle datasets download -d {DATASET_SLUG} "
            f"-p {RAW_KAGGLE.relative_to(paths.ROOT)}/ --unzip"
        )
    return {name.removesuffix(".csv"): pd.read_csv(RAW_KAGGLE / name) for name in _REQUIRED_CSVS}


def _pair(team_a: str | None, team_b: str | None) -> frozenset | None:
    """Order-independent key of the two canonical team names, or ``None``.

    Home/away ordering differs between sources, so we key matches on the
    unordered pair. Returns ``None`` if either team is missing (a placeholder).
    """
    ca, cb = canonical(team_a), canonical(team_b)
    if ca is None or cb is None:
        return None
    return frozenset((ca, cb))


# Kaggle dates come from kickoff_time_utc, so a late North-American kickoff lands
# on the next UTC day vs openfootball's local match date. Allow a one-day gap.
_MAX_DAY_GAP = 1


def build_crosswalk(matches_detailed: pd.DataFrame, of_matches: pd.DataFrame) -> pd.DataFrame:
    """Map each Kaggle match to our openfootball ``match_id`` on team pair + date.

    Matches on the unordered canonical team pair, then disambiguates by date
    within a one-day tolerance (see :data:`_MAX_DAY_GAP`). Skips openfootball
    placeholder fixtures and Kaggle rows with missing team names.
    """
    of_by_pair: dict[frozenset, list[tuple[pd.Timestamp, str]]] = {}
    for row in of_matches.itertuples(index=False):
        if getattr(row, "is_placeholder", False) or pd.isna(row.date):
            continue
        pair = _pair(row.team1, row.team2)
        if pair is not None:
            of_by_pair.setdefault(pair, []).append((pd.Timestamp(row.date), row.match_id))

    rows = []
    for row in matches_detailed.itertuples(index=False):
        pair = _pair(row.home_team_name, row.away_team_name)
        match_id = None
        if pair is not None and not pd.isna(row.date):
            kdate = pd.Timestamp(row.date)
            # nearest openfootball fixture of the same pair, within the day gap.
            near = sorted(
                (abs((kdate - d).days), mid)
                for d, mid in of_by_pair.get(pair, [])
                if abs((kdate - d).days) <= _MAX_DAY_GAP
            )
            if near:
                match_id = near[0][1]
        rows.append(
            {
                "kaggle_match_id": row.match_id,
                "match_id": match_id,
                "date": row.date,
                "home_team": canonical(row.home_team_name),
                "away_team": canonical(row.away_team_name),
            }
        )
    return pd.DataFrame(rows, columns=CROSSWALK_COLUMNS)


def normalize_team_match_stats(
    matches: pd.DataFrame,
    match_team_stats: pd.DataFrame,
    teams: pd.DataFrame,
    crosswalk: pd.DataFrame,
) -> pd.DataFrame:
    """One row per team per match: xG (from ``matches``) + per-team stats.

    xG lives on the match (``home_xg``/``away_xg``), so we resolve each stats
    row's ``team_id`` to the home or away side to attach the right xG value.
    """
    # side + xg per stats row, via the match's home/away team ids.
    match_sides = matches[["match_id", "home_team_id", "away_team_id", "home_xg", "away_xg"]]
    df = match_team_stats.merge(match_sides, on="match_id", how="left")
    is_home = df["team_id"] == df["home_team_id"]
    df["side"] = is_home.map({True: "home", False: "away"})
    df["xg"] = df["home_xg"].where(is_home, df["away_xg"])

    df = df.merge(teams[["team_id", "team_name"]], on="team_id", how="left")
    df["team"] = df["team_name"].map(canonical)

    # attach our openfootball match_id via the crosswalk (Kaggle id -> ours).
    df = df.merge(
        crosswalk[["kaggle_match_id", "match_id"]].rename(columns={"match_id": "of_match_id"}),
        left_on="match_id",
        right_on="kaggle_match_id",
        how="left",
    )

    out = pd.DataFrame(
        {
            "match_id": df["of_match_id"],
            "kaggle_match_id": df["match_id"],
            "team": df["team"],
            "side": df["side"],
            "xg": df["xg"].astype(float),
            "possession": df["possession_pct"].astype("Int64"),
            "shots": df["total_shots"].astype("Int64"),
            "shots_on_target": df["shots_on_target"].astype("Int64"),
            "corners": df["corners"].astype("Int64"),
            "fouls": df["fouls"].astype("Int64"),
            "offsides": df["offsides"].astype("Int64"),
            "saves": df["saves"].astype("Int64"),
        },
        columns=TEAM_STATS_COLUMNS,
    )
    return out


def normalize_venues(venues: pd.DataFrame) -> pd.DataFrame:
    """Stadiums with the altitude angle (``elevation_m``)."""
    out = venues.rename(columns={"stadium_name": "name", "elevation_meters": "elevation_m"})[
        ["name", "city", "country", "capacity", "latitude", "longitude", "elevation_m"]
    ].copy()
    out["elevation_m"] = out["elevation_m"].astype("Int64")
    out["capacity"] = out["capacity"].astype("Int64")
    return out[VENUE_COLUMNS]


def normalize_referees(referees: pd.DataFrame) -> pd.DataFrame:
    """Referees with average cards per game."""
    return referees[["name", "country", "avg_cards_per_game"]].copy()


def run() -> dict[str, "pd.DataFrame"]:
    """Load raw -> crosswalk -> normalize -> write Parquet -> print summary + checks."""
    raw = load_raw()
    of_matches = pd.read_parquet(paths.PROCESSED / "matches.parquet")

    crosswalk = build_crosswalk(raw["matches_detailed"], of_matches)
    team_stats = normalize_team_match_stats(
        raw["matches"], raw["match_team_stats"], raw["teams"], crosswalk
    )
    venues = normalize_venues(raw["venues"])
    referees = normalize_referees(raw["referees"])

    paths.PROCESSED.mkdir(parents=True, exist_ok=True)
    outputs = {
        "team_match_stats": team_stats,
        "venues": venues,
        "referees": referees,
        "match_crosswalk": crosswalk,
    }
    for name, df in outputs.items():
        df.to_parquet(paths.PROCESSED / f"{name}.parquet", index=False)

    _report_coverage(crosswalk, raw["matches"], of_matches)
    _report_xg_sanity(raw["matches_detailed"])
    return outputs


def _report_coverage(
    crosswalk: pd.DataFrame, kaggle_matches: pd.DataFrame, of_matches: pd.DataFrame
) -> None:
    """Print join coverage: openfootball played matches matched to a Kaggle xG."""
    # Kaggle matches that actually carry an xG value.
    has_xg = kaggle_matches[kaggle_matches["home_xg"].notna()]["match_id"]
    xg_kaggle_ids = set(has_xg)
    resolved = crosswalk[crosswalk["match_id"].notna()]
    matched_of_ids = set(resolved[resolved["kaggle_match_id"].isin(xg_kaggle_ids)]["match_id"])

    played = of_matches[of_matches["status"] == "played"]
    played_ids = set(played["match_id"].astype(str))
    matched = {str(i) for i in matched_of_ids} & played_ids
    unmatched = played_ids - matched

    print(
        f"Join coverage: {len(matched)}/{len(played_ids)} played openfootball matches "
        f"matched to Kaggle xG ({len(unmatched)} unmatched)."
    )
    if unmatched:
        rows = played[played["match_id"].astype(str).isin(unmatched)]
        for r in rows.itertuples(index=False):
            print(f"  unmatched: {r.date}  {r.team1} vs {r.team2}  (match_id={r.match_id})")

    # Kaggle rows with a real fixture that failed to resolve to us (coverage gaps
    # the other direction — e.g. a spelling we haven't aliased yet).
    unresolved_kaggle = crosswalk[crosswalk["match_id"].isna() & crosswalk["home_team"].notna()]
    if len(unresolved_kaggle):
        print(
            f"  {len(unresolved_kaggle)} Kaggle fixture(s) did not resolve to an openfootball id:"
        )
        for r in unresolved_kaggle.itertuples(index=False):
            print(f"    {r.date}  {r.home_team} vs {r.away_team}  (kaggle_id={r.kaggle_match_id})")


def _report_xg_sanity(matches_detailed: pd.DataFrame) -> None:
    """Spot-check xG plausibility and print 5 completed matches for external eyeballing."""
    completed = matches_detailed[
        (matches_detailed["status"] == "Completed") & matches_detailed["home_xg"].notna()
    ].copy()

    xg = pd.concat([completed["home_xg"], completed["away_xg"]])
    goals = pd.concat([completed["home_score"], completed["away_score"]])
    in_range = ((xg >= 0) & (xg <= 6)).mean() * 100
    corr = pd.DataFrame({"xg": xg, "goals": goals}).corr().iloc[0, 1]

    print(
        f"\nxG sanity check ({len(completed)} completed matches): "
        f"{in_range:.0f}% of team-xG values in [0,6]; "
        f"corr(xG, goals) = {corr:.2f} (expect a positive, ~0.5-0.8 relationship)."
    )
    print("  5 samples to compare against a public tracker (FotMob / RealGM WC2026 xG):")
    sample = completed.head(5)
    for r in sample.itertuples(index=False):
        print(
            f"    {r.date}  {r.home_team_name} {int(r.home_score)}-{int(r.away_score)} "
            f"{r.away_team_name}   xG {r.home_xg:.2f} - {r.away_xg:.2f}"
        )


def main() -> None:
    run()


if __name__ == "__main__":
    main()
