"""Tests for release version validation logic, label policy simulation, and YAML schema checking."""

from __future__ import annotations

import pathlib
from typing import Any

import pytest
import validate_release_version
import yaml
from validate_release_version import parse_semver


def test_parse_semver_valid() -> None:
    assert parse_semver("0.1.0") == (0, 1, 0)
    assert parse_semver("0.1.1") == (0, 1, 1)
    assert parse_semver("0.2.0") == (0, 2, 0)
    assert parse_semver("1.0.0") == (1, 0, 0)
    assert parse_semver("10.20.30") == (10, 20, 30)


@pytest.mark.parametrize(
    "invalid",
    [
        "v1.0.0",
        "1.0",
        "1.0.0-rc.1",
        "1.0.0+build123",
        "01.1.0",
        "1.0.0b1",
        "random",
        "",
    ],
)
def test_parse_semver_invalid(invalid: str) -> None:
    with pytest.raises(ValueError, match="Invalid version"):
        parse_semver(invalid)


def resolve_version_from_config(
    current_version: str,
    merged_pr_labels: list[list[str]],
    config: dict[str, Any],
) -> str:
    """Resolves the next version directly based on the parsed Release Drafter YAML config."""
    major, minor, patch = parse_semver(current_version)

    exclude_labels: set[str] = set(config.get("exclude-labels", []))
    resolver: dict[str, Any] = config.get("version-resolver", {})

    major_labels: set[str] = set(resolver.get("major", {}).get("labels", []))
    minor_labels: set[str] = set(resolver.get("minor", {}).get("labels", []))
    patch_labels: set[str] = set(resolver.get("patch", {}).get("labels", []))
    default_bump: str = resolver.get("default", "patch")

    bump_major = False
    bump_minor = False
    bump_patch = False

    for labels in merged_pr_labels:
        # Pre-exclusion: if PR has any excluded label, it is skipped
        if any(lbl in exclude_labels for lbl in labels):
            continue

        matched = False
        if any(lbl in major_labels for lbl in labels):
            bump_major = True
            matched = True
        elif any(lbl in minor_labels for lbl in labels):
            bump_minor = True
            matched = True
        elif any(lbl in patch_labels for lbl in labels):
            bump_patch = True
            matched = True

        if not matched:
            if default_bump == "patch":
                bump_patch = True
            elif default_bump == "minor":
                bump_minor = True
            elif default_bump == "major":
                bump_major = True

    if bump_major:
        return f"{major + 1}.0.0"
    elif bump_minor:
        return f"{major}.{minor + 1}.0"
    elif bump_patch:
        return f"{major}.{minor}.{patch + 1}"
    else:
        return current_version


def test_release_drafter_yaml_configuration() -> None:
    config_path = pathlib.Path(".github/release-drafter.yml")
    assert config_path.exists(), ".github/release-drafter.yml must exist"

    with open(config_path, encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f)

    assert config.get("include-pre-releases") is True
    assert "skip-changelog" in config.get("exclude-labels", [])
    assert config.get("name-template") == "v$RESOLVED_VERSION"
    assert config.get("tag-template") == "v$RESOLVED_VERSION"

    resolver = config.get("version-resolver", {})
    assert "release:major" in resolver.get("major", {}).get("labels", [])
    assert "release:minor" in resolver.get("minor", {}).get("labels", [])
    assert "release:patch" in resolver.get("patch", {}).get("labels", [])
    assert resolver.get("default") == "patch"

    # Test all scenarios directly against the loaded YAML config
    baseline = "0.1.0"

    # 1. Patch label: 0.1.0 -> 0.1.1
    assert resolve_version_from_config(baseline, [["release:patch"]], config) == "0.1.1"

    # 2. Minor label: 0.1.0 -> 0.2.0
    assert resolve_version_from_config(baseline, [["release:minor"]], config) == "0.2.0"

    # 3. Major label: 0.1.0 -> 1.0.0
    assert resolve_version_from_config(baseline, [["release:major"]], config) == "1.0.0"

    # 4. Minor and patch labels across merged PRs: Minor wins
    assert resolve_version_from_config(baseline, [["release:patch"], ["release:minor"]], config) == "0.2.0"
    assert resolve_version_from_config(baseline, [["release:patch", "release:minor"]], config) == "0.2.0"

    # 5. Major and minor labels across merged PRs: Major wins
    assert resolve_version_from_config(baseline, [["release:minor"], ["release:major"]], config) == "1.0.0"
    assert resolve_version_from_config(baseline, [["release:major", "release:minor"]], config) == "1.0.0"

    # 6. No release label on a merged PR: Patch fallback applies
    assert resolve_version_from_config(baseline, [[]], config) == "0.1.1"
    assert resolve_version_from_config(baseline, [["dependencies", "python:uv"]], config) == "0.1.1"

    # 7. Release-preparation PR labeled skip-changelog: Excluded from notes and version resolution
    assert resolve_version_from_config(baseline, [["skip-changelog"]], config) == "0.1.0"
    assert resolve_version_from_config(baseline, [["skip-changelog", "release:major"]], config) == "0.1.0"

    # 8. skip-changelog along with a normal unlabeled PR
    assert resolve_version_from_config(baseline, [["skip-changelog"], ["dependencies"]], config) == "0.1.1"


def test_gh_api_helpers_presence() -> None:
    assert callable(validate_release_version.gh_api_request)
