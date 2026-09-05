# Contributing

```bash
uv sync
uv run poe test        # pytest
uv run poe lint        # ruff check
uv run poe typecheck   # mypy --strict
uv run poe format      # ruff format
```

## How the models are produced

Two steps, deliberately separated by whether they need the outside world.

`poe sync-schema` is maintainer-only and needs `cue` on PATH plus network
access. It exports every `#Definition` from the upstream CUE module as JSON
Schema, merges them into `schemas/gemara-v1.schema.json`, records the exact ref
and digest in `schemas/provenance.json`, and re-vendors the upstream
`good-*`/`bad-*` corpus into `schemas/fixtures/`. JSON Schema rather than
upstream's OpenAPI projection, which loses integer types and flattens
`date-time` to `date`.

`poe generate` is hermetic — no `cue`, no network. It reads the vendored schema,
applies its repair passes, runs `datamodel-codegen`, and writes
`src/gemara/v1/_models.py` and `_registry.py`.

Both generated files are committed. **Never edit them by hand**: CI regenerates
them and fails on any diff, so a hand edit is reverted on the next run. Change
`tools/generate.py` instead, then `poe generate`.

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
that got *looser* is the thing to watch for — see the known limitation
documented on `recover_array_allof_element_type` in `tools/generate.py`.

Update `SEMANTIC_GAPS` in `tests/test_fixtures.py` if the corpus changed. Those
entries are asserted to *still parse*, so newly-gained strictness fails the
suite rather than passing unnoticed — that is the point of them.

## Tests

The fixture corpus is vendored, so the suite runs anywhere with no `cue` and no
warm cache. CI fails the build if **any** test is skipped: the predecessor read
its fixtures from `~/.cache/cue`, reported "1 passed, 39 skipped" on every run,
and stayed green on a single assertion for its entire life.

## Releasing

Publishing uses Trusted Publishing (OIDC); no API tokens are stored. The
`testpypi` and `pypi` GitHub environments must exist with a matching pending
publisher registered on each index.

- **Rehearse:** run the *Publish to TestPyPI* workflow manually
  (`workflow_dispatch`) against any ref.
- **Release:** set `version` in `pyproject.toml`, then push a matching `vX.Y.Z`
  tag. The release workflow refuses a tag that disagrees with that version, and
  refuses `0.0.0` outright.
