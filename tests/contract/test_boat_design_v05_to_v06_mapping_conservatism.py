"""Mechanical conservativity check for the v0.5 -> v0.6 rig/rudder mapping.

`docs/engineering/BOAT_DESIGN_V05_TO_V06_MAPPING.md` §3 documents, in prose
tables, how the v0.5 combined `rig_type` and `rudder_type` tokens translate into
the v0.6 decomposed fields. Independent review found the original tables
over-inferred: they asserted decomposed facts (e.g. `ketch -> masthead_fractional:
not_applicable`, `spade -> rudder_balance: balanced`) that the v0.5 token never
actually encoded.

This module transcribes the corrected tables as literal Python data and then
enforces the *governing rule itself* -- not just "does the code match the
table" (which would let a bug in both drift together undetected) -- so a future
edit cannot silently reintroduce an invented fact without an explicit, reviewed
change to the enforcement rule below, not merely to the table.

None of this is wired into the persistence importer/readback path; it is a
standalone compatibility check, not a production migration.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

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
# Deliberately has no "rudder_count" key anywhere: rudder_count is a
# straight-moved field (§2), never synthesized from rudder_type.
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


def test_mapping_tables_never_synthesize_rudder_count() -> None:
    # rudder_count is a straight-moved field (mapping doc SS2), independent of
    # rudder_type; the twin -> rudder_count=2 shortcut from the pre-review draft
    # would lose a real v0.5 payload's actual (possibly null) recorded count.
    for row in RUDDER_TYPE_MAPPING.values():
        assert "rudder_count" not in row


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
    base = _load_base_instance()
    for row in RUDDER_TYPE_MAPPING.values():
        instance = copy.deepcopy(base)
        instance["baseline"]["appendages"]["rudder_position"] = row["rudder_position"]
        instance["baseline"]["appendages"]["rudder_support"] = row["rudder_support"]
        instance["baseline"]["appendages"]["rudder_balance"] = row["rudder_balance"]
        # rudder_count / skeg_type are independent of this mapping and are left
        # as the base fixture's own concrete values (rudder_count=1, skeg_type
        # full), which is compatible with every mapped support value here.
        _V06.validate(instance)
