"""Repo-root-relative data directories.

Everything downstream resolves paths through here so nothing is hardcoded to an
absolute location. The repo root is found by walking up from this file until we
reach the directory that contains ``pyproject.toml``.
"""

from __future__ import annotations

from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    """Return the repo root: the nearest ancestor that contains ``pyproject.toml``."""
    start = (start or Path(__file__)).resolve()
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(f"could not locate repo root (no pyproject.toml above {start})")


ROOT = repo_root()
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
