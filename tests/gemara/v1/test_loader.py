"""Loader dispatch, input handling, and the error surface."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from gemara.v1 import (
    DOCUMENT_TYPES,
    SCHEMA_VERSION,
    ControlCatalog,
    GemaraError,
    GuidanceCatalog,
    UnknownDocumentTypeError,
    load,
    loads,
)

CATALOG: dict[str, Any] = {
    "metadata": {
        "id": "example",
        "author": {"id": "author-1", "name": "Example Author", "type": "Human"},
        "description": "A minimal catalog used to exercise dispatch.",
        "gemara-version": "1.5.0",
        "type": "ControlCatalog",
    },
    "title": "Example catalog",
}


def test_loads_dispatches_json_on_metadata_type() -> None:
    doc = loads(json.dumps(CATALOG))
    assert isinstance(doc, ControlCatalog)
    assert doc.metadata.type == "ControlCatalog"


def test_loads_accepts_yaml() -> None:
    text = "\n".join(
        [
            "metadata:",
            "  id: example",
            "  author:",
            "    id: author-1",
            "    name: Example Author",
            "    type: Human",
            "  description: A minimal catalog used to exercise dispatch.",
            "  gemara-version: 1.5.0",
            "  type: ControlCatalog",
            "title: Example catalog",
        ]
    )
    doc = loads(text)
    assert isinstance(doc, ControlCatalog)


def test_structurally_invalid_document_raises_validation_error() -> None:
    """Dispatch succeeds, then the model rejects it -- pydantic's error, not ours."""
    with pytest.raises(ValidationError):
        loads(json.dumps({"metadata": {"type": "ControlCatalog"}}))


def test_loads_accepts_bytes() -> None:
    doc = loads(json.dumps(CATALOG).encode())
    assert isinstance(doc, ControlCatalog)


def test_load_reads_a_path(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(CATALOG), encoding="utf-8")
    assert isinstance(load(path), ControlCatalog)


def test_load_reads_an_open_file_object(tmp_path: Path) -> None:
    """`load` follows `json.load`'s contract: it also accepts a file object."""
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(CATALOG), encoding="utf-8")
    with path.open(encoding="utf-8") as f:
        assert isinstance(load(f), ControlCatalog)


def test_document_model_from_file_returns_its_declared_type(tmp_path: Path) -> None:
    path = tmp_path / "catalog.yaml"
    path.write_text(json.dumps(CATALOG), encoding="utf-8")

    catalog = ControlCatalog.from_file(path)

    assert isinstance(catalog, ControlCatalog)


def test_document_model_from_text_returns_its_declared_type() -> None:
    catalog = ControlCatalog.from_text(json.dumps(CATALOG))

    assert isinstance(catalog, ControlCatalog)


def test_document_model_typed_loading_rejects_another_document_type() -> None:
    with pytest.raises(ValidationError, match="GuidanceCatalog"):
        GuidanceCatalog.from_text(json.dumps(CATALOG))


def test_loads_accepts_bytearray() -> None:
    doc = loads(bytearray(json.dumps(CATALOG), "utf-8"))
    assert isinstance(doc, ControlCatalog)


def test_loads_accepts_memoryview() -> None:
    doc = loads(memoryview(json.dumps(CATALOG).encode("utf-8")))
    assert isinstance(doc, ControlCatalog)


def test_unknown_type_names_the_value_and_the_valid_set() -> None:
    with pytest.raises(UnknownDocumentTypeError) as excinfo:
        loads(json.dumps({"metadata": {"type": "NotAThing"}}))
    message = str(excinfo.value)
    assert excinfo.value.value == "NotAThing"
    assert "NotAThing" in message
    for name in DOCUMENT_TYPES:
        assert name in message


def test_missing_type_raises_unknown_document_type_with_none() -> None:
    with pytest.raises(UnknownDocumentTypeError) as excinfo:
        loads(json.dumps({"metadata": {}}))
    assert excinfo.value.value is None


def test_non_mapping_document_is_rejected() -> None:
    with pytest.raises(GemaraError, match="mapping"):
        loads("[1, 2, 3]")


def test_malformed_yaml_raises_gemara_error_not_the_leaked_yaml_exception() -> None:
    """`yaml.parser.ParserError` must never escape; it is not in the docstring's
    exception contract and forces a consumer to import an optional dependency.
    """
    with pytest.raises(GemaraError):
        loads("a: [")


def test_tab_indented_json_raises_gemara_error_not_the_leaked_yaml_exception() -> None:
    """Valid JSON, tab-indented: PyYAML's scanner rejects tabs before JSON's
    parser gets a chance, and used to leak `yaml.scanner.ScannerError`.
    """
    with pytest.raises(GemaraError):
        loads('\t{"a": 1}')


@pytest.mark.parametrize(
    "buffer",
    [
        pytest.param(b"\xff\xfe not utf-8", id="bytes"),
        pytest.param(bytearray(b"\xff\xfe not utf-8"), id="bytearray"),
        pytest.param(memoryview(b"\xff\xfe not utf-8"), id="memoryview"),
    ],
)
def test_loads_contains_undecodable_bytes(buffer: bytes | bytearray | memoryview) -> None:
    """Decoding failure is a parse failure and must not leak `UnicodeDecodeError`.

    `loads` documents that no exception outside the `GemaraError` hierarchy (plus
    `ValidationError`) escapes it. Widening the accepted input to bytes-likes added
    a decode step in front of the parser, and that step is a second way in.
    """
    with pytest.raises(GemaraError):
        loads(buffer)


def test_loads_names_the_encoding_problem() -> None:
    with pytest.raises(GemaraError, match="UTF-8"):
        loads(b"\xff\xfe")


def test_load_contains_undecodable_bytes_from_a_path(tmp_path: Path) -> None:
    path = tmp_path / "catalog.yaml"
    path.write_bytes(b"\xff\xfe not utf-8")
    with pytest.raises(GemaraError):
        load(path)


def test_load_contains_undecodable_bytes_from_a_file_object() -> None:
    with pytest.raises(GemaraError):
        load(io.BytesIO(b"\xff\xfe not utf-8"))


def test_a_field_from_a_later_minor_is_accepted() -> None:
    """Gemara v1 is additive, so a v1.5.0 reader must not reject a v1.6.0 document."""
    doc = {**CATALOG, "metadata": dict(CATALOG["metadata"])}
    doc["field-added-in-a-later-minor"] = "hello"
    doc["metadata"]["field-added-in-a-later-minor"] = "hello"
    assert isinstance(loads(json.dumps(doc)), ControlCatalog)


def test_a_field_from_a_later_minor_is_not_carried_onto_the_model() -> None:
    """Unknown properties are accepted, then dropped -- not stored, not re-serialised.

    This matches go-gemara, where a property absent from the Go struct is neither
    retained nor re-marshalled, and it keeps the models honest as a typed surface:
    an attribute kept at runtime but absent from the stubs would be invisible to
    every type checker, in a package whose entire product is types.
    """
    doc = {**CATALOG, "metadata": dict(CATALOG["metadata"])}
    doc["field-added-in-a-later-minor"] = "hello"
    doc["metadata"]["field-added-in-a-later-minor"] = "hello"
    parsed = loads(json.dumps(doc))
    assert not hasattr(parsed, "field-added-in-a-later-minor")
    assert not hasattr(parsed.metadata, "field-added-in-a-later-minor")
    dumped = parsed.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert "field-added-in-a-later-minor" not in dumped
    assert "field-added-in-a-later-minor" not in dumped["metadata"]


def test_unknown_document_type_is_a_gemara_error() -> None:
    assert issubclass(UnknownDocumentTypeError, GemaraError)


def test_schema_version_matches_provenance() -> None:
    provenance = json.loads(
        (Path(__file__).resolve().parents[3] / "schemas" / "provenance.json").read_text(encoding="utf-8")
    )
    assert SCHEMA_VERSION == provenance["ref"].lstrip("v")
