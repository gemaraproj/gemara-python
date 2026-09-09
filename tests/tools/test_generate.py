"""Unit tests for the hermetic parts of codegen (no datamodel-codegen run)."""

from __future__ import annotations

import json
from typing import Any

import generate
import pytest


def _schema() -> dict[str, Any]:
    return {
        "$defs": {
            "ArtifactType": {"enum": ["ControlCatalog", "Lexicon"]},
            "ControlCatalog": {
                "type": "object",
                "properties": {
                    "metadata": {
                        "type": "object",
                        "properties": {"type": {"const": "ControlCatalog"}},
                    }
                },
            },
            "Lexicon": {
                "type": "object",
                "properties": {
                    "metadata": {
                        "type": "object",
                        "properties": {"type": {"const": "Lexicon"}},
                    }
                },
            },
            "Catalog": {
                "type": "object",
                "properties": {"metadata": {"$ref": "#/$defs/Metadata"}},
            },
        }
    }


def test_inject_metadata_titles_extracts_each_narrowed_metadata() -> None:
    schema = _schema()
    generate.inject_metadata_titles(schema)
    props = schema["$defs"]["ControlCatalog"]["properties"]
    assert props["metadata"] == {"$ref": "#/$defs/ControlCatalogMetadata"}
    assert schema["$defs"]["ControlCatalogMetadata"] == {
        "allOf": [
            {"$ref": "#/$defs/Metadata"},
            {"properties": {"type": {"const": "ControlCatalog"}}, "type": "object"},
        ]
    }


def test_inject_metadata_titles_returns_the_discriminator_map() -> None:
    doc_types = generate.inject_metadata_titles(_schema())
    assert doc_types == {"ControlCatalog": "ControlCatalog", "Lexicon": "Lexicon"}


def test_inject_metadata_titles_leaves_unnarrowed_metadata_alone() -> None:
    """The base Catalog's metadata is a plain $ref and must not be retitled."""
    schema = _schema()
    generate.inject_metadata_titles(schema)
    assert schema["$defs"]["Catalog"]["properties"]["metadata"] == {"$ref": "#/$defs/Metadata"}


def test_check_document_types_accepts_agreement_with_artifact_type() -> None:
    schema = _schema()
    doc_types = generate.inject_metadata_titles(schema)
    generate.check_document_types(schema, doc_types)  # does not raise


def test_check_document_types_rejects_a_missing_discriminator() -> None:
    """A destroyed discriminator must fail loudly at generation time."""
    schema = _schema()
    del schema["$defs"]["Lexicon"]["properties"]["metadata"]["properties"]
    doc_types = generate.inject_metadata_titles(schema)
    with pytest.raises(generate.GenerateError, match="Lexicon"):
        generate.check_document_types(schema, doc_types)


def test_ignore_unknown_properties_reopens_closed_objects() -> None:
    """Gemara v1 evolves additively, so a v1.5.0 reader must tolerate v1.6.0 fields.

    The key is removed rather than set to `true`: an unset `additionalProperties`
    generates no `extra` setting, and pydantic's default is "ignore" -- unknown
    properties are accepted and not carried onto the model, matching go-gemara,
    where a field absent from the struct is neither stored nor re-marshalled.
    """
    schema = {"$defs": {"Doc": {"type": "object", "additionalProperties": False, "properties": {}}}}
    generate.ignore_unknown_properties(schema)
    assert "additionalProperties" not in schema["$defs"]["Doc"]


def test_ignore_unknown_properties_reaches_nested_objects() -> None:
    schema: dict[str, Any] = {
        "$defs": {
            "Doc": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"inner": {"type": "object", "additionalProperties": False}},
            }
        }
    }
    generate.ignore_unknown_properties(schema)
    assert "additionalProperties" not in schema["$defs"]["Doc"]["properties"]["inner"]


def test_ignore_unknown_properties_leaves_schemas_alone_that_never_closed() -> None:
    """Only `false` is flipped; a schema constraining additionalProperties by type is untouched."""
    schema = {"$defs": {"Doc": {"type": "object", "additionalProperties": {"type": "string"}}}}
    generate.ignore_unknown_properties(schema)
    assert schema["$defs"]["Doc"]["additionalProperties"] == {"type": "string"}


def test_fold_hidden_definitions_replaces_refs_with_base_definitions() -> None:
    schema: dict[str, Any] = {
        "$defs": {
            "Mapping": {"type": "object"},
            "AssessmentLog": {"type": "object"},
            "FutureBase": {"type": "object"},
            "_MappingStrict": {"$ref": "#/$defs/Mapping", "type": "object"},
            "_AssessmentLogStrict": {"$ref": "#/$defs/AssessmentLog", "type": "object"},
            "_FutureWrapper": {"$ref": "#/$defs/FutureBase", "type": "object"},
            "Document": {
                "properties": {
                    "mapping": {"$ref": "#/$defs/_MappingStrict"},
                    "logs": {"items": {"$ref": "#/$defs/_AssessmentLogStrict"}, "type": "array"},
                    "future": {"$ref": "#/$defs/_FutureWrapper"},
                }
            },
        }
    }

    merged = generate.fold_hidden_definitions(schema)

    assert merged == 3
    assert schema["$defs"]["Document"]["properties"]["mapping"] == {"$ref": "#/$defs/Mapping"}
    assert schema["$defs"]["Document"]["properties"]["logs"]["items"] == {"$ref": "#/$defs/AssessmentLog"}
    assert schema["$defs"]["Document"]["properties"]["future"] == {"$ref": "#/$defs/FutureBase"}
    assert "_MappingStrict" not in schema["$defs"]
    assert "_AssessmentLogStrict" not in schema["$defs"]
    assert "_FutureWrapper" not in schema["$defs"]


def test_fold_hidden_definitions_rejects_hidden_constraints() -> None:
    schema: dict[str, Any] = {
        "$defs": {
            "Base": {"type": "object"},
            "_Constrained": {"$ref": "#/$defs/Base", "required": ["value"], "type": "object"},
        }
    }

    with pytest.raises(generate.GenerateError, match="cannot be safely folded"):
        generate.fold_hidden_definitions(schema)


def test_render_registry_emits_sorted_typed_entries() -> None:
    source = generate.render_registry(
        {"Lexicon": "Lexicon", "ControlCatalog": "ControlCatalog"},
        schema_version="1.5.0",
        model_names=["ControlCatalog", "Lexicon"],
    )
    assert 'SCHEMA_VERSION: Final[str] = "1.5.0"' in source
    assert '"ControlCatalog": _models.ControlCatalog,' in source
    assert source.index('"ControlCatalog"') < source.index('"Lexicon"')
    assert "Do not edit" in source
    assert "GemaraDocument: TypeAlias = _models.ControlCatalog | _models.Lexicon" in source
    assert '"GemaraDocument"' in source


def test_public_model_names_reads_classes_from_source() -> None:
    names = generate.public_model_names("class Alpha(BaseModel):\n    pass\n\n\nclass _Private:\n    pass\n")
    assert names == ["Alpha"]


def test_render_models_excludes_denylisted_names_from_all() -> None:
    source = generate.render_models(
        "from __future__ import annotations\n\n"
        "class Catalog(BaseModel):\n    pass\n\n\n"
        "class Log(BaseModel):\n    pass\n\n\n"
        "class Alpha(BaseModel):\n    pass\n",
        ["Alpha", "Model", "Type"],
        ["Alpha"],
    )
    assert '"Alpha",' in source
    assert '"Model",' not in source
    assert '"Type",' not in source
    assert "from gemara.v1._document import GemaraDocumentModel" in source
    assert "class Alpha(GemaraDocumentModel):" in source


def test_render_models_makes_category_bases_document_models() -> None:
    source = generate.render_models(
        "from __future__ import annotations\n\nclass Catalog(BaseModel):\n    pass\n\n\n"
        "class Log(BaseModel):\n    pass\n\n\n"
        "class ControlCatalog(BaseModel):\n    pass\n",
        ["Catalog", "Log", "ControlCatalog"],
        ["ControlCatalog"],
    )
    assert "class Catalog(GemaraDocumentModel):" in source
    assert "class ControlCatalog(Catalog):" in source


def test_recover_array_allof_element_type_collapses_a_single_items_arm() -> None:
    """EnforcementLog.actions shape: one arm is comprehension metadata with no
    `items`, the other carries the real element type. Exactly one arm has
    `items`, so the node collapses to that arm, keeping the outer `description`
    since the winning arm does not define one of its own.
    """
    node: dict[str, Any] = {
        "allOf": [
            {"description": "Enforce that Clear dispositions only contain Passed results", "type": "array"},
            {"items": {"$ref": "#/$defs/ActionResult"}, "minItems": 1, "type": "array"},
        ],
        "description": "actions is the list of enforcement actions performed",
    }
    schema: dict[str, Any] = {"$defs": {"EnforcementLog": {"properties": {"actions": node}}}}
    collapsed = generate.recover_array_allof_element_type(schema)
    actions = schema["$defs"]["EnforcementLog"]["properties"]["actions"]
    assert "allOf" not in actions
    assert actions["items"] == {"$ref": "#/$defs/ActionResult"}
    assert actions["minItems"] == 1
    assert actions["description"] == "actions is the list of enforcement actions performed"
    assert collapsed == 1


def test_recover_array_allof_element_type_leaves_multi_item_arms_untouched() -> None:
    """ControlEvaluation.assessment-logs shape: all three arms carry `items`, so
    which is authoritative is ambiguous and the node must be left alone.
    """
    node: dict[str, Any] = {
        "allOf": [
            {"items": {"type": "object"}, "type": "array"},
            {"items": {"$ref": "#/$defs/_AssessmentLogStrict"}, "minItems": 1, "type": "array"},
            {"items": {"$ref": "#/$defs/AssessmentLog"}, "minItems": 1, "type": "array"},
        ],
        "description": "assessment logs",
    }
    schema: dict[str, Any] = {"$defs": {"ControlEvaluation": {"properties": {"assessment-logs": node}}}}
    before = json.loads(json.dumps(schema))
    collapsed = generate.recover_array_allof_element_type(schema)
    assert schema == before
    assert collapsed == 0


def test_recover_array_allof_element_type_leaves_non_array_allof_untouched() -> None:
    """MappingTarget.strength shape: arms are `number`/`integer`, not `array`."""
    node: dict[str, Any] = {
        "allOf": [{"type": "number"}, {"maximum": 10, "minimum": 1, "type": "integer"}],
        "description": "strength",
    }
    schema: dict[str, Any] = {"$defs": {"MappingTarget": {"properties": {"strength": node}}}}
    before = json.loads(json.dumps(schema))
    collapsed = generate.recover_array_allof_element_type(schema)
    assert schema == before
    assert collapsed == 0
