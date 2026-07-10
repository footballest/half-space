"""Unit tests for the Kaggle WC2026 normalizers (no network / no download).

Everything runs off tiny inline fixture frames that mimic the real CSV columns.
"""

import pandas as pd

from fsc.collectors import kaggle_wc2026 as kg
from fsc.utils.teams import canonical

# --- openfootball side (the crosswalk join target) ---
# G2 exercises a team-name alias (Kaggle "Czechia" -> "Czech Republic"); "73"
# exercises the one-day date offset (Kaggle files it a day later).
OF_MATCHES = pd.DataFrame(
    [
        {
            "match_id": "G1",
            "date": "2026-06-11",
            "team1": "Mexico",
            "team2": "South Africa",
            "is_placeholder": False,
            "status": "played",
        },
        {
            "match_id": "G2",
            "date": "2026-06-11",
            "team1": "South Korea",
            "team2": "Czech Republic",
            "is_placeholder": False,
            "status": "played",
        },
        {
            "match_id": "73",
            "date": "2026-06-28",
            "team1": "South Africa",
            "team2": "Canada",
            "is_placeholder": False,
            "status": "played",
        },
        {
            "match_id": "101",
            "date": "2026-07-14",
            "team1": "W73",
            "team2": "2A",
            "is_placeholder": True,
            "status": "scheduled",
        },
    ]
)

# --- Kaggle matches_detailed side ---
MATCHES_DETAILED = pd.DataFrame(
    [
        {
            "match_id": 1,
            "date": "2026-06-11",
            "home_team_name": "Mexico",
            "away_team_name": "South Africa",
            "status": "Completed",
            "home_score": 2,
            "away_score": 0,
            "home_xg": 1.84,
            "away_xg": 0.52,
        },
        {
            "match_id": 2,
            "date": "2026-06-11",
            "home_team_name": "South Korea",
            "away_team_name": "Czechia",
            "status": "Completed",  # alias needed
            "home_score": 2,
            "away_score": 1,
            "home_xg": 1.45,
            "away_xg": 1.12,
        },
        {
            "match_id": 73,
            "date": "2026-06-29",
            "home_team_name": "South Africa",
            "away_team_name": "Canada",
            "status": "Completed",  # +1 day vs openfootball
            "home_score": 1,
            "away_score": 1,
            "home_xg": 1.10,
            "away_xg": 0.90,
        },
        {
            "match_id": 99,
            "date": "2026-07-19",
            "home_team_name": "France",
            "away_team_name": "Brazil",
            "status": "Scheduled",  # no openfootball row
            "home_score": None,
            "away_score": None,
            "home_xg": None,
            "away_xg": None,
        },
    ]
)


def test_canonical_aliases_and_passthrough():
    assert canonical("Czechia") == "Czech Republic"
    assert canonical("Türkiye") == "Turkey"
    assert canonical("Mexico") == "Mexico"  # already canonical
    assert canonical(float("nan")) is None  # NaN team (placeholder) -> None
    assert canonical(None) is None


def test_crosswalk_matches_alias_and_date_offset():
    cw = kg.build_crosswalk(MATCHES_DETAILED, OF_MATCHES)
    by_kid = cw.set_index("kaggle_match_id")
    assert list(cw.columns) == kg.CROSSWALK_COLUMNS
    assert by_kid.loc[1, "match_id"] == "G1"
    assert by_kid.loc[2, "match_id"] == "G2"  # matched despite Czechia/Czech Republic
    assert by_kid.loc[73, "match_id"] == "73"  # matched despite the one-day gap


def test_crosswalk_flags_unmatchable_row():
    cw = kg.build_crosswalk(MATCHES_DETAILED, OF_MATCHES).set_index("kaggle_match_id")
    assert pd.isna(cw.loc[99, "match_id"])  # France/Brazil has no openfootball fixture


# --- team_match_stats fixtures ---
MATCHES = pd.DataFrame(
    [{"match_id": 1, "home_team_id": 10, "away_team_id": 20, "home_xg": 1.84, "away_xg": 0.52}]
)
MATCH_TEAM_STATS = pd.DataFrame(
    [
        {
            "match_id": 1,
            "team_id": 10,
            "possession_pct": 57,
            "total_shots": 16,
            "shots_on_target": 4,
            "corners": 6,
            "fouls": 11,
            "offsides": 2,
            "saves": 1,
        },
        {
            "match_id": 1,
            "team_id": 20,
            "possession_pct": 43,
            "total_shots": 3,
            "shots_on_target": 2,
            "corners": 3,
            "fouls": 15,
            "offsides": 1,
            "saves": 4,
        },
    ]
)
TEAMS = pd.DataFrame(
    [{"team_id": 10, "team_name": "Mexico"}, {"team_id": 20, "team_name": "Czechia"}]
)
CROSSWALK = pd.DataFrame([{"kaggle_match_id": 1, "match_id": "G1"}])


def test_team_match_stats_columns_and_dtypes():
    df = kg.normalize_team_match_stats(MATCHES, MATCH_TEAM_STATS, TEAMS, CROSSWALK)
    assert list(df.columns) == kg.TEAM_STATS_COLUMNS
    assert len(df) == 2
    assert df["xg"].dtype == float
    assert str(df["possession"].dtype) == "Int64"


def test_team_match_stats_side_xg_and_alias():
    df = kg.normalize_team_match_stats(MATCHES, MATCH_TEAM_STATS, TEAMS, CROSSWALK).set_index(
        "team"
    )
    # xG is per-match (home/away); each team row must pick up its own side's value.
    assert df.loc["Mexico", "side"] == "home"
    assert df.loc["Mexico", "xg"] == 1.84
    assert df.loc["Mexico", "match_id"] == "G1"  # resolved to our id via crosswalk
    # the away team's name is canonicalized (Czechia -> Czech Republic)
    assert "Czech Republic" in df.index
    assert df.loc["Czech Republic", "side"] == "away"
    assert df.loc["Czech Republic", "xg"] == 0.52


def test_normalize_venues_and_referees():
    venues = pd.DataFrame(
        [
            {
                "venue_id": 1,
                "stadium_name": "Estadio Azteca",
                "city": "Mexico City",
                "country": "MEX",
                "capacity": 80824,
                "latitude": 19.3,
                "longitude": -99.1,
                "elevation_meters": 2200,
            }
        ]
    )
    v = kg.normalize_venues(venues)
    assert list(v.columns) == kg.VENUE_COLUMNS
    assert v.loc[0, "name"] == "Estadio Azteca"
    assert v.loc[0, "elevation_m"] == 2200
    assert str(v["elevation_m"].dtype) == "Int64"

    referees = pd.DataFrame(
        [
            {
                "referee_id": 1,
                "name": "Szymon Marciniak",
                "country": "Poland",
                "avg_cards_per_game": 4.2,
            }
        ]
    )
    r = kg.normalize_referees(referees)
    assert list(r.columns) == kg.REFEREE_COLUMNS
    assert r.loc[0, "avg_cards_per_game"] == 4.2
