"""Gemara v1 schema types as Pydantic v2 models."""

from __future__ import annotations

from importlib.metadata import version as _distribution_version

from gemara.v1._loader import GemaraError, UnknownDocumentTypeError, load, loads
from gemara.v1._models import *
from gemara.v1._models import __all__ as _MODEL_NAMES
from gemara.v1._registry import DOCUMENT_TYPES, SCHEMA_VERSION, GemaraDocument

__version__ = _distribution_version("gemara-python")

__all__ = [
    "DOCUMENT_TYPES",
    "SCHEMA_VERSION",
    "GemaraDocument",
    "GemaraError",
    "UnknownDocumentTypeError",
    "__version__",
    "load",
    "loads",
    *_MODEL_NAMES,
]
