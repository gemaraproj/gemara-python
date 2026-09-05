"""Gemara v1 schema types as Pydantic v2 models.

    from gemara.v1 import load, DOCUMENT_TYPES, ControlCatalog

    doc = load("catalog.yaml")   # dispatches on metadata.type

The models are a *structural* validator. See the README's known limitations.
"""

from __future__ import annotations

from gemara.v1._loader import GemaraError, UnknownDocumentTypeError, load, loads
from gemara.v1._models import *  # noqa: F403
from gemara.v1._models import __all__ as _MODEL_NAMES
from gemara.v1._registry import DOCUMENT_TYPES, SCHEMA_VERSION, GemaraDocument

__all__ = [
    "DOCUMENT_TYPES",
    "SCHEMA_VERSION",
    "GemaraDocument",
    "GemaraError",
    "UnknownDocumentTypeError",
    "load",
    "loads",
    *_MODEL_NAMES,
]
