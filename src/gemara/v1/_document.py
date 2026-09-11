"""Shared typed loading constructors for generated document models."""

from __future__ import annotations

import os
from typing import IO, Self

from pydantic import BaseModel


class GemaraDocumentModel(BaseModel):
    """Base for top-level Gemara documents with typed parsing constructors."""

    @classmethod
    def from_text(cls, text: str | bytes | bytearray | memoryview) -> Self:
        """Parse JSON or YAML text into this document type."""
        # Import lazily: the loader's registry imports the generated models.
        from gemara.v1._loader import _loads_as

        return _loads_as(cls, text)

    @classmethod
    def from_file(cls, source: str | os.PathLike[str] | IO[str] | IO[bytes]) -> Self:
        """Read JSON or YAML from a path or open file into this document type."""
        from gemara.v1._loader import _read_source

        return cls.from_text(_read_source(source))
