"""Collector for the openfootball World Cup feed (Track A).

Fetches the public-domain openfootball JSON for a World Cup, snapshots it
untouched under ``data/raw/`` (one file per UTC day, committed to git), and
normalizes the current tournament state into two tidy Parquet tables under
``data/processed/``:

* ``matches.parquet`` — one row per match.
* ``goals.parquet``   — one row per goal.

Run it by hand with::

    uv run python -m fsc.collectors.openfootball

``data/processed/`` is regenerated from the freshest fetch each run (it is the
*current* state of the tournament); ``data/raw/`` preserves the daily history.
"""

from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from fsc.utils import paths

FEED_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master/{year}/worldcup.json"
)
USER_AGENT = "half-space-collector/0.1 (+https://github.com/half-space; openfootball WC data)"

# Bracket placeholders that appear before a knockout fixture resolves, e.g.
# "W97" (winner of match 97), "L101" (loser of match 101), "2A" (Group A
# runner-up), "3ACD" (a third-placed team). Real team names never match this.
_PLACEHOLDER_RE = re.compile(r"^(\d+[A-Z]+|[WL]\d+)$")

MATCH_COLUMNS = [
    "match_id",
    "round",
    "stage",
    "group",
    "date",
    "time",
    "team1",
    "team2",
    "ft1",
    "ft2",
    "ht1",
    "ht2",
    "et1",
    "et2",
    "p1",
    "p2",
    "status",
    "is_placeholder",
    "venue",
    "snapshot_date",
]
# Score columns are stored as pandas nullable ints so unplayed matches read back
# as <NA> rather than being coerced to floats (e.g. 2.0).
_SCORE_INT_COLUMNS = ["ft1", "ft2", "ht1", "ht2", "et1", "et2", "p1", "p2"]

GOAL_COLUMNS = [
    "match_id",
    "team",
    "side",
    "scorer",
    "minute_raw",
    "minute",
    "penalty",
    "owngoal",
    "snapshot_date",
]


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _is_placeholder_team(name: str | None) -> bool:
    """True if ``name`` is a bracket placeholder (e.g. "W97", "2A") not a real team."""
    return bool(name) and _PLACEHOLDER_RE.match(name) is not None


def _parse_minute(minute_raw: object) -> int | None:
    """Numeric base minute from a raw string like "90+9" -> 90; None if unparseable."""
    if minute_raw is None:
        return None
    base = str(minute_raw).split("+", 1)[0].strip()
    try:
        return int(base)
    except ValueError:
        return None


def _match_id(match: dict) -> str:
    """Stable id: the knockout ``num`` if present, else a slug of date + teams.

    Group pairings are fixed from the start, so ``date + team1 + team2`` is stable
    across snapshots; knockout matches get their official bracket number (73-104).
    """
    if "num" in match:
        return str(match["num"])
    return f"{match.get('date')}_{match.get('team1')}_vs_{match.get('team2')}"


def _pair(score: dict, key: str) -> tuple[int | None, int | None]:
    """Return ``(home, away)`` from a 2-element score list, or ``(None, None)``."""
    vals = score.get(key)
    if isinstance(vals, (list, tuple)) and len(vals) == 2:
        return vals[0], vals[1]
    return None, None


def fetch_raw(year: int = 2026, timeout: int = 30) -> dict:
    """GET the openfootball feed for ``year`` and return the parsed JSON.

    Sends a User-Agent, applies a ``timeout`` (seconds), and retries once on failure.
    """
    url = FEED_URL.format(year=year)
    headers = {"User-Agent": USER_AGENT}
    last_err: Exception | None = None
    for attempt in (1, 2):  # initial try + one retry
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as err:
            last_err = err
            if attempt == 1:
                time.sleep(2)  # brief backoff before the single retry
    raise RuntimeError(f"failed to fetch {url} after one retry: {last_err}") from last_err


def save_snapshot(raw: dict, snapshot_date: date | str | None = None) -> Path:
    """Write ``raw`` to ``data/raw/openfootball/worldcup_YYYY-MM-DD.json`` (UTC day).

    One file per day; re-running on the same day overwrites that day's file.
    Immutability is *across* days — the cron will run once daily.
    """
    snapshot_date = snapshot_date or _utc_today()
    out_dir = paths.RAW / "openfootball"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"worldcup_{snapshot_date}.json"
    out_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def normalize_matches(raw: dict, snapshot_date: date | str) -> pd.DataFrame:
    """One tidy row per match; see :data:`MATCH_COLUMNS` for the schema."""
    snap = str(snapshot_date)
    rows = []
    for m in raw.get("matches", []):
        score = m.get("score") or {}
        ft1, ft2 = _pair(score, "ft")
        ht1, ht2 = _pair(score, "ht")
        et1, et2 = _pair(score, "et")
        p1, p2 = _pair(score, "p")
        rows.append(
            {
                "match_id": _match_id(m),
                "round": m.get("round"),
                # num is present iff knockout; group is present iff group stage.
                "stage": "knockout" if "num" in m else "group",
                "group": m.get("group"),
                "date": m.get("date"),
                "time": m.get("time"),
                "team1": m.get("team1"),
                "team2": m.get("team2"),
                "ft1": ft1,
                "ft2": ft2,
                "ht1": ht1,
                "ht2": ht2,
                "et1": et1,
                "et2": et2,
                "p1": p1,
                "p2": p2,
                "status": "played" if score else "scheduled",
                "is_placeholder": (
                    _is_placeholder_team(m.get("team1")) or _is_placeholder_team(m.get("team2"))
                ),
                "venue": m.get("ground"),
                "snapshot_date": snap,
            }
        )
    df = pd.DataFrame(rows, columns=MATCH_COLUMNS)
    df[_SCORE_INT_COLUMNS] = df[_SCORE_INT_COLUMNS].astype("Int64")
    df["is_placeholder"] = df["is_placeholder"].astype(bool)
    return df


def normalize_goals(raw: dict, snapshot_date: date | str) -> pd.DataFrame:
    """One tidy row per goal; see :data:`GOAL_COLUMNS` for the schema.

    ``team`` is the name of the team the goal is credited to; ``side`` is which
    side scored it (``team1``/``team2``). openfootball files goals — own goals
    included — under the array of the team that benefits, so for an own goal
    ``team`` is the benefiting team while ``scorer`` is the opposition player.
    """
    snap = str(snapshot_date)
    rows = []
    for m in raw.get("matches", []):
        mid = _match_id(m)
        for array_key, side in (("goals1", "team1"), ("goals2", "team2")):
            team = m.get(side)  # resolve to the actual name of the benefiting side
            for g in m.get(array_key) or []:  # goals arrays are absent on 0-0 matches
                minute_raw = g.get("minute")
                rows.append(
                    {
                        "match_id": mid,
                        "team": team,
                        "side": side,
                        "scorer": g.get("name"),
                        "minute_raw": minute_raw,
                        "minute": _parse_minute(minute_raw),
                        "penalty": bool(g.get("penalty", False)),
                        "owngoal": bool(g.get("owngoal", False)),
                        "snapshot_date": snap,
                    }
                )
    df = pd.DataFrame(rows, columns=GOAL_COLUMNS)
    df["minute"] = df["minute"].astype("Int64")
    df["penalty"] = df["penalty"].astype(bool)
    df["owngoal"] = df["owngoal"].astype(bool)
    return df


def run(year: int = 2026) -> tuple[Path, Path]:
    """Fetch -> snapshot raw -> normalize -> write processed Parquet -> print summary."""
    snapshot_date = _utc_today()
    raw = fetch_raw(year=year)
    save_snapshot(raw, snapshot_date)

    matches = normalize_matches(raw, snapshot_date)
    goals = normalize_goals(raw, snapshot_date)

    paths.PROCESSED.mkdir(parents=True, exist_ok=True)
    matches_path = paths.PROCESSED / "matches.parquet"
    goals_path = paths.PROCESSED / "goals.parquet"
    matches.to_parquet(matches_path, index=False)
    goals.to_parquet(goals_path, index=False)

    n_played = int((matches["status"] == "played").sum())
    rel = matches_path.parent.relative_to(paths.ROOT)
    print(
        f"Snapshot {snapshot_date}: {len(matches)} matches "
        f"({n_played} played, {len(matches) - n_played} scheduled), "
        f"{len(goals)} goals -> {rel}/"
    )
    return matches_path, goals_path


def main() -> None:
    run()


if __name__ == "__main__":
    main()
