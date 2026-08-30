"""Contract tests for BOAT_DESIGN_SCHEMA.v0.6 (SLICE-0034).

Validates the four required synthetic structural archetypes and proves the schema
fails closed on unknown properties, malformed enums, out-of-range counts,
incomplete override family sets, and bounded cross-field contradictions
(hull_configuration/hull_count, skeg_type=none vs a skeg-supported rudder,
a zero appendage count vs a concrete descriptor of that appendage). Also proves
rudder position and rudder support are independently representable (a
transom-positioned rudder may carry skeg-support semantics without contradiction)
and that newly added search-significant families are override-capable through
both NamedVariant and DesignOption mechanisms.

None of these fixtures represent real-world boat facts.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import ValidationError

from hullq.contracts import ContractRegistry

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
FIXTURES_DIR = ROOT / "fixtures" / "technical_profile" / "valid"

_REGISTRY = ContractRegistry.from_directory(SPECS)
_V06 = _REGISTRY.validator_by_name("BOAT_DESIGN_SCHEMA.v0.6.json")

ARCHETYPE_FILES = sorted(FIXTURES_DIR.glob("*.json"))


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def load_archetype(name_fragment: str) -> dict[str, Any]:
    matches = [p for p in ARCHETYPE_FILES if name_fragment in p.name]
    assert len(matches) == 1, f"expected exactly one archetype matching {name_fragment!r}"
    return load(matches[0])


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_v06_is_registered() -> None:
    assert "BOAT_DESIGN_SCHEMA.v0.6.json" in _REGISTRY.schema_names


def test_v05_still_registered_and_unmodified_id() -> None:
    # v0.6 must supersede v0.5 for new payloads without rewriting the v0.5 contract.
    assert "BOAT_DESIGN_SCHEMA.v0.5.json" in _REGISTRY.schema_names
    v05 = json.loads((SPECS / "BOAT_DESIGN_SCHEMA.v0.5.json").read_text(encoding="utf-8"))
    assert v05["$id"] == "https://hullq.local/schemas/boat-design/0.5"
    assert v05["properties"]["schema_version"]["const"] == "0.5"


# ---------------------------------------------------------------------------
# Required structural archetypes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ARCHETYPE_FILES, ids=lambda p: p.stem)
def test_archetype_fixtures_validate(path: Path) -> None:
    fixture = load(path)
    fixture.pop("fixture_purpose")
    _V06.validate(fixture)


def test_four_required_archetypes_present() -> None:
    assert len(ARCHETYPE_FILES) == 4


def test_classic_aft_cockpit_masthead_sloop_archetype() -> None:
    fixture = load_archetype("classic_aft_cockpit")
    appendages = fixture["baseline"]["appendages"]
    assert appendages["keel_type"] == "full"
    assert fixture["baseline"]["rig"]["sailplan"] == "sloop"
    assert fixture["baseline"]["rig"]["masthead_fractional"] == "masthead"
    assert fixture["baseline"]["deck"]["cockpit_position"] == "aft"


def test_center_cockpit_archetype() -> None:
    fixture = load_archetype("center_cockpit")
    assert fixture["baseline"]["deck"]["cockpit_position"] == "center"


def test_modern_production_options_archetype() -> None:
    fixture = load_archetype("modern_production_cruiser")
    axes = {opt["axis"] for opt in fixture["design_options"]}
    assert axes == {"draft", "helm"}
    draft_option = next(o for o in fixture["design_options"] if o["axis"] == "draft")
    helm_option = next(o for o in fixture["design_options"] if o["axis"] == "helm")
    assert (
        draft_option["overrides"]["dimensions"]["draft_min_m"]
        < fixture["baseline"]["dimensions"]["draft_min_m"]
    )
    assert helm_option["overrides"]["deck"]["helm_count"] == 2
    assert fixture["baseline"]["deck"]["helm_count"] == 1


def test_performance_rig_keel_variant_archetype() -> None:
    fixture = load_archetype("performance_rig_keel_variant")
    assert fixture["design_options"] == []
    variant = fixture["named_variants"][0]
    assert variant["overrides"]["appendages"]["keel_type"] == "fin"
    assert fixture["baseline"]["appendages"]["keel_type"] == "long_fin"
    assert (
        variant["overrides"]["rig"]["mast_height_m"] > fixture["baseline"]["rig"]["mast_height_m"]
    )


# ---------------------------------------------------------------------------
# Required schema semantics: rig and rudder decomposition
# ---------------------------------------------------------------------------


def test_masthead_and_fractional_sloop_are_distinguishable_without_opaque_label() -> None:
    masthead = load_archetype("classic_aft_cockpit")["baseline"]["rig"]
    fractional = load_archetype("modern_production_cruiser")["baseline"]["rig"]
    assert masthead["sailplan"] == fractional["sailplan"] == "sloop"
    assert masthead["masthead_fractional"] == "masthead"
    assert fractional["masthead_fractional"] == "fractional"


def test_transom_rudder_can_carry_keel_or_skeg_support_without_contradiction() -> None:
    fixture = load_archetype("classic_aft_cockpit")
    appendages = fixture["baseline"]["appendages"]
    assert appendages["rudder_position"] == "transom"
    assert appendages["rudder_support"] == "skeg"
    # Also prove the schema independently accepts transom + keel-support as a
    # distinct, non-contradictory combination (not just the skeg case above).
    mutated = copy.deepcopy(fixture)
    mutated.pop("fixture_purpose")
    mutated["baseline"]["appendages"]["rudder_support"] = "keel"
    _V06.validate(mutated)


def test_rudder_position_and_support_vary_independently_across_archetypes() -> None:
    positions = set()
    supports = set()
    for path in ARCHETYPE_FILES:
        appendages = load(path)["baseline"]["appendages"]
        positions.add(appendages["rudder_position"])
        supports.add(appendages["rudder_support"])
    assert len(positions) > 1
    assert len(supports) > 1


# ---------------------------------------------------------------------------
# Override symmetry (Required schema semantics E)
# ---------------------------------------------------------------------------


def test_every_baseline_family_is_override_capable_in_both_mechanisms() -> None:
    schema = json.loads((SPECS / "BOAT_DESIGN_SCHEMA.v0.6.json").read_text(encoding="utf-8"))
    baseline_families = set(schema["properties"]["baseline"]["properties"].keys())
    override_families = set(schema["$defs"]["overrides"]["properties"].keys())
    assert baseline_families == override_families
    # Both NamedVariant and DesignOption reuse the exact same overrides $def.
    named_variant_overrides_ref = schema["properties"]["named_variants"]["items"]["properties"][
        "overrides"
    ]
    design_option_overrides_ref = schema["properties"]["design_options"]["items"]["properties"][
        "overrides"
    ]
    assert named_variant_overrides_ref == {"$ref": "#/$defs/overrides"}
    assert design_option_overrides_ref == {"$ref": "#/$defs/overrides"}


def test_new_search_significant_families_are_not_baseline_only() -> None:
    fixture = load_archetype("classic_aft_cockpit")
    fixture.pop("fixture_purpose")
    for family in ("rig", "appendages", "deck", "propulsion", "accommodation", "compliance"):
        candidate = copy.deepcopy(fixture)
        candidate["named_variants"] = [
            {
                "id": f"NV_PROBE_{family}",
                "name": f"Probe {family}",
                "aliases": [],
                "applicability": {
                    "first_built": None,
                    "last_built": None,
                    "hull_number_from": None,
                    "hull_number_to": None,
                    "notes": None,
                },
                "overrides": {
                    "dimensions": {},
                    "ratio_input_basis": {},
                    "configuration": {},
                    "appendages": {},
                    "rig": {},
                    "deck": {},
                    "construction": {},
                    "propulsion": {},
                    "accommodation": {},
                    "compliance": {},
                },
                "requires_option_ids": [],
                "excludes_option_ids": [],
            }
        ]
        candidate["named_variants"][0]["overrides"][family] = _one_field_override(fixture, family)
        _V06.validate(candidate)


def _one_field_override(fixture: dict[str, Any], family: str) -> dict[str, Any]:
    baseline_family = fixture["baseline"][family]
    key = next(iter(baseline_family))
    return {key: baseline_family[key]}


# ---------------------------------------------------------------------------
# Fail-closed: unknown extra properties, malformed enums/counts, tampering
# ---------------------------------------------------------------------------


def _base_instance() -> dict[str, Any]:
    fixture = load_archetype("classic_aft_cockpit")
    fixture.pop("fixture_purpose")
    return fixture


def test_rejects_unknown_extra_property_in_baseline_family() -> None:
    instance = _base_instance()
    instance["baseline"]["appendages"]["extra_bogus_field"] = "nope"
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_rejects_unknown_extra_property_at_top_level() -> None:
    instance = _base_instance()
    instance["unexpected_top_level_field"] = True
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_rejects_malformed_sailplan_enum() -> None:
    instance = _base_instance()
    instance["baseline"]["rig"]["sailplan"] = "gaff_schooner_supreme"
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_rejects_malformed_rudder_support_enum() -> None:
    instance = _base_instance()
    instance["baseline"]["appendages"]["rudder_support"] = "trampoline"
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_rejects_negative_rudder_count() -> None:
    instance = _base_instance()
    instance["baseline"]["appendages"]["rudder_count"] = -1
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_rejects_wrong_type_dimension() -> None:
    instance = _base_instance()
    instance["baseline"]["dimensions"]["loa_m"] = "10.97"
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_rejects_zero_loa() -> None:
    instance = _base_instance()
    instance["baseline"]["dimensions"]["loa_m"] = 0
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_rejects_wrong_schema_version_const() -> None:
    instance = _base_instance()
    instance["schema_version"] = "0.5"
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_rejects_missing_required_baseline_family() -> None:
    instance = _base_instance()
    del instance["baseline"]["rig"]
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_rejects_incomplete_override_family_set() -> None:
    instance = load_archetype("performance_rig_keel_variant")
    instance.pop("fixture_purpose")
    del instance["named_variants"][0]["overrides"]["rig"]
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_rejects_extra_property_inside_a_partial_override() -> None:
    instance = load_archetype("modern_production_cruiser")
    instance.pop("fixture_purpose")
    instance["design_options"][0]["overrides"]["appendages"]["unknown_override_field"] = "x"
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_rejects_unbounded_design_option_axis() -> None:
    instance = load_archetype("modern_production_cruiser")
    instance.pop("fixture_purpose")
    instance["design_options"][0]["axis"] = "not_a_real_axis"
    with pytest.raises(ValidationError):
        _V06.validate(instance)


# ---------------------------------------------------------------------------
# Bounded cross-field fail-closed invariants (SLICE-0034 amendment).
#
# Each invariant below is a definitional/mathematical certainty (what the words
# monohull/catamaran/trimaran mean; a zero count cannot coexist with a concrete
# descriptor of the thing being counted; skeg_type=none cannot coexist with a
# skeg-supported rudder), not a domain-taxonomy guess. Every "reject" case is
# paired with an "accept" case proving the invariant only fires on the actual
# contradiction, and a partial-override case proves an invariant never forces a
# NamedVariant/DesignOption override to restate untouched sibling fields.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("hull_configuration", "hull_count"),
    [("catamaran", 1), ("trimaran", 2), ("trimaran", 1), ("monohull", 2), ("monohull", 3)],
)
def test_rejects_hull_configuration_hull_count_mismatch(
    hull_configuration: str, hull_count: int
) -> None:
    instance = _base_instance()
    instance["baseline"]["configuration"] = {
        "hull_configuration": hull_configuration,
        "hull_count": hull_count,
    }
    with pytest.raises(ValidationError):
        _V06.validate(instance)


@pytest.mark.parametrize(
    ("hull_configuration", "hull_count"),
    [("monohull", 1), ("catamaran", 2), ("trimaran", 3), ("monohull", None), ("other", 5)],
)
def test_accepts_hull_configuration_hull_count_agreement_or_unknown_count(
    hull_configuration: str, hull_count: int | None
) -> None:
    instance = _base_instance()
    instance["baseline"]["configuration"] = {
        "hull_configuration": hull_configuration,
        "hull_count": hull_count,
    }
    _V06.validate(instance)


def test_rejects_skeg_none_with_skeg_supported_rudder() -> None:
    instance = _base_instance()
    instance["baseline"]["appendages"]["skeg_type"] = "none"
    instance["baseline"]["appendages"]["rudder_support"] = "skeg"
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_accepts_skeg_none_with_non_skeg_rudder_support() -> None:
    instance = _base_instance()
    instance["baseline"]["appendages"]["skeg_type"] = "none"
    instance["baseline"]["appendages"]["rudder_support"] = "free"
    _V06.validate(instance)


def test_rejects_zero_centerboard_count_with_concrete_centerboard_type() -> None:
    instance = _base_instance()
    instance["baseline"]["appendages"]["centerboard_count"] = 0
    instance["baseline"]["appendages"]["centerboard_type"] = "swing"
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_rejects_zero_daggerboard_count_with_concrete_daggerboard_type() -> None:
    instance = _base_instance()
    instance["baseline"]["appendages"]["daggerboard_count"] = 0
    instance["baseline"]["appendages"]["daggerboard_type"] = "carbon"
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_accepts_zero_board_counts_with_null_board_types() -> None:
    instance = _base_instance()
    instance["baseline"]["appendages"]["centerboard_count"] = 0
    instance["baseline"]["appendages"]["centerboard_type"] = None
    instance["baseline"]["appendages"]["daggerboard_count"] = 0
    instance["baseline"]["appendages"]["daggerboard_type"] = None
    _V06.validate(instance)


def test_rejects_zero_rudder_count_with_concrete_rudder_position() -> None:
    # The classic-aft-cockpit base fixture already carries a concrete
    # rudder_position/support/balance; setting rudder_count=0 without clearing
    # them must be rejected.
    instance = _base_instance()
    instance["baseline"]["appendages"]["rudder_count"] = 0
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_accepts_zero_rudder_count_with_all_unknown_rudder_facts() -> None:
    instance = _base_instance()
    instance["baseline"]["appendages"].update(
        rudder_count=0,
        rudder_position="unknown",
        rudder_support="unknown",
        rudder_balance="unknown",
    )
    _V06.validate(instance)


def test_accepts_null_rudder_count_with_concrete_rudder_position() -> None:
    # An unrecorded count (null) is honest "we don't know how many"; it must not
    # be treated as a contradiction the way an explicit zero is.
    instance = _base_instance()
    instance["baseline"]["appendages"]["rudder_count"] = None
    _V06.validate(instance)


def test_rejects_zero_cockpit_count_with_concrete_cockpit_position() -> None:
    instance = _base_instance()
    instance["baseline"]["deck"]["cockpit_count"] = 0
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_accepts_zero_cockpit_count_with_unknown_cockpit_position() -> None:
    instance = _base_instance()
    instance["baseline"]["deck"]["cockpit_count"] = 0
    instance["baseline"]["deck"]["cockpit_position"] = "unknown"
    _V06.validate(instance)


def test_rejects_zero_helm_count_with_concrete_helm_type() -> None:
    instance = _base_instance()
    instance["baseline"]["deck"]["helm_count"] = 0
    with pytest.raises(ValidationError):
        _V06.validate(instance)


def test_accepts_zero_helm_count_with_unknown_helm_type() -> None:
    instance = _base_instance()
    instance["baseline"]["deck"]["helm_count"] = 0
    instance["baseline"]["deck"]["helm_type"] = "unknown"
    _V06.validate(instance)


def test_cross_field_invariants_do_not_force_partial_overrides_to_restate_siblings() -> None:
    """A NamedVariant overriding only rudder_count=0 must not be forced to also
    restate rudder_position/support/balance, since it never touched them."""
    instance = load_archetype("performance_rig_keel_variant")
    instance.pop("fixture_purpose")
    instance["named_variants"][0]["overrides"]["appendages"] = {"rudder_count": 0}
    _V06.validate(instance)


def test_draft_min_exceeds_draft_max_is_a_known_unenforceable_gap() -> None:
    """Deliberately documents a gap, not a guarantee.

    draft_min_m > draft_max_m is a genuine contradiction, but standard JSON
    Schema (Draft 2020-12, as consumed by this repo's `jsonschema` package,
    which does not implement the non-standard `$data` proposal) has no
    declarative way to compare two sibling numeric properties without a custom
    keyword/format extension. This repo's only existing cross-field pattern
    (`FIELD_RESOLUTION_SCHEMA.v0.1/v0.2`, and the invariants added above) is
    entirely `const`/`enum`-based `if`/`then`, never a numeric comparison
    between two variable properties, so there is no local precedent to extend
    either. Introducing a new validation mechanism for this one field pair
    would be disproportionate to a bounded schema-shape amendment. This test
    exists to make the gap explicit and regression-visible rather than silent:
    if a future change closes it, this test should start failing and can be
    deleted.
    """
    instance = _base_instance()
    instance["baseline"]["dimensions"]["draft_min_m"] = 5.0
    instance["baseline"]["dimensions"]["draft_max_m"] = 1.0
    _V06.validate(instance)  # not raising is the documented, known gap


# ---------------------------------------------------------------------------
# No source promotion (F): fixtures must not resemble real motivating designs
# ---------------------------------------------------------------------------

_REAL_MOTIVATING_DESIGN_NAMES = [
    "rustler 36",
    "contessa 32",
    "bavaria cruiser 34",
    "sun odyssey 36i",
    "albin vega",
    "rival 34",
]


def test_fixtures_do_not_name_real_motivating_designs() -> None:
    for path in ARCHETYPE_FILES:
        text = path.read_text(encoding="utf-8").lower()
        for real_name in _REAL_MOTIVATING_DESIGN_NAMES:
            assert real_name not in text, (
                f"{path.name} appears to reference real design {real_name!r}"
            )
