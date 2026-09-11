"""Read a Gemara document and dispatch it to the right model."""

from __future__ import annotations

import os
from pathlib import Path
from typing import IO, Any, TypeVar, cast

import yaml
from pydantic import BaseModel

from gemara.v1._registry import DOCUMENT_TYPES, GemaraDocument

__all__ = ["GemaraError", "UnknownDocumentTypeError", "load", "loads"]

T = TypeVar("T", bound=BaseModel)


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


def _decode_text(text: str | bytes | bytearray | memoryview) -> str:
    """Return text unchanged or decode a bytes-like document as UTF-8."""
    return text if isinstance(text, str) else _decode(text)


def _parse(text: str) -> Any:
    """Parse JSON or YAML. YAML is a superset of JSON, so one parser covers both."""
    try:
        parsed: Any = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise GemaraError(f"could not parse the document as YAML or JSON: {exc}") from exc
    return parsed


def _loads_as(model: type[T], text: str | bytes | bytearray | memoryview) -> T:
    """Parse text and validate it as one explicitly selected document model."""
    return model.model_validate(_parse(_decode_text(text)))


def _read_source(source: str | os.PathLike[str] | IO[str] | IO[bytes]) -> str | bytes:
    """Read a path or an already-open text or binary file."""
    if isinstance(source, (str, os.PathLike)):
        return Path(source).read_bytes()
    return source.read()


def _dispatch(raw: Any) -> GemaraDocument:
    """Route a parsed mapping to the model selected by `metadata.type`."""
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
    return _dispatch(_parse(_decode_text(text)))


def load(source: str | os.PathLike[str] | IO[str] | IO[bytes]) -> GemaraDocument:
    """Read and parse a Gemara document from a file path or an open file.

    `source` follows the `json.load`/`pickle.load` convention: a path (`str`
    or `os.PathLike`), or an already-open file object providing `.read()`
    (e.g. the result of `open(path)`). Like `json.load`, the file may be opened
    in either text or binary mode; binary content is decoded as UTF-8.

    Raises the parsing and validation exceptions documented by `loads`, plus
    filesystem or stream I/O exceptions from reading `source`.
    """
    return loads(_read_source(source))
