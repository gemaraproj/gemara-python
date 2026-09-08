"""The registry must be derived, complete, and in step with #ArtifactType."""

from __future__ import annotations

import json
import typing
from pathlib import Path

from pydantic import BaseModel

from gemara.v1 import DOCUMENT_TYPES, GemaraDocument

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schemas"


def test_registry_matches_the_artifact_type_enum() -> None:
    schema = json.loads((SCHEMA_DIR / "gemara-v1.schema.json").read_text(encoding="utf-8"))
    declared = set(schema["$defs"]["ArtifactType"]["enum"])
    assert set(DOCUMENT_TYPES) == declared


def test_registry_has_thirteen_document_types() -> None:
    assert len(DOCUMENT_TYPES) == 13


def test_every_registry_entry_is_a_model() -> None:
    for name, model in DOCUMENT_TYPES.items():
        assert issubclass(model, BaseModel), name


def test_every_model_narrows_its_metadata_type() -> None:
    """Defect 4 regression guard: dispatch depends on this narrowing."""
    for name, model in DOCUMENT_TYPES.items():
        metadata = model.model_fields["metadata"].annotation
        assert metadata is not None
        assert metadata.__name__ == f"{name}Metadata", name


def test_gemara_document_alias_matches_document_types() -> None:
    """`GemaraDocument` must cover exactly the registry, so it cannot drift."""
    members = set(typing.get_args(GemaraDocument))
    assert members == set(DOCUMENT_TYPES.values())
    assert len(members) == 13
