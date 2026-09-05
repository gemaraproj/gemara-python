"""Unit tests for the pure parts of the schema sync (no cue, no network)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import sync_schema  # noqa: E402


def test_merge_exports_flattens_nested_defs_and_roots() -> None:
    exports: dict[str, dict[str, Any]] = {
        "#Catalog": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": {"Group": {"type": "object"}},
            "type": "object",
            "properties": {"groups": {"$ref": "#/$defs/Group"}},
        },
        "#ArtifactType": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "enum": ["ControlCatalog", "Lexicon"],
        },
    }
    merged = sync_schema.merge_exports(exports)

    assert merged["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert set(merged["$defs"]) == {"Group", "Catalog", "ArtifactType"}
    # The root of an export becomes the def body, minus $schema/$defs.
    assert merged["$defs"]["Catalog"] == {
        "type": "object",
        "properties": {"groups": {"$ref": "#/$defs/Group"}},
    }
    assert merged["$defs"]["ArtifactType"] == {"enum": ["ControlCatalog", "Lexicon"]}


def test_merge_exports_keeps_the_first_nested_def_seen() -> None:
    """The same nested def is exported by many parents; they agree, so first wins."""
    exports: dict[str, dict[str, Any]] = {
        "#A": {"$defs": {"Shared": {"type": "string"}}, "type": "object"},
        "#B": {"$defs": {"Shared": {"type": "string"}}, "type": "object"},
    }
    merged = sync_schema.merge_exports(exports)
    assert merged["$defs"]["Shared"] == {"type": "string"}


def test_merge_exports_rejects_conflicting_nested_defs() -> None:
    exports: dict[str, dict[str, Any]] = {
        "#A": {"$defs": {"Shared": {"type": "string"}}, "type": "object"},
        "#B": {"$defs": {"Shared": {"type": "integer"}}, "type": "object"},
    }
    with pytest.raises(sync_schema.SyncError, match="conflicting definition 'Shared'"):
        sync_schema.merge_exports(exports)


def test_document_type_names_reads_the_artifact_type_enum() -> None:
    schema = {"$defs": {"ArtifactType": {"enum": ["Lexicon", "ControlCatalog"]}}}
    assert sync_schema.document_type_names(schema) == ["ControlCatalog", "Lexicon"]


def test_document_type_names_rejects_a_missing_enum() -> None:
    with pytest.raises(sync_schema.SyncError, match="ArtifactType"):
        sync_schema.document_type_names({"$defs": {}})


def test_strip_ref_encoding_removes_cue_percent_escapes() -> None:
    raw = '{"$ref": "#/$defs/%23Catalog"}'
    assert sync_schema.strip_ref_encoding(raw) == '{"$ref": "#/$defs/Catalog"}'


def test_strip_ref_encoding_removes_quoted_identifier_escapes() -> None:
    """cue emits a quoted identifier's surrounding quotes as `%22` in $ref pointers."""
    raw = '{"$ref": "#/$defs/%22reference-id%22"}'
    assert sync_schema.strip_ref_encoding(raw) == '{"$ref": "#/$defs/reference-id"}'


def test_merge_exports_unquotes_quoted_identifier_names() -> None:
    """cue's quoted identifiers (e.g. #"reference-id") keep literal quote characters
    in both the root export name and any nested $defs key; both must be stripped so
    the stored key matches a %22-decoded $ref pointing at it.
    """
    exports: dict[str, dict[str, Any]] = {
        '#"reference-id"': {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "string",
        },
        "#Field": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": {'"reference-id"': {"type": "string"}},
            "type": "object",
            "properties": {"ref": {"$ref": "#/$defs/reference-id"}},
        },
    }
    merged = sync_schema.merge_exports(exports)
    assert "reference-id" in merged["$defs"]
    assert merged["$defs"]["reference-id"] == {"type": "string"}
    assert not any('"' in key for key in merged["$defs"])
