"""Guards on the vendored schema's own integrity: its provenance record, and
that every `$ref` in it actually resolves.

Hermetic and fast: no cue, no network -- these only read the committed
`schemas/gemara-v1.schema.json` and `schemas/provenance.json`.

Commit a21d87e fixed a dangling-`$ref` bug caused by cue's quoted identifiers
(e.g. `#"reference-id"`). The regression guards added there were unit tests on
synthetic inputs in `tests/test_sync_schema.py` -- nothing walked the real,
vendored schema's actual `$ref`s. A future upstream ref with a second quoted
shape `sync_schema.py` doesn't anticipate could reproduce that bug with every
existing test still green. `test_every_ref_resolves` is the guard that would
catch it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "gemara-v1.schema.json"
PROVENANCE_PATH = PROJECT_ROOT / "schemas" / "provenance.json"

SCHEMA_BYTES = SCHEMA_PATH.read_bytes()
SCHEMA = json.loads(SCHEMA_BYTES)
PROVENANCE = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))


def _iter_refs(node: Any) -> list[str]:
    """Every `$ref` string pointer found anywhere under `node`."""
    refs: list[str] = []
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            refs.append(ref)
        for value in node.values():
            refs.extend(_iter_refs(value))
    elif isinstance(node, list):
        for item in node:
            refs.extend(_iter_refs(item))
    return refs


def test_provenance_digest_matches_the_schema() -> None:
    assert hashlib.sha256(SCHEMA_BYTES).hexdigest() == PROVENANCE["schema_sha256"]


def test_schema_has_the_recorded_definition_count() -> None:
    assert len(SCHEMA["$defs"]) == PROVENANCE["definition_count"] == 93


def test_every_ref_resolves() -> None:
    """Walk every `$ref` in the schema; each must name a real `$defs` entry."""
    refs = _iter_refs(SCHEMA)
    assert len(refs) >= 50, f"only walked {len(refs)} $refs; the walk itself may be broken"

    defs = SCHEMA["$defs"]
    unresolved = []
    for ref in refs:
        if not ref.startswith("#/$defs/"):
            unresolved.append(ref)
            continue
        name = ref.removeprefix("#/$defs/")
        if name not in defs:
            unresolved.append(ref)

    assert unresolved == [], f"dangling $ref(s): {unresolved}"
