# gemara-python

## What This Is

`gemara-python` provides generated Pydantic v2 models for
[Gemara](https://github.com/gemaraproj/gemara) v1 documents.
Use it to load, validate, and work with Gemara JSON or YAML in Python.

## How to Install

```bash
pip install gemara-python
```

## Getting Started

```python
from gemara.v1 import ControlCatalog, Lexicon, load

doc = load("catalog.yaml")  # dispatches on metadata.type

match doc:
    case ControlCatalog():
        print(len(doc.controls or []))
    case Lexicon():
        print(len(doc.terms))
```

`load` accepts a file path or open file. Use `loads` for JSON or YAML text and
bytes. Both return the model selected by `metadata.type`.

When the expected document type is already known, load it directly from the
model to receive that concrete type without dispatching:

```python
from gemara.v1 import GuidanceCatalog

guidance = GuidanceCatalog.from_file("guidance.yaml")
```

`from_file` accepts a file path or open file. `from_text` accepts JSON or YAML
text and bytes. Both validate the input as the selected document model.

## Reference

- `DOCUMENT_TYPES` contains the supported document models.
- `SCHEMA_VERSION` is the Gemara release used to generate the models
- Invalid input raises `GemaraError`, `UnknownDocumentTypeError`, or
  `pydantic.ValidationError`.
- `load` and `from_file` also propagate filesystem and stream I/O exceptions.

## Compatibility

Changes within Gemara v1 are additive, so these models read every v1.x document,
including ones written against a minor newer than `SCHEMA_VERSION`. Properties
they do not recognize are accepted and dropped rather than carried onto the
model.

## Known limitations

**These models are a structural validator, not a full Gemara validator.** CUE
enforces cross-field semantics — uniqueness via hidden `_unique*` fields,
referential integrity via comprehensions -- that cannot survive projection into
JSON Schema.

What still applies: required fields, enums, patterns, and length bounds. If you
need full validation, run `cue vet` against the Gemara schemas.

## License

Apache-2.0.
