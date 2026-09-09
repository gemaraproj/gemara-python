#!/usr/bin/env python3
"""Vendor the Gemara v1 JSON Schema, its provenance, and its test fixtures.

Maintainer-only: requires `cue` on PATH and network access. Everything it
produces is committed, so `tools/generate.py` and the test suite are hermetic.

Usage: python tools/sync_schema.py [--ref v1.5.0]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CUE_MODULE = "github.com/gemaraproj/gemara"
REPOSITORY = "https://github.com/gemaraproj/gemara"
DEFAULT_REF = "v1.5.0"
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = PROJECT_ROOT / "schemas"
SCHEMA_PATH = SCHEMA_DIR / "gemara-v1.schema.json"
PROVENANCE_PATH = SCHEMA_DIR / "provenance.json"
FIXTURE_DIR = SCHEMA_DIR / "fixtures"

FIXTURE_GLOBS = ("good-*", "bad-*")


class SyncError(RuntimeError):
    """A schema export or merge could not be completed."""


def strip_ref_encoding(raw: str) -> str:
    """cue emits `#` in $ref pointers as `%23`, and a quoted identifier's
    surrounding quotes as `%22`. Both escapes are removed outright (not decoded
    to a literal `"`, which would break the surrounding JSON) so a $ref lines up
    with the matching key produced by `_normalize_def_name`.
    """
    return raw.replace("%23", "").replace("%22", "")


def _normalize_def_name(raw: str) -> str:
    """Strip cue's leading `#` and, for a quoted identifier, its surrounding quotes.

    cue emits a plain definition as `#Name` and a quoted one (e.g. one containing
    a hyphen) as `#"a-name"`; nested $defs keys carry the same shapes minus the
    root's own name. Both must normalize to the bare name so they match a
    `strip_ref_encoding`-decoded $ref pointing at them.
    """
    name = raw.lstrip("#")
    if name.startswith('"') and name.endswith('"'):
        name = name[1:-1]
    return name


def _cue(*args: str) -> str:
    result = subprocess.run(["cue", *args], capture_output=True, encoding="utf-8", check=False)
    if result.returncode != 0:
        raise SyncError(f"cue {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def cue_version() -> str:
    for line in _cue("version").splitlines():
        if line.startswith("cue version "):
            return line.removeprefix("cue version ").strip()
    raise SyncError("could not parse `cue version` output")


def discover_definitions(ref: str) -> list[str]:
    """Every exported top-level definition, e.g. '#ControlCatalog'."""
    stdout = _cue("eval", f"{CUE_MODULE}@{ref}")
    names = {
        line.split(":")[0].split(" ")[0].strip()
        for line in stdout.splitlines()
        if line.startswith("#") and not line.startswith("#_")
    }
    if not names:
        raise SyncError(f"no definitions found in {CUE_MODULE}@{ref}")
    return sorted(names)


def export_definitions(names: list[str], ref: str) -> dict[str, dict[str, Any]]:
    exports: dict[str, dict[str, Any]] = {}
    for name in names:
        raw = _cue("def", "-e", name, "--out", "jsonschema", f"{CUE_MODULE}@{ref}")
        try:
            exports[name] = json.loads(strip_ref_encoding(raw))
        except json.JSONDecodeError as exc:
            raise SyncError(f"{name} exported invalid JSON Schema: {exc}") from exc
    return exports


def merge_exports(exports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Fold per-definition exports into one schema with a flat `$defs`.

    Each export carries its transitive dependencies under `$defs` and the
    definition itself at the root. Nested defs are shared across exports and
    must agree; a disagreement means the exports are not from one build.
    """
    defs: dict[str, Any] = {}
    for export in exports.values():
        for key, value in export.get("$defs", {}).items():
            key = _normalize_def_name(key)
            if key in defs and defs[key] != value:
                raise SyncError(f"conflicting definition '{key}' across exports")
            defs.setdefault(key, value)
    for name, export in exports.items():
        body = {k: v for k, v in export.items() if k not in ("$schema", "$defs")}
        key = _normalize_def_name(name)
        if key in defs and defs[key] != body:
            raise SyncError(f"conflicting definition '{key}' across exports")
        defs[key] = body
    return {"$schema": SCHEMA_DIALECT, "$defs": defs}


def document_type_names(schema: dict[str, Any]) -> list[str]:
    artifact_type = schema.get("$defs", {}).get("ArtifactType")
    if not isinstance(artifact_type, dict) or not isinstance(artifact_type.get("enum"), list):
        raise SyncError("schema has no #ArtifactType enum to derive document types from")
    return sorted(str(value) for value in artifact_type["enum"])


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def vendor_fixtures(ref: str) -> str:
    """Clone the schema repo at `ref` and copy its good-*/bad-* test data."""
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "gemara"
        cloned = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", ref, REPOSITORY, str(clone)],
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        if cloned.returncode != 0:
            raise SyncError(f"git clone --branch {ref} failed: {cloned.stderr.strip()}")

        rev_parsed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=clone,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        if rev_parsed.returncode != 0:
            raise SyncError(f"git rev-parse HEAD failed: {rev_parsed.stderr.strip()}")
        commit = rev_parsed.stdout.strip()

        source = clone / "test" / "test-data"
        if not source.is_dir():
            raise SyncError(f"{ref} has no test/test-data directory")

        if FIXTURE_DIR.exists():
            shutil.rmtree(FIXTURE_DIR)
        FIXTURE_DIR.mkdir(parents=True)

        copied = 0
        for pattern in FIXTURE_GLOBS:
            for path in sorted(source.glob(pattern)):
                shutil.copy2(path, FIXTURE_DIR / path.name)
                copied += 1
        if copied == 0:
            raise SyncError(f"no fixtures matched {FIXTURE_GLOBS} at {ref}")
        print(f"  vendored {copied} fixtures")
        return commit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default=DEFAULT_REF, help=f"upstream tag (default: {DEFAULT_REF})")
    args = parser.parse_args()
    ref: str = args.ref

    print(f"Syncing {CUE_MODULE}@{ref}")

    print("  Discovering definitions...")
    names = discover_definitions(ref)
    print(f"  Found {len(names)} definitions")

    print("  Exporting JSON Schema...")
    schema = merge_exports(export_definitions(names, ref))
    print(f"  Merged into {len(schema['$defs'])} $defs")

    doc_types = document_type_names(schema)
    print(f"  #ArtifactType declares {len(doc_types)} document types")

    print("  Vendoring fixtures...")
    commit = vendor_fixtures(ref)

    write_json(SCHEMA_PATH, schema)
    digest = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()

    write_json(
        PROVENANCE_PATH,
        {
            "module": CUE_MODULE,
            "repository": REPOSITORY,
            "ref": ref,
            "commit": commit,
            "cue_version": cue_version(),
            "retrieved": dt.date.today().isoformat(),
            "schema_sha256": digest,
            "definition_count": len(schema["$defs"]),
            "document_types": doc_types,
        },
    )

    print(f"  Wrote {SCHEMA_PATH.relative_to(PROJECT_ROOT)}")
    print(f"  Wrote {PROVENANCE_PATH.relative_to(PROJECT_ROOT)}")
    print("Run `uv run poe generate` next.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
