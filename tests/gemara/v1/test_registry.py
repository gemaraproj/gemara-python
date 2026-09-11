"""The registry must be derived, complete, and in step with #ArtifactType."""

from __future__ import annotations

import json
import typing
from importlib.metadata import version
from pathlib import Path

from pydantic import BaseModel

from gemara.v1 import DOCUMENT_TYPES, Catalog, GemaraDocument, Log, Metadata, __version__
from gemara.v1._document import GemaraDocumentModel

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schemas"


def test_registry_matches_the_artifact_type_enum() -> None:
    schema = json.loads((SCHEMA_DIR / "gemara-v1.schema.json").read_text(encoding="utf-8"))
    declared = set(schema["$defs"]["ArtifactType"]["enum"])
    assert set(DOCUMENT_TYPES) == declared


def test_registry_has_thirteen_document_types() -> None:
    assert len(DOCUMENT_TYPES) == 13


def test_package_version_matches_distribution_metadata() -> None:
    assert __version__ == version("gemara-python")


def test_every_registry_entry_is_a_model() -> None:
    for name, model in DOCUMENT_TYPES.items():
        assert issubclass(model, BaseModel), name
        assert issubclass(model, GemaraDocumentModel), name


def test_every_model_narrows_its_metadata_type() -> None:
    """Dispatch depends on each model's narrowed metadata type."""
    for name, model in DOCUMENT_TYPES.items():
        metadata = model.model_fields["metadata"].annotation
        assert metadata is not None
        assert metadata.__name__ == f"{name}Metadata", name
        assert issubclass(metadata, Metadata), name


def test_gemara_document_alias_matches_document_types() -> None:
    """`GemaraDocument` must cover exactly the registry, so it cannot drift."""
    members = set(typing.get_args(GemaraDocument))
    assert members == set(DOCUMENT_TYPES.values())
    assert len(members) == 13


def test_catalog_models_share_the_catalog_runtime_base() -> None:
    assert "imports" in Catalog.model_fields
    for name, model in DOCUMENT_TYPES.items():
        assert issubclass(model, Catalog) is name.endswith("Catalog")


def test_log_models_share_the_log_runtime_base() -> None:
    assert "target" in Log.model_fields
    for name, model in DOCUMENT_TYPES.items():
        assert issubclass(model, Log) is name.endswith("Log")


def test_documents_narrow_to_their_category_via_isinstance() -> None:
    """The tier's point: a consumer narrows any dispatched document by
    `isinstance` -- e.g. to gather every catalog's `imports` or every log's
    `target` -- instead of re-reading `metadata.type`."""
    for name, model in DOCUMENT_TYPES.items():
        doc = model.model_construct()
        assert isinstance(doc, Catalog) is name.endswith("Catalog"), name
        assert isinstance(doc, Log) is name.endswith("Log"), name
