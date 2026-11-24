"""Validation helper for release preparation.

Validates that an input version is a stable semantic version (X.Y.Z),
is strictly newer than the latest published release, matches the active
Release Drafter draft tag, and does not collide with an existing tag or release.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import tomllib
import urllib.error
import urllib.request
from typing import Any

SEMVER_REGEX = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def parse_semver(version: str) -> tuple[int, int, int]:
    match = SEMVER_REGEX.match(version)
    if not match:
        raise ValueError(
            f"Invalid version '{version}'. Expected a stable semver in X.Y.Z format "
            "without prefixes or prerelease tags."
        )
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def gh_api_request(endpoint: str, token: str) -> Any:
    url = f"https://api.github.com{endpoint}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "gemara-python-release-validation",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate release version preparation.")
    parser.add_argument("--version", required=True, help="Target release version (X.Y.Z)")
    parser.add_argument("--repo", required=True, help="GitHub repository (owner/name)")
    args = parser.parse_args()

    target_version = args.version.strip()
    repo = args.repo.strip()

    try:
        target_tuple = parse_semver(target_version)
    except ValueError as e:
        print(f"::error::{e}", file=sys.stderr)
        sys.exit(1)

    # Check against currently declared pyproject.toml version
    pyproject_path = pathlib.Path("pyproject.toml")
    if pyproject_path.exists():
        pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        declared_version = pyproject_data.get("project", {}).get("version")
        if declared_version == target_version:
            print(
                f"::error::Target version '{target_version}' is already the declared version in pyproject.toml.",
                file=sys.stderr,
            )
            sys.exit(1)

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("::error::GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    # 1. Fetch all releases from GitHub to find the latest published release and check for drafts
    releases = gh_api_request(f"/repos/{repo}/releases?per_page=100", token)

    draft_releases = [r for r in releases if r.get("draft") is True]
    published_releases = [r for r in releases if not r.get("draft") and not r.get("prerelease")]
    # If no non-prerelease published releases exist, include prereleases as published baseline
    if not published_releases:
        published_releases = [r for r in releases if not r.get("draft")]

    # Check if target tag/release already exists
    target_tag = f"v{target_version}"
    for r in releases:
        if not r.get("draft") and r.get("tag_name") == target_tag:
            print(
                f"::error::A published release with tag '{target_tag}' already exists in {repo}.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Check git tags directly in the repo
    try:
        tag_check = gh_api_request(f"/repos/{repo}/git/ref/tags/{target_tag}", token)
        if tag_check:
            print(
                f"::error::A git tag '{target_tag}' already exists in {repo}.",
                file=sys.stderr,
            )
            sys.exit(1)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise

    # 2. Validate that target version is newer than the latest published release
    latest_published_tag: str | None = None
    latest_published_tuple: tuple[int, int, int] = (0, 0, 0)
    for r in published_releases:
        tag_name = r.get("tag_name", "")
        clean_tag = tag_name[1:] if tag_name.startswith("v") else tag_name
        try:
            parsed = parse_semver(clean_tag)
            if parsed > latest_published_tuple:
                latest_published_tuple = parsed
                latest_published_tag = tag_name
        except ValueError:
            continue

    if latest_published_tag and target_tuple <= latest_published_tuple:
        latest_v = ".".join(map(str, latest_published_tuple))
        print(
            f"::error::Target version '{target_version}' must be strictly newer than "
            f"the latest published release {latest_published_tag} ({latest_v}).",
            file=sys.stderr,
        )
        sys.exit(1)

    # 3. Check against Release Drafter draft
    if not draft_releases:
        print(
            "::error::No draft release found. Release Drafter should have created a draft release on PR merge.",
            file=sys.stderr,
        )
        sys.exit(1)

    matching_draft = next((d for d in draft_releases if d.get("tag_name") == target_tag), None)
    if not matching_draft:
        draft_tags = [d.get("tag_name") for d in draft_releases]
        print(
            f"::error::Target version '{target_version}' (expected tag '{target_tag}') "
            f"does not match any current draft release tag: {draft_tags}.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"Validation successful: target version {target_version} matches draft {target_tag} "
        f"and is newer than {latest_published_tag}."
    )


if __name__ == "__main__":
    main()
