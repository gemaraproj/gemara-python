# py-gemara

[Gemara](https://github.com/gemaraproj/gemara) v1 schema types as Pydantic v2
models, generated from the upstream CUE schemas.

```bash
pip install py-gemara          # core: pydantic only
pip install py-gemara[yaml]    # adds YAML support
```

```python
from gemara.v1 import load, DOCUMENT_TYPES, SCHEMA_VERSION, ControlCatalog

doc = load("catalog.yaml")  # dispatches on metadata.type
assert isinstance(doc, ControlCatalog)
```

`DOCUMENT_TYPES` maps each of the 13 `metadata.type` values to its model, and is
generated from the schema's discriminators — you never need to hand-maintain a
dispatch table. `load` and `loads` raise `UnknownDocumentTypeError` (naming the
offending value and the 13 valid ones) or `pydantic.ValidationError`.

Models are fully typed and the package ships `py.typed`.

## Versioning

`SCHEMA_VERSION` reports the Gemara schema release these models were generated
from: currently **v1.5.0**. Changes within Gemara v1 are additive by
construction — upstream CI enforces this with `oasdiff` — so one model set reads
every v1.x document.

**Documents from a newer v1.x are read, not rejected.** Properties these models
do not know about are ignored: accepted on the way in, then dropped rather than
carried onto the model or written back out — the same behaviour as
[go-gemara](https://github.com/gemaraproj/go-gemara), where a property with no
corresponding struct field is neither stored nor re-marshalled. Without this,
every additive release upstream would break every already-installed reader until
it re-synced, and a schema library that rejects valid documents of its own major
version is worse than no library.

The consequence worth knowing: `load` followed by `model_dump` is **not** a
faithful copy of a document written against a newer minor — unknown fields are
absent from the output. Treat these models as a reader, not a round-tripping
editor, and keep the source document if you need to preserve it byte for byte.

Strictness is relocated, not lost: required fields, enums, patterns and length
bounds still apply, and `cue vet` remains the source of truth for the rest.

There is also deliberately no per-minor namespace. Pinning to an older minor
would buy breakage, not safety.

A future `gemara.v2` will ship as a separate distribution, installable
side by side, because `gemara` is a PEP 420 namespace package.

## Known limitations

**These models are a structural validator, not a full Gemara validator.** CUE
enforces cross-field semantics — uniqueness via hidden `_unique*` fields,
referential integrity via comprehensions — that cannot survive projection into
JSON Schema. Measured against the upstream corpus at v1.5.0, 12 of 17 `bad-*`
fixtures parse successfully, including `bad-lexicon-duplicate-term-id`,
`bad-risk-catalog-duplicate-rank`, `bad-evaluation-log-missing-start`, and the
`bad-*-invalid-group` family.

If you need full validation, run `cue vet` against the Gemara schemas. The gaps
are pinned in `SEMANTIC_GAPS` in `tests/test_fixtures.py`, so any newly-gained
strictness fails the test suite instead of passing unnoticed.

## Development

```bash
uv sync
uv run poe test        # pytest
uv run poe lint        # ruff check
uv run poe typecheck   # mypy --strict
uv run poe generate    # regenerate _models.py and _registry.py (hermetic)
uv run poe sync-schema # re-vendor from upstream (maintainer only; needs cue)
```

`src/gemara/v1/_models.py` and `_registry.py` are generated and committed. CI
regenerates them and fails on any diff, so edit `tools/generate.py`, never the
output.

## License

Apache-2.0.
