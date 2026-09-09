"""Gemara v1 schema types as Pydantic v2 models."""

from __future__ import annotations

from gemara.v1._loader import GemaraError, UnknownDocumentTypeError, load, loads
from gemara.v1._models import *
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
