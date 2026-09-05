"""Read a Gemara document and dispatch it to the right model.

Hand-written; passes `mypy --strict`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import IO, Any, cast

import yaml

from gemara.v1._registry import DOCUMENT_TYPES, GemaraDocument

__all__ = ["GemaraError", "UnknownDocumentTypeError", "load", "loads"]


class GemaraError(Exception):
    """Base class for every error this package raises."""


class UnknownDocumentTypeError(GemaraError):
    """`metadata.type` was absent or not one of the known document types."""

    def __init__(self, value: object) -> None:
        self.value = value
        known = ", ".join(sorted(DOCUMENT_TYPES))
        super().__init__(f"unknown document type {value!r}; expected one of: {known}")


def _decode(data: bytes | bytearray | memoryview) -> str:
    """Decode UTF-8 bytes, turning a decoding failure into a `GemaraError`.

    Decoding is the first step that can reject a document, so it must raise from
    the same hierarchy as parsing -- otherwise widening `loads` to accept
    bytes-likes would reopen the leak that wrapping `yaml.YAMLError` closed.
    """
    try:
        return bytes(data).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GemaraError(f"document is not valid UTF-8: {exc}") from exc


def _parse(text: str) -> Any:
    """Parse JSON or YAML. YAML is a superset of JSON, so one parser covers both."""
    try:
        parsed: Any = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise GemaraError(f"could not parse the document as YAML or JSON: {exc}") from exc
    return parsed


def _dispatch(raw: Any) -> GemaraDocument:
    if not isinstance(raw, dict):
        raise GemaraError(f"a Gemara document must be a mapping, got {type(raw).__name__}")
    metadata = raw.get("metadata")
    document_type = metadata.get("type") if isinstance(metadata, dict) else None
    if not isinstance(document_type, str) or document_type not in DOCUMENT_TYPES:
        raise UnknownDocumentTypeError(document_type)
    model = DOCUMENT_TYPES[document_type]
    # DOCUMENT_TYPES' declared value type is `type[BaseModel]` (see
    # tools/generate.py's render_registry) so that adding a document type never
    # requires widening it by hand. The cast is sound because
    # `check_document_types` (run at generation time) guarantees DOCUMENT_TYPES'
    # values are exactly the GemaraDocument union's members -- a fact
    # `test_registry.py::test_gemara_document_alias_matches_document_types`
    # keeps honest.
    return cast(GemaraDocument, model.model_validate(raw))


def loads(text: str | bytes | bytearray | memoryview) -> GemaraDocument:
    """Parse a Gemara document from JSON or YAML text.

    `text` follows the `json.loads`/`pickle.loads` convention: a `str`, or
    bytes-like (`bytes`, `bytearray`, or `memoryview`) UTF-8-encoded text.

    Dispatches on `metadata.type`. Raises `GemaraError` (or a subclass) for
    every failure this function can produce: `GemaraError` itself if bytes-like
    input is not valid UTF-8, if the text cannot be parsed as YAML or JSON, or
    if the parsed value is not a mapping;
    `UnknownDocumentTypeError` (a `GemaraError` subclass) if `metadata.type` is
    missing or unrecognised; and `pydantic.ValidationError` if the document
    does not match its model. No other exception type -- in particular no
    `yaml.YAMLError` -- escapes this function.
    """
    if isinstance(text, str):
        decoded = text
    else:
        # `isinstance(text, bytes)` is False for `bytearray`/`memoryview`, so a
        # narrower check would let those buffers reach here undecoded and fail
        # deep inside YAML/JSON with an unhelpful internals error instead.
        decoded = _decode(text)
    return _dispatch(_parse(decoded))


def load(source: str | os.PathLike[str] | IO[str] | IO[bytes]) -> GemaraDocument:
    """Read and parse a Gemara document from a file path or an open file.

    `source` follows the `json.load`/`pickle.load` convention: a path (`str`
    or `os.PathLike`), or an already-open file object providing `.read()`
    (e.g. the result of `open(path)`). Like `json.load`, the file may be opened
    in either text or binary mode; binary content is decoded as UTF-8.

    Raises the same exceptions as `loads`, to which it delegates.
    """
    if isinstance(source, (str, os.PathLike)):
        return loads(Path(source).read_bytes())
    return loads(source.read())
