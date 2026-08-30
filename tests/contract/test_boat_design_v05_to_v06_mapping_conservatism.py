"""Mechanical conservativity check for the v0.5 -> v0.6 rig/rudder mapping.

`docs/engineering/BOAT_DESIGN_V05_TO_V06_MAPPING.md` §3 documents, in prose
tables, how the v0.5 combined `rig_type` and `rudder_type` tokens translate into
the v0.6 decomposed fields. Independent review found the original tables
over-inferred: they asserted decomposed facts (e.g. `ketch -> masthead_fractional:
not_applicable`, `spade -> rudder_balance: balanced`) that the v0.5 token never
actually encoded (amendment 1).

A second review then found amendment 1 over-corrected one case: `rudder_type =
"twin"` definitionally guarantees two rudders, and the mapping had started
discarding that guaranteed fact by leaving `rudder_count` untouched even when
the source had it as `null`. `project_rudder_count` below (amendment 2) restores
that one guaranteed projection while refusing to silently resolve a `twin`
record whose source `rudder_count` disagrees (a concrete value other than `2`).

This module transcribes the corrected tables/rules as literal Python data and
functions, then enforces the *governing rule itself* -- not just "does the code
match the table" (which would let a bug in both drift together undetected) --
so a future edit cannot silently reintroduce an invented fact, or silently
resolve a contradictory predecessor payload, without an explicit, reviewed
change to the enforcement rule below, not merely to the table.

None of this is wired into the persistence importer/readback path; it is a
standalone compatibility check, not a production migration.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from hullq.contracts import ContractRegistry

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
FIXTURES_DIR = ROOT / "fixtures" / "technical_profile" / "valid"

_REGISTRY = ContractRegistry.from_directory(SPECS)
_V06 = _REGISTRY.validator_by_name("BOAT_DESIGN_SCHEMA.v0.6.json")

_V05_SCHEMA = json.loads((SPECS / "BOAT_DESIGN_SCHEMA.v0.5.json").read_text(encoding="utf-8"))
_V05_RIG_TYPE_ENUM = set(
    _V05_SCHEMA["properties"]["baseline"]["properties"]["configuration"]["properties"]["rig_type"][
        "enum"
    ]
)
_V05_RUDDER_TYPE_ENUM = set(
    _V05_SCHEMA["properties"]["baseline"]["properties"]["configuration"]["properties"][
        "rudder_type"
    ]["enum"]
)

# Transcription of docs/engineering/BOAT_DESIGN_V05_TO_V06_MAPPING.md §3.1.
RIG_TYPE_MAPPING: dict[str, dict[str, str]] = {
    "masthead_sloop": {"sailplan": "sloop", "masthead_fractional": "masthead"},
    "fractional_sloop": {"sailplan": "sloop", "masthead_fractional": "fractional"},
    "cutter": {"sailplan": "cutter", "masthead_fractional": "unknown"},
    "ketch": {"sailplan": "ketch", "masthead_fractional": "unknown"},
    "yawl": {"sailplan": "yawl", "masthead_fractional": "unknown"},
    "schooner": {"sailplan": "schooner", "masthead_fractional": "unknown"},
    "cat_rig": {"sailplan": "cat", "masthead_fractional": "unknown"},
    "other": {"sailplan": "other", "masthead_fractional": "unknown"},
    "unknown": {"sailplan": "unknown", "masthead_fractional": "unknown"},
}

# Transcription of docs/engineering/BOAT_DESIGN_V05_TO_V06_MAPPING.md §3.2.
# Deliberately has no "rudder_count" key anywhere: rudder_count projection is
# handled separately by project_rudder_count() below, since -- uniquely for
# "twin" -- the correct projection depends on the *source* rudder_count value,
# not on rudder_type alone (a static per-token table entry cannot express that).
RUDDER_TYPE_MAPPING: dict[str, dict[str, str]] = {
    "keel_hung": {
        "rudder_position": "unknown",
        "rudder_support": "keel",
        "rudder_balance": "unknown",
    },
    "skeg_hung": {
        "rudder_position": "unknown",
        "rudder_support": "skeg",
        "rudder_balance": "unknown",
    },
    "partial_skeg": {
        "rudder_position": "unknown",
        "rudder_support": "skeg",
        "rudder_balance": "unknown",
    },
    "spade": {"rudder_position": "unknown", "rudder_support": "free", "rudder_balance": "unknown"},
    "transom_hung": {
        "rudder_position": "transom",
        "rudder_support": "transom",
        "rudder_balance": "unknown",
    },
    "twin": {
        "rudder_position": "unknown",
        "rudder_support": "unknown",
        "rudder_balance": "unknown",
    },
    "other": {
        "rudder_position": "unknown",
        "rudder_support": "unknown",
        "rudder_balance": "unknown",
    },
    "unknown": {
        "rudder_position": "unknown",
        "rudder_support": "unknown",
        "rudder_balance": "unknown",
    },
}


class RudderCountMappingConflict(ValueError):
    """A v0.5 payload's rudder_type and rudder_count logically disagree.

    Raised, never silently resolved, by project_rudder_count() below. Mirrors
    the "applicability before conflict" / 6-8-eye principle in
    TECHNICAL_PROFILE_SPEC.v0.1.md SS5/SS6: two disagreeing predecessor facts are
    flagged for manual/conflict resolution, not mechanically arbitrated.
    """


def project_rudder_count(rudder_type: str, source_rudder_count: int | None) -> int | None:
    """Project v0.5 baseline.appendages.rudder_count into v0.6, per mapping doc SS3.2.

    A straight passthrough for every rudder_type except "twin": "twin" is
    definitionally two rudders, so a null/unrecorded source count is projected
    as 2 (a guaranteed fact, not a guess) and an already-2 source count stays 2.
    A concrete source count other than 2 combined with rudder_type="twin" is an
    internally inconsistent v0.5 payload; this function refuses to silently
    pick a winner and raises RudderCountMappingConflict instead.
    """
    if rudder_type != "twin":
        return source_rudder_count
    if source_rudder_count is None or source_rudder_count == 2:
        return 2
    raise RudderCountMappingConflict(
        f"v0.5 payload has rudder_type='twin' but rudder_count={source_rudder_count!r}; "
        "this is an internally inconsistent predecessor record. This compatibility "
        "mapping does not silently resolve it -- flag for manual/conflict resolution "
        "(TECHNICAL_PROFILE_SPEC.v0.1.md SS5/SS6)."
    )


# ---------------------------------------------------------------------------
# Completeness: the table must cover exactly the v0.5 enum, sourced from the
# schema file itself so this cannot silently go stale.
# ---------------------------------------------------------------------------


def test_rig_type_mapping_covers_exactly_the_v05_enum() -> None:
    assert set(RIG_TYPE_MAPPING.keys()) == _V05_RIG_TYPE_ENUM


def test_rudder_type_mapping_covers_exactly_the_v05_enum() -> None:
    assert set(RUDDER_TYPE_MAPPING.keys()) == _V05_RUDDER_TYPE_ENUM


# ---------------------------------------------------------------------------
# Governing rule, enforced independently of the table's own content: a
# decomposed value may only be non-"unknown" where the v0.5 token itself
# literally proves it.
# ---------------------------------------------------------------------------

_TOKENS_THAT_PROVE_MASTHEAD_FRACTIONAL = {"masthead_sloop", "fractional_sloop"}


def test_masthead_fractional_is_unknown_except_where_the_v05_token_proves_it() -> None:
    for rig_type, row in RIG_TYPE_MAPPING.items():
        if rig_type in _TOKENS_THAT_PROVE_MASTHEAD_FRACTIONAL:
            assert row["masthead_fractional"] != "unknown", (
                f"{rig_type!r} literally names masthead/fractional character and must not be unknown"
            )
        else:
            assert row["masthead_fractional"] == "unknown", (
                f"{rig_type!r} does not prove masthead/fractional character; "
                f"must not assert {row['masthead_fractional']!r} (was not_applicable before the "
                "post-review correction for ketch/yawl/schooner/cat_rig -- see mapping doc SS3.1)"
            )


def test_no_rig_type_token_asserts_not_applicable() -> None:
    # not_applicable remains a legitimate v0.6 value for freshly-researched data,
    # but no v0.5 token logically guarantees it, so the mapping must never emit it.
    asserted = {row["masthead_fractional"] for row in RIG_TYPE_MAPPING.values()}
    assert "not_applicable" not in asserted


def test_rudder_balance_is_always_unknown() -> None:
    # No v0.5 rudder_type token encodes balance at all -- not even transom_hung
    # or spade, which merely describe support/position, not balance style.
    for rudder_type, row in RUDDER_TYPE_MAPPING.items():
        assert row["rudder_balance"] == "unknown", (
            f"{rudder_type!r} does not encode rudder balance in v0.5; "
            f"must not assert {row['rudder_balance']!r}"
        )


_TOKENS_THAT_PROVE_RUDDER_POSITION = {"transom_hung"}


def test_rudder_position_is_unknown_except_where_the_v05_token_proves_it() -> None:
    for rudder_type, row in RUDDER_TYPE_MAPPING.items():
        if rudder_type in _TOKENS_THAT_PROVE_RUDDER_POSITION:
            assert row["rudder_position"] == "transom"
        else:
            assert row["rudder_position"] == "unknown", (
                f"{rudder_type!r} does not prove rudder position; support (a different, "
                f"independent v0.6 field) must not be conflated into position -- must not assert "
                f"{row['rudder_position']!r}"
            )


def test_rudder_support_is_unknown_unless_the_v05_token_names_the_support_mechanism() -> None:
    literal_support = {
        "keel_hung": "keel",
        "skeg_hung": "skeg",
        "partial_skeg": "skeg",
        "spade": "free",
        "transom_hung": "transom",
    }
    for rudder_type, row in RUDDER_TYPE_MAPPING.items():
        expected = literal_support.get(rudder_type, "unknown")
        assert row["rudder_support"] == expected, (
            f"{rudder_type!r}: rudder_support must be {expected!r} (definitionally proven by the "
            f"v0.5 token's own name), not {row['rudder_support']!r}"
        )


def test_rudder_type_mapping_never_asserts_other_for_every_field_simultaneously() -> None:
    # Regression for the specific defect flagged by review: an opaque v0.5
    # "other" must not cascade into "other" on every decomposed dimension.
    other_row = RUDDER_TYPE_MAPPING["other"]
    assert list(other_row.values()) != ["other", "other", "other"]
    assert all(value == "unknown" for value in other_row.values())


# ---------------------------------------------------------------------------
# rudder_count projection: twin is the one narrow, guaranteed exception to the
# "rudder_count is a straight-moved field" rule (mapping doc SS2/SS3.2).
# ---------------------------------------------------------------------------


def test_twin_with_null_source_count_projects_to_the_guaranteed_two() -> None:
    assert project_rudder_count("twin", None) == 2


def test_twin_with_already_two_source_count_stays_two() -> None:
    assert project_rudder_count("twin", 2) == 2


@pytest.mark.parametrize("contradictory_count", [0, 1, 3, 4])
def test_twin_with_contradictory_source_count_is_not_silently_resolved(
    contradictory_count: int,
) -> None:
    # Neither silently overwritten to 2 nor silently kept as the contradictory
    # value while dropping the twin fact -- must raise, not return anything.
    with pytest.raises(RudderCountMappingConflict):
        project_rudder_count("twin", contradictory_count)


def test_twin_still_does_not_invent_position_support_or_balance() -> None:
    # The rudder_count correction (amendment 2) must not reopen amendment 1's
    # conservatism for the other three decomposed rudder fields.
    row = RUDDER_TYPE_MAPPING["twin"]
    assert row == {
        "rudder_position": "unknown",
        "rudder_support": "unknown",
        "rudder_balance": "unknown",
    }


@pytest.mark.parametrize("rudder_type", sorted(t for t in RUDDER_TYPE_MAPPING if t != "twin"))
@pytest.mark.parametrize("source_count", [None, 0, 1, 2, 3])
def test_non_twin_rudder_types_never_synthesize_rudder_count(
    rudder_type: str, source_count: int | None
) -> None:
    assert project_rudder_count(rudder_type, source_count) == source_count


# ---------------------------------------------------------------------------
# The mapping's output must itself be schema-valid v0.6, for every source token.
# ---------------------------------------------------------------------------


def _load_base_instance() -> dict[str, Any]:
    fixture = json.loads(
        (FIXTURES_DIR / "01_classic_aft_cockpit_masthead_sloop.json").read_text(encoding="utf-8")
    )
    fixture.pop("fixture_purpose")
    return fixture


def test_every_mapped_rig_type_row_produces_a_schema_valid_instance() -> None:
    base = _load_base_instance()
    for row in RIG_TYPE_MAPPING.values():
        instance = copy.deepcopy(base)
        instance["baseline"]["rig"]["sailplan"] = row["sailplan"]
        instance["baseline"]["rig"]["masthead_fractional"] = row["masthead_fractional"]
        _V06.validate(instance)


def test_every_mapped_rudder_type_row_produces_a_schema_valid_instance() -> None:
    # Uses source_rudder_count=None (the representative "never recorded" case)
    # so the twin row exercises its actual guaranteed projection (-> 2) rather
    # than an arbitrary leftover fixture value.
    base = _load_base_instance()
    for rudder_type, row in RUDDER_TYPE_MAPPING.items():
        instance = copy.deepcopy(base)
        instance["baseline"]["appendages"]["rudder_position"] = row["rudder_position"]
        instance["baseline"]["appendages"]["rudder_support"] = row["rudder_support"]
        instance["baseline"]["appendages"]["rudder_balance"] = row["rudder_balance"]
        instance["baseline"]["appendages"]["rudder_count"] = project_rudder_count(rudder_type, None)
        # skeg_type is independent of this mapping and is left as the base
        # fixture's own concrete value ("full"), which is compatible with
        # every mapped rudder_support value exercised here.
        _V06.validate(instance)


def test_twin_with_null_source_count_produces_a_schema_valid_count_two_instance() -> None:
    base = _load_base_instance()
    instance = copy.deepcopy(base)
    instance["baseline"]["appendages"].update(
        rudder_position="unknown",
        rudder_support="unknown",
        rudder_balance="unknown",
        rudder_count=project_rudder_count("twin", None),
    )
    assert instance["baseline"]["appendages"]["rudder_count"] == 2
    _V06.validate(instance)


def test_twin_with_agreeing_source_count_two_produces_a_schema_valid_instance() -> None:
    base = _load_base_instance()
    instance = copy.deepcopy(base)
    instance["baseline"]["appendages"].update(
        rudder_position="unknown",
        rudder_support="unknown",
        rudder_balance="unknown",
        rudder_count=project_rudder_count("twin", 2),
    )
    _V06.validate(instance)


def test_twin_with_contradictory_source_count_never_reaches_schema_validation() -> None:
    # The conflict must be caught by the mapping function itself, before any
    # v0.6 instance is even constructed -- there is no "clean" instance to
    # validate for a rudder_type=twin/rudder_count=1 source payload.
    with pytest.raises(RudderCountMappingConflict):
        project_rudder_count("twin", 1)
