"""Team-name canonicalization across data sources.

Different feeds spell nations differently (openfootball "Czech Republic" vs the
Kaggle set's "Czechia"). :func:`canonical` maps every known variant to a single
canonical spelling so rows from different sources can be joined on team name.

The canonical form is openfootball's spelling, since that feed is the backbone
of ``matches.parquet``. Track B (kloppy/StatsBomb/PFF) will reuse this map, so
add new provider spellings here rather than in ad-hoc join code.
"""

from __future__ import annotations

# variant spelling -> canonical (openfootball) spelling.
# Only entries where sources disagree need to appear; identical spellings pass
# through :func:`canonical` unchanged.
TEAM_ALIASES: dict[str, str] = {
    # Kaggle "FIFA World Cup 2026" dataset spellings (Phase 1b):
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
    "Cabo Verde": "Cape Verde",
    "Congo DR": "DR Congo",
    "Czechia": "Czech Republic",
    "Côte d'Ivoire": "Ivory Coast",
    "IR Iran": "Iran",
    "Türkiye": "Turkey",
    # Other common variants seen across public sources (harmless if unused):
    "United States": "USA",
    "Korea Republic": "South Korea",
    "Turkiye": "Turkey",
}


def canonical(name: str | None) -> str | None:
    """Return the canonical spelling of ``name`` (unchanged if already canonical).

    ``None`` and blank strings pass through as ``None`` so placeholder/unresolved
    fixtures don't collide on an empty key.
    """
    # Treat None and pandas NaN (a float) alike — unresolved placeholders.
    if name is None or not isinstance(name, str):
        return None
    stripped = name.strip()
    if not stripped:
        return None
    return TEAM_ALIASES.get(stripped, stripped)
