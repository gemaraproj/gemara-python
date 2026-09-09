"""Tests for vendored fixture discovery."""

from __future__ import annotations

from pathlib import Path

import pytest
from test_helpers import fixture_paths


def test_fixture_paths_fails_when_no_matching_fixtures_are_vendored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("test_helpers.FIXTURE_DIR", tmp_path)

    with pytest.raises(AssertionError, match=r"no good-\* fixtures vendored"):
        fixture_paths("good-")
