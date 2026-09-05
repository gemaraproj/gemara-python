# py-gemara

[Gemara](https://github.com/gemaraproj/gemara) v1 schema types as Pydantic v2
models, generated from the upstream CUE schemas.

```bash
pip install py-gemara
```

```python
from gemara.v1 import ControlCatalog, Lexicon, load

doc = load("catalog.yaml")  # dispatches on metadata.type

match doc:
    case ControlCatalog():
        print(len(doc.controls or []))
    case Lexicon():
        print(len(doc.terms or []))
```

`load` takes a path or an open file, `loads` takes text or bytes, and both read
JSON or YAML. They dispatch on `metadata.type` through `DOCUMENT_TYPES` — a
registry generated from the schema's own discriminators, so you never hand-write
a dispatch table — and return a `GemaraDocument`, the union of the 13 document
models. Narrowing it with `match` or `isinstance` typechecks under `mypy
--strict`; the package ships `py.typed`.

Failures raise from one hierarchy: `UnknownDocumentTypeError` when
`metadata.type` is missing or unrecognised (its message names the offending
value and the 13 valid ones), `GemaraError` for anything unparseable, and
`pydantic.ValidationError` when a document does not match its model.

`SCHEMA_VERSION` reports the Gemara release these models were generated from:
currently **v1.5.0**.

## Reading documents from a newer v1.x

Changes within Gemara v1 are additive, so these models read every v1.x document,
including ones written against a minor newer than `SCHEMA_VERSION`. Properties
they do not recognise are ignored — accepted, then dropped rather than carried
onto the model. This matches
[go-gemara](https://github.com/gemaraproj/go-gemara).

The consequence worth knowing: `load` followed by `model_dump` is **not** a
faithful copy of such a document, because its newer fields are absent from the
output. These models are a reader, not a round-tripping editor — keep the source
if you need to preserve it byte for byte.

## Known limitations

**These models are a structural validator, not a full Gemara validator.** CUE
enforces cross-field semantics — uniqueness via hidden `_unique*` fields,
referential integrity via comprehensions — that cannot survive projection into
JSON Schema. Measured against the upstream corpus at v1.5.0, 12 of 17 `bad-*`
fixtures parse successfully, including `bad-lexicon-duplicate-term-id`,
`bad-risk-catalog-duplicate-rank`, `bad-evaluation-log-missing-start`, and the
`bad-*-invalid-group` family.

What still applies: required fields, enums, patterns, and length bounds. If you
need full validation, run `cue vet` against the Gemara schemas.

## License

Apache-2.0.
