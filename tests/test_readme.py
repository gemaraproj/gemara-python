"""The README must carry the limitation the spec requires to be stated."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
README = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")


def test_readme_states_the_structural_validator_limitation() -> None:
    # Extract the "## Known limitations" section
    assert "## Known limitations" in README, "README must have a '## Known limitations' section"

    # Get content from "## Known limitations" to the next "## " heading (or EOF)
    known_limitations_start = README.find("## Known limitations")
    remaining = README[known_limitations_start:]
    next_section = remaining.find("## ", 2)  # Skip the current "##" and find the next one
    if next_section == -1:
        known_limitations_section = remaining
    else:
        known_limitations_section = remaining[:next_section]

    # Both the limitation statement and escape hatch must be in the section
    assert "structural validator, not a full Gemara validator" in known_limitations_section, (
        "Limitation statement must appear in '## Known limitations' section"
    )
    assert "cue vet" in known_limitations_section, (
        "'cue vet' escape hatch must appear in '## Known limitations' section"
    )


def test_readme_pins_the_same_schema_version_as_provenance() -> None:
    provenance = json.loads((PROJECT_ROOT / "schemas" / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["ref"] in README
