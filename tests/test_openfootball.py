"""Unit tests for the openfootball normalizer (no network — inline fixture)."""

import pandas as pd

from fsc.collectors import openfootball as of

SNAPSHOT = "2026-07-09"
GROUP_ID = "2026-06-11_Mexico_vs_South Africa"

# A tiny hand-built feed exercising the tricky parts found in the live data:
#   1. a played group match with two goals (one a penalty, one in stoppage "90+9")
#   2. an unplayed knockout match with bracket placeholders ("W73" / "2A")
#   3. a played knockout decided in extra time + a penalty shootout, incl. an own goal
FIXTURE = {
    "name": "Test Cup",
    "matches": [
        {
            "round": "Matchday 1",
            "date": "2026-06-11",
            "time": "13:00 UTC-6",
            "team1": "Mexico",
            "team2": "South Africa",
            "score": {"ft": [2, 1], "ht": [1, 0]},
            "goals1": [{"name": "Raúl Jiménez", "minute": "67"}],
            "goals2": [{"name": "Percy Tau", "minute": "90+9", "penalty": True}],
            "group": "Group A",
            "ground": "Mexico City",
        },
        {
            "round": "Semi-final",
            "num": 101,
            "date": "2026-07-14",
            "time": "19:00 UTC-4",
            "team1": "W73",
            "team2": "2A",
            "ground": "Dallas",
        },
        {
            "round": "Round of 32",
            "num": 74,
            "date": "2026-06-29",
            "time": "16:30 UTC-4",
            "team1": "Germany",
            "team2": "Paraguay",
            "score": {"p": [3, 4], "et": [1, 1], "ft": [1, 1], "ht": [0, 1]},
            "goals1": [{"name": "Kai Havertz", "minute": "54"}],
            "goals2": [{"name": "Own Goal", "minute": "78", "owngoal": True}],
            "ground": "Boston (Foxborough)",
        },
    ],
}


def _matches_indexed():
    return of.normalize_matches(FIXTURE, SNAPSHOT).set_index("match_id")


def test_normalize_matches_shape_and_columns():
    df = of.normalize_matches(FIXTURE, SNAPSHOT)
    assert len(df) == 3
    assert list(df.columns) == of.MATCH_COLUMNS
    assert (df["snapshot_date"] == SNAPSHOT).all()


def test_match_id_scheme():
    ids = set(of.normalize_matches(FIXTURE, SNAPSHOT)["match_id"])
    assert ids == {GROUP_ID, "101", "74"}  # slug for group, bracket num for knockout


def test_status_derived_from_score_presence():
    df = _matches_indexed()
    assert df.loc[GROUP_ID, "status"] == "played"
    assert df.loc["101", "status"] == "scheduled"  # unplayed semi-final
    assert df.loc["74", "status"] == "played"


def test_stage_and_group_assignment():
    df = _matches_indexed()
    assert df.loc[GROUP_ID, "stage"] == "group"
    assert df.loc[GROUP_ID, "group"] == "Group A"
    assert df.loc["101", "stage"] == "knockout"
    assert pd.isna(df.loc["101", "group"])


def test_placeholder_flag():
    df = _matches_indexed()
    assert bool(df.loc["101", "is_placeholder"]) is True  # W73 / 2A
    assert bool(df.loc["74", "is_placeholder"]) is False  # Germany / Paraguay
    assert bool(df.loc[GROUP_ID, "is_placeholder"]) is False


def test_unplayed_scores_are_null():
    df = _matches_indexed()
    for col in ("ft1", "ft2", "ht1", "ht2"):
        assert pd.isna(df.loc["101", col])


def test_extra_time_and_penalty_columns():
    df = _matches_indexed()
    ko = df.loc["74"]
    assert (int(ko["ft1"]), int(ko["ft2"])) == (1, 1)
    assert (int(ko["et1"]), int(ko["et2"])) == (1, 1)
    assert (int(ko["p1"]), int(ko["p2"])) == (3, 4)
    # a group match has no extra time / shootout
    grp = df.loc[GROUP_ID]
    for col in ("et1", "et2", "p1", "p2"):
        assert pd.isna(grp[col])


def test_normalize_goals_one_row_per_goal():
    goals = of.normalize_goals(FIXTURE, SNAPSHOT)
    assert list(goals.columns) == of.GOAL_COLUMNS
    assert len(goals) == 4  # 2 in the group match + 2 in the knockout (incl. own goal)
    assert (goals["snapshot_date"] == SNAPSHOT).all()
    # every goal joins back to a real match
    assert set(goals["match_id"]) <= set(of.normalize_matches(FIXTURE, SNAPSHOT)["match_id"])


def test_goal_flags_and_minute_parsing():
    goals = of.normalize_goals(FIXTURE, SNAPSHOT).set_index("scorer")
    pen = goals.loc["Percy Tau"]
    assert bool(pen["penalty"]) is True
    assert pen["minute_raw"] == "90+9"
    assert int(pen["minute"]) == 90  # numeric base minute parsed from "90+9"
    assert pen["team"] == "South Africa"  # team resolved to the actual name
    assert pen["side"] == "team2"  # original side preserved
    assert bool(goals.loc["Raúl Jiménez", "penalty"]) is False


def test_goal_team_resolution_and_own_goal_credit():
    goals = of.normalize_goals(FIXTURE, SNAPSHOT).set_index("scorer")
    # a normal goal is credited to the side that scored it
    assert (goals.loc["Raúl Jiménez", "team"], goals.loc["Raúl Jiménez", "side"]) == (
        "Mexico",
        "team1",
    )
    # an own goal is credited to the *benefiting* team, not the scorer's side
    og = goals.loc["Own Goal"]
    assert bool(og["owngoal"]) is True
    assert (og["team"], og["side"]) == ("Paraguay", "team2")
