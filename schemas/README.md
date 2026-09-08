# Schema Directory

This directory contains the vendored Gemara v1 JSON Schema and its upstream
conformance fixtures. Keeping these inputs in the repository makes code
generation and tests hermetic: contributors and CI do not need `cue` or network
to run them.

## Contents

- `gemara-v1.schema.json` is a single JSON Schema document containing every
  exported upstream definition.
- `fixtures/` contains the upstream `good-*` and `bad-*` test documents.
- `provenance.json` records the upstream tag and commit, CUE version, retrieval
  date, exported definitions, document types, and SHA-256 digest of the schema.

Do not edit these files by hand. Regenerate them from the named upstream
release so the schema, fixtures, and provenance remain a single traceable
snapshot.

## Updating the Schema

Install `cue`, ensure it is on `PATH`, and use a checkout with network access.
Then run the sync command for the intended upstream tag:

```bash
uv run poe sync-schema   # optionally --ref vX.Y.Z
uv run poe generate
uv run poe test
```

Omit `--ref` to use the script's default Gemara version. The sync command:

1. Discovers and exports every public CUE definition as JSON Schema.
2. Merges the exports into `gemara-v1.schema.json`.
3. Clones the same upstream tag and replaces `fixtures/` with its `good-*` and
   `bad-*` corpus.
4. Writes the exact upstream commit and schema digest to `provenance.json`.

`poe generate` then produces the Pydantic models from the vendored schema.
Review changes to `schemas/` and `src/gemara/v1/` together before committing.

## Fixture Process

Fixtures are copied verbatim from Gemara's `test/test-data` directory. The test
suite loads every `good-*` fixture and accounts for every `bad-*` fixture; an
empty fixture directory or an unclassified bad fixture fails the tests.

When the upstream corpus changes, update the fixture classification in
`tests/test_fixtures.py`. Fixtures in `STRUCTURALLY_REJECTED` must fail model
validation. Fixtures in `SEMANTIC_GAPS` are known CUE cross-field rules that
JSON Schema cannot currently express and are deliberately asserted to parse.
Move an entry between those sets only when the test result and underlying
validation capability have changed.
