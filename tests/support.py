"""Shared test helpers, importable by name (unlike `conftest`)."""

from __future__ import annotations

from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "schemas" / "fixtures"


def fixture_paths(prefix: str) -> list[Path]:
    paths = sorted(p for p in FIXTURE_DIR.iterdir() if p.name.startswith(prefix))
    if not paths:
        raise AssertionError(f"no {prefix}* fixtures vendored in {FIXTURE_DIR}")
    return paths
