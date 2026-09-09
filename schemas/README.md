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

The complete schema-update procedure, including prerequisites and review steps,
is maintained in [Contributing](../CONTRIBUTING.md#bumping-the-schema-version).

## Fixture Process

Fixtures are copied verbatim from Gemara's `test/test-data` directory. The test
suite loads every `good-*` fixture and accounts for every `bad-*` fixture; an
empty fixture directory or an unclassified bad fixture fails the tests.

When the upstream corpus changes, follow the fixture-classification instructions
in [Contributing](../CONTRIBUTING.md#bumping-the-schema-version).
