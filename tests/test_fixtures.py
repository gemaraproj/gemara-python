"""Conformance against the upstream good-*/bad-* corpus.

These fixtures are vendored under schemas/fixtures/, so this suite runs on a
bare CI runner. The predecessor read them from ~/.cache/cue and silently
skipped 39 of 40 tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from test_helpers import fixture_paths

from gemara.v1 import UnknownDocumentTypeError, load

GOOD = fixture_paths("good-")
BAD = fixture_paths("bad-")

# bad-* fixtures that the models correctly reject on structure alone.
STRUCTURALLY_REJECTED = {
    "bad-audit-log",
    "bad-audit-log-invalid-digest",
    "bad-enforcement-log",
    "bad-enforcement-missing-log",
    "bad-mapping-document",
}

# bad-* fixtures that parse anyway. Some are CUE cross-field semantics
# (uniqueness via hidden _unique* fields, referential checks via
# comprehensions) that cannot survive projection into JSON Schema -- but not
# all of these are guaranteed to be that; two of the previous fourteen
# (bad-enforcement-log, bad-enforcement-missing-log) turned out to be a
# codegen fidelity loss instead and were moved to STRUCTURALLY_REJECTED once
# `recover_array_allof_element_type` fixed it. Treat "still in this set" as
# "not yet proven recoverable", not as "provably a CUE limitation". They are
# pinned here and asserted to STILL parse: if a schema or Pydantic change
# starts catching one, this test fails and we find out rather than never
# noticing.
SEMANTIC_GAPS = {
    "bad-audit-log-undeclared-criteria",
    "bad-capability-invalid-group",
    "bad-control-invalid-group",
    "bad-enforcement-clear-failed",
    "bad-evaluation-log-missing-start",
    "bad-lexicon-duplicate-term-id",
    "bad-lifecycle",
    "bad-mapping-no-target",
    "bad-no-groups",
    "bad-principle-invalid-group",
    "bad-risk-catalog-duplicate-rank",
    "bad-threat-invalid-group",
}


def test_the_corpus_is_fully_accounted_for() -> None:
    """Every bad-* fixture is classified; no fixture is silently ignored."""
    assert {p.stem for p in BAD} == STRUCTURALLY_REJECTED | SEMANTIC_GAPS
    assert len(GOOD) == 19
    assert len(BAD) == 17


@pytest.mark.parametrize("path", GOOD, ids=lambda p: p.stem)
def test_good_fixture_validates(path: Path) -> None:
    load(path)


@pytest.mark.parametrize("path", GOOD, ids=lambda p: p.stem)
def test_good_fixture_round_trips(path: Path) -> None:
    """Dumping by alias in JSON mode must not lose or rename anything.

    The property asserted is that the JSON-mode dump is a fixed point: re-validating
    it and dumping again reproduces it exactly. Strict model equality (`second ==
    first`) is deliberately NOT asserted, because it cannot hold in general.
    `ControlEvaluation.assessment-logs` projects to `dict[str, Any]` instead of a
    fixed element model -- NOT because it is an unconstrained CUE type (it $refs
    the strict `_AssessmentLogStrict`/`AssessmentLog` definitions), but because its
    schema `allOf`s three array arms and all three carry `items`, so which is
    authoritative is ambiguous: typing it as `list[AssessmentLog]` would reject the
    good fixture `good-evaluation-log-unstarted`, because CUE defaults
    `requirement.reference-id` in from the control, a value the JSON Schema
    projection cannot supply. See `recover_array_allof_element_type` in
    `tools/generate.py`. Inside that `Any` region nothing is coerced. PyYAML parses
    an ISO timestamp into a native `datetime` while JSON leaves it a `str`, so the
    two representations differ by parser, not by information. The fixed point still
    proves no key is dropped or renamed and no value changes.
    """
    first = load(path)
    dumped = first.model_dump(by_alias=True, mode="json", exclude_none=True)
    redumped = type(first).model_validate(dumped).model_dump(by_alias=True, mode="json", exclude_none=True)
    assert redumped == dumped


@pytest.mark.parametrize(
    "path",
    [p for p in BAD if p.stem in STRUCTURALLY_REJECTED],
    ids=lambda p: p.stem,
)
def test_bad_fixture_is_rejected(path: Path) -> None:
    with pytest.raises((ValidationError, UnknownDocumentTypeError)):
        load(path)


@pytest.mark.parametrize(
    "path",
    [p for p in BAD if p.stem in SEMANTIC_GAPS],
    ids=lambda p: p.stem,
)
def test_known_semantic_gap_still_parses(path: Path) -> None:
    """Pinned so that newly-gained strictness is surfaced, not absorbed."""
    load(path)
