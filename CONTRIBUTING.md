# Contributing

```bash
uv sync
uv run poe test        # pytest
uv run poe lint        # ruff check
uv run poe typecheck   # mypy --strict
uv run poe format      # ruff format
```

Dependencies are split into purpose-scoped groups, so a job or a contributor can
install only what it needs: `test`, `lint`, `codegen` (regenerating the models),
and `dev`, which includes all three. `uv sync` installs `dev`; `uv sync --only-group lint`
is enough to run the linters.

## How the models are produced

This consists of two steps.

1. `poe sync-schema`: needs `cue` on PATH plus network
access. It exports every `#Definition` from the upstream CUE module as JSON
Schema, merges them into `schemas/gemara-v1.schema.json`, records the exact ref
and digest in `schemas/provenance.json`, and re-vendors the upstream
`good-*`/`bad-*` corpus into `schemas/fixtures/`.

2. `poe generate`: reads the vendored schema, applies its repair passes,
calls `datamodel-code-generator` in-process, and writes `src/gemara/v1/_models.py`
and `_registry.py`.

Both generated files are committed. **Never edit them by hand**: CI regenerates
them and fails on any diff, so a hand edit is reverted on the next run.

The codegen invocation is fixed at
`--preset practical-py311-20260619 --schema-version 2020-12`, and
`datamodel-code-generator` and `ruff` are pinned exactly. Both touch generated
bytes, so an unpinned bump would churn thousands of committed lines and fail the
drift gate for no semantic reason. Do not add hand-picked generator flags.

## Bumping the schema version

```bash
uv run poe sync-schema   # optionally --ref vX.Y.Z
uv run poe generate
uv run poe test
```

Review the diff to `schemas/` and `src/gemara/v1/_models.py` together. A field
that got *looser* is the thing to watch for: a repair pass in `tools/generate.py`
may drop a constraint it cannot merge, and the only signal is a looser generated
type.

Update `SEMANTIC_GAPS` in `tests/test_fixtures.py` if the corpus changed. Read
the comment on that set for what it means and when to move an entry.

## Tests

The fixture corpus is vendored, so the suite runs anywhere with no `cue` and no
warm cache. CI fails the build if any test is skipped.

## Releasing

Publishing uses Trusted Publishing (OIDC); no API tokens are stored. The
`testpypi` and `pypi` GitHub environments must exist with a matching pending
publisher registered on each index.

- **Rehearse:** run the *Publish to TestPyPI* workflow manually
  (`workflow_dispatch`) against any ref or push a test tag matching `test-vX.Y.Z`.

### Release Versioning Policy

Release Drafter automatically maintains a draft release on GitHub as pull requests are merged into `main`. The next version is resolved from PR labels using SemVer:

- `release:major` / `major` / `breaking`: increments major version (`X+1.0.0`, e.g. `0.1.0` -> `1.0.0` or `1.2.3` -> `2.0.0`).
- `release:minor` / `minor` / `feature` / `enhancement`: increments minor version (`X.Y+1.0`, e.g. `0.1.0` -> `0.2.0`).
- `release:patch` / `patch` / `fix`: increments patch version (`X.Y.Z+1`, e.g. `0.1.0` -> `0.1.1`).

**Rules & Precedence:**
- **Baseline and pre-releases:** `include-pre-releases: true` is configured so that the existing `v0.1.0` pre-release acts as the baseline for change aggregation and next-version resolution.
- **Highest increment wins:** When multiple merged PRs carry different release labels, the highest bump applies (`major` > `minor` > `patch`).
- **Unlabeled PR fallback:** Pull requests merged without a release label default to a `patch` increment.
- **Exclusion of release preparation PRs:** Pull requests labeled `skip-changelog` (such as automated release-preparation PRs) are excluded from both changelog notes and version calculation.

### Maintainer Release Process

This repository uses the shared organization release workflow from [`github-community-projects/ospo-reusable-workflows`](https://github.com/github-community-projects/ospo-reusable-workflows) (pinned at `v2.3.1`).

1. **Check the Draft Release:**
   Inspect the active draft release under GitHub Releases. Verify the draft release notes and resolved tag (e.g., `v0.2.0`).

2. **Run the Version-Preparation Workflow:**
   Trigger the *Prepare Release* workflow (`.github/workflows/prepare-release.yml`) via `workflow_dispatch`, passing the target version without the `v` prefix (e.g. `0.2.0`).
   The workflow:
   - Validates that the target version is a stable `X.Y.Z` semver, is strictly newer than the latest published release, and matches the active draft tag.
   - Updates `pyproject.toml` with `uv version "<version>"` and verifies `uv.lock` with `uv lock --check`.
   - Runs test, lint, formatting, typechecking, and package build checks.
   - Opens or updates a release-preparation pull request targeting `main` with the `release` and `skip-changelog` labels on branch `release-prep/v<version>`. Re-running for the same version updates the existing PR without creating duplicates.

   *Note on workflow permissions:* If the PR is created using GitHub Actions default `GITHUB_TOKEN`, GitHub branch protection or actions policies may require a maintainer approval before CI runs on the PR.

3. **Review and Merge the Version PR:**
   Review and merge the release-preparation PR into `main` with the `release` label.

4. **Automated Release and PyPI Publishing:**
   When the version PR carrying the `release` label is merged to `main`, `.github/workflows/release.yml` executes:
   - Runs `github-community-projects/ospo-reusable-workflows/.github/workflows/release.yaml` to finalize and publish the GitHub release with tags `vX.Y.Z` and `vX`.
   - Directly executes the chained `publish-pypi` job in the same run to verify and publish the package to PyPI via Trusted Publishing (`id-token: write`).
   - Runs `verify-published` to test the published package on the live PyPI index.

### Troubleshooting & Mismatch Resolution

- **Draft / Tag / Package version mismatch:** If `pyproject.toml` does not match the published release tag `vX.Y.Z`, the release workflow fails immediately before building or publishing. Re-run *Prepare Release* for the matching version and ensure the PR is merged into `main` before publishing the release.
- **Lockfile mismatch:** If `uv.lock` is out of sync, `uv lock --check` fails during the preparation workflow. Run `uv lock` locally or re-sync dependencies.
- **Already published:** The validation script and PyPI trusted publishing prevent re-publishing an existing version.
