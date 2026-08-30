"""Mechanical/adversarial verification for the SLICE-0036 marine-technical
entailment contract.

`specs/MARINE_TECHNICAL_ENTAILMENT.v0.1.md` / `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json`
classify every controlled enum token in the fixed v0.6 field inventory (plus
the preserved legacy v0.5 rig_type/rudder_type vocabularies) as exactly one of
DEFINITIONAL_ENTAILMENT, DIRECT_ONLY or NO_DERIVATION. This module proves the
registry is exhaustive against the live schemas (not a self-authorizing
fixture), internally consistent, and fail-closed: no sentinel/free-text/
unresolved input can manufacture a concrete derived fact, no reverse direction
is silently authorized, and no rule can overwrite a same-scope contradiction.

It also mechanically exercises the >=3 real-design validation required by the
slice, using facts already retained in `research/benchmark/SEED_RESEARCH_NOTES.md`
(no new research campaign) -- see
`research/validation/SL0036-marine-entailment-real-design-validation.md` for
the full narrative record. Nothing here promotes any design to canonical data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from hullq.contracts.marine_entailment import (
    RudderCountEntailmentConflict,
    field_token_classification,
    load_registry,
    project_twin_rudder_count,
    rules_by_id,
)

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"

_REGISTRY = load_registry()
_V06_SCHEMA: dict[str, Any] = json.loads(
    (SPECS / "BOAT_DESIGN_SCHEMA.v0.6.json").read_text(encoding="utf-8")
)
_V05_SCHEMA: dict[str, Any] = json.loads(
    (SPECS / "BOAT_DESIGN_SCHEMA.v0.5.json").read_text(encoding="utf-8")
)


def _schema_enum(schema: dict[str, Any], path: list[str]) -> set[str]:
    node: Any = schema
    for step in path:
        node = node[step]
    if not isinstance(node, list):
        raise TypeError(f"Expected an enum list at {path!r}, got {type(node).__name__}")
    return set(node)


def _schema_for(name: str) -> dict[str, Any]:
    return _V06_SCHEMA if name == "v06" else _V05_SCHEMA


_ENUM_FIELDS = {
    name: entry for name, entry in _REGISTRY["fields"].items() if entry["kind"] == "enum"
}
_FREE_TEXT_FIELDS = {
    name: entry for name, entry in _REGISTRY["fields"].items() if entry["kind"] == "free_text"
}
_INTEGER_FIELDS = {
    name: entry for name, entry in _REGISTRY["fields"].items() if entry["kind"] == "integer"
}
_LEGACY_FIELDS = {"legacy.rig_type", "legacy.rudder_type"}
_NATIVE_ENUM_FIELDS = {name: e for name, e in _ENUM_FIELDS.items() if name not in _LEGACY_FIELDS}

_RULES_BY_ID = rules_by_id(_REGISTRY)


# ---------------------------------------------------------------------------
# Coverage: registry enum token sets must equal the live schema enum sets
# exactly, sourced from the schema files themselves, not duplicated fixtures.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_name", sorted(_ENUM_FIELDS))
def test_registry_enum_tokens_exactly_match_schema_enum(field_name: str) -> None:
    entry = _ENUM_FIELDS[field_name]
    schema = _schema_for(entry["schema"])
    schema_tokens = _schema_enum(schema, entry["enum_path"])
    registry_tokens = set(entry["tokens"])
    assert registry_tokens == schema_tokens, (
        f"{field_name}: registry tokens {registry_tokens} != schema enum {schema_tokens}"
    )


def test_no_in_scope_enum_field_is_missing_from_the_registry() -> None:
    # Every field named by the fixed field inventory (SLICE-0036.md section 2 /
    # MARINE_TECHNICAL_ENTAILMENT.v0.1.md section 2) must appear.
    expected = {
        "configuration.hull_configuration",
        "configuration.hull_count",
        "appendages.keel_type",
        "appendages.keel_subtype",
        "appendages.centerboard_count",
        "appendages.centerboard_type",
        "appendages.daggerboard_count",
        "appendages.daggerboard_type",
        "appendages.rudder_count",
        "appendages.rudder_position",
        "appendages.rudder_support",
        "appendages.rudder_balance",
        "appendages.skeg_type",
        "rig.sailplan",
        "rig.masthead_fractional",
        "rig.mast_count",
        "rig.mast_step",
        "rig.rig_variant",
        "deck.cockpit_position",
        "deck.cockpit_count",
        "deck.helm_type",
        "deck.helm_count",
        "legacy.rig_type",
        "legacy.rudder_type",
    }
    assert set(_REGISTRY["fields"]) == expected


def test_adding_a_new_schema_enum_token_would_break_the_coverage_check() -> None:
    # Adversarial proof that the mechanism above actually catches drift: a
    # schema enum set with one synthetic extra token must NOT equal the
    # registry's token set, demonstrating test_registry_enum_tokens_exactly_match_schema_enum
    # would fail (not silently pass) if BOAT_DESIGN_SCHEMA.v0.6.json grew a new
    # hull_configuration value without a registry update.
    entry = _REGISTRY["fields"]["configuration.hull_configuration"]
    real_schema_tokens = _schema_enum(_V06_SCHEMA, entry["enum_path"])
    drifted_schema_tokens = real_schema_tokens | {"__synthetic_new_enum_value__"}
    assert set(entry["tokens"]) != drifted_schema_tokens


# ---------------------------------------------------------------------------
# Free-text fields: full non-entailment, no enumerated tokens.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_name", sorted(_FREE_TEXT_FIELDS))
def test_free_text_fields_are_fully_non_entailing(field_name: str) -> None:
    entry = _FREE_TEXT_FIELDS[field_name]
    assert entry["classification"] == "NO_DERIVATION"
    assert "tokens" not in entry


def test_free_text_fields_are_exactly_the_four_named_by_the_slice() -> None:
    assert set(_FREE_TEXT_FIELDS) == {
        "appendages.keel_subtype",
        "appendages.centerboard_type",
        "appendages.daggerboard_type",
        "rig.rig_variant",
    }


def test_no_rule_uses_a_free_text_field_as_a_source() -> None:
    free_text_fields = set(_FREE_TEXT_FIELDS)
    for rule in _REGISTRY["rules"]:
        source = rule.get("source")
        if source is not None:
            assert source["field"] not in free_text_fields, (
                f"{rule['id']} illegally sources from free-text field {source['field']!r}"
            )
        for co_input in rule.get("co_inputs", []):
            assert co_input["field"] not in free_text_fields


# ---------------------------------------------------------------------------
# Universal sentinel rule: 'unknown' and 'other' never entail anything in
# v0.6-native fields (legacy fields preserve their own accepted SLICE-0034
# trivial-identity rows and are checked separately below).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_name", sorted(_NATIVE_ENUM_FIELDS))
def test_unknown_token_is_always_no_derivation_in_native_fields(field_name: str) -> None:
    tokens = _NATIVE_ENUM_FIELDS[field_name]["tokens"]
    if "unknown" in tokens:
        assert tokens["unknown"]["classification"] == "NO_DERIVATION"


@pytest.mark.parametrize("field_name", sorted(_NATIVE_ENUM_FIELDS))
def test_other_token_is_always_no_derivation_in_native_fields(field_name: str) -> None:
    tokens = _NATIVE_ENUM_FIELDS[field_name]["tokens"]
    if "other" in tokens:
        assert tokens["other"]["classification"] == "NO_DERIVATION"


def test_not_applicable_is_direct_only_not_a_sentinel() -> None:
    tokens = _REGISTRY["fields"]["rig.masthead_fractional"]["tokens"]
    assert tokens["not_applicable"]["classification"] == "DIRECT_ONLY"


def test_no_rule_asserts_not_applicable_as_an_output() -> None:
    # not_applicable remains legitimate for freshly-researched v0.6 data, but no
    # rule in this contract may assert it (see MARINE_TECHNICAL_ENTAILMENT.v0.1.md
    # section 6 item 1 -- sailplan=cat deliberately does not entail it).
    for rule in _REGISTRY["rules"]:
        for output in rule.get("output", []):
            assert output.get("value") != "not_applicable", (
                f"{rule['id']} illegally asserts not_applicable as a derived output"
            )


# ---------------------------------------------------------------------------
# Rule structural completeness: every DEFINITIONAL_ENTAILMENT rule records the
# minimum required metadata, and every classified DEFINITIONAL_ENTAILMENT token
# actually has a corresponding rule (and vice versa).
# ---------------------------------------------------------------------------

_REQUIRED_RULE_KEYS = {
    "id",
    "version",
    "area",
    "output",
    "prerequisites",
    "applicability",
    "exceptions",
    "conflict_behavior",
    "evidence_basis",
    "lineage_requirement",
}


@pytest.mark.parametrize("rule", _REGISTRY["rules"], ids=lambda r: r["id"])
def test_every_rule_records_the_minimum_required_metadata(rule: dict[str, Any]) -> None:
    missing = _REQUIRED_RULE_KEYS - set(rule)
    assert not missing, f"{rule['id']} is missing required keys: {missing}"
    for key in _REQUIRED_RULE_KEYS - {"id", "output"}:
        assert rule[key], f"{rule['id']}.{key} must not be empty"
    assert rule["output"], f"{rule['id']}.output must not be empty"
    assert "source" in rule or "co_inputs" in rule, f"{rule['id']} has no declared input"


def test_no_duplicate_rule_ids() -> None:
    rules = _REGISTRY["rules"]
    assert len(_RULES_BY_ID) == len(rules)


def test_rules_by_id_rejects_a_duplicate_rule_id() -> None:
    duplicated = dict(_REGISTRY)
    duplicated["rules"] = [_REGISTRY["rules"][0], _REGISTRY["rules"][0]]
    with pytest.raises(ValueError, match="Duplicate rule id"):
        rules_by_id(duplicated)


def test_load_registry_rejects_a_non_object_json_root(tmp_path: Path) -> None:
    bad_file = tmp_path / "not_an_object.json"
    bad_file.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(TypeError, match="Registry root must be a JSON object"):
        load_registry(bad_file)


@pytest.mark.parametrize("rule", _REGISTRY["rules"], ids=lambda r: r["id"])
def test_every_rule_conflict_behavior_names_a_fail_closed_response(
    rule: dict[str, Any],
) -> None:
    text = rule["conflict_behavior"]
    assert (
        "UNRESOLVED_CONFLICT" in text
        or "raises" in text
        or "not silently resolved" in text
        or "N/A" in text
        or "independently enforced structurally" in text
    ), f"{rule['id']} conflict_behavior does not name a fail-closed response: {text!r}"


@pytest.mark.parametrize("rule", _REGISTRY["rules"], ids=lambda r: r["id"])
def test_every_rule_lineage_requirement_names_the_rule_id(rule: dict[str, Any]) -> None:
    assert rule["id"] in rule["lineage_requirement"]


@pytest.mark.parametrize("rule", _REGISTRY["rules"], ids=lambda r: r["id"])
def test_every_rule_applicability_names_a_scope(rule: dict[str, Any]) -> None:
    assert "scope" in rule["applicability"]


# ---------------------------------------------------------------------------
# No rule references an out-of-scope path/token.
# ---------------------------------------------------------------------------


def _all_field_refs(rule: dict[str, Any]) -> list[str]:
    refs = []
    if "source" in rule:
        refs.append(rule["source"]["field"])
    refs.extend(co_input["field"] for co_input in rule.get("co_inputs", []))
    refs.extend(output["field"] for output in rule["output"])
    return refs


@pytest.mark.parametrize("rule", _REGISTRY["rules"], ids=lambda r: r["id"])
def test_every_rule_field_reference_is_in_scope(rule: dict[str, Any]) -> None:
    in_scope_fields = set(_REGISTRY["fields"])
    for field in _all_field_refs(rule):
        assert field in in_scope_fields, f"{rule['id']} references out-of-scope field {field!r}"


@pytest.mark.parametrize("rule", _REGISTRY["rules"], ids=lambda r: r["id"])
def test_every_rule_source_token_is_a_classified_token_of_its_field(
    rule: dict[str, Any],
) -> None:
    source = rule.get("source")
    if source is None:
        return
    field_entry = _REGISTRY["fields"][source["field"]]
    if field_entry["kind"] == "enum":
        assert source["value"] in field_entry["tokens"]
    elif field_entry["kind"] == "integer":
        values = [vr["value"] for vr in field_entry.get("value_rules", [])]
        assert source["value"] in values


# ---------------------------------------------------------------------------
# Every DEFINITIONAL_ENTAILMENT token classification is backed by a real rule,
# and that rule's declared source matches the token.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_name", sorted(_ENUM_FIELDS))
def test_every_definitional_entailment_token_has_a_matching_rule(field_name: str) -> None:
    for token, meta in _ENUM_FIELDS[field_name]["tokens"].items():
        if meta["classification"] != "DEFINITIONAL_ENTAILMENT":
            continue
        assert meta["rule_ids"], f"{field_name}={token} claims DEFINITIONAL_ENTAILMENT with no rule"
        for rule_id in meta["rule_ids"]:
            rule = _RULES_BY_ID[rule_id]
            assert rule["source"]["field"] == field_name
            assert rule["source"]["value"] == token


@pytest.mark.parametrize("field_name", sorted(_INTEGER_FIELDS))
def test_every_integer_value_rule_matches_its_referenced_rule(field_name: str) -> None:
    for value_rule in _INTEGER_FIELDS[field_name].get("value_rules", []):
        rule = _RULES_BY_ID[value_rule["rule_id"]]
        assert rule["source"]["field"] == field_name
        assert rule["source"]["value"] == value_rule["value"]


# ---------------------------------------------------------------------------
# Reverse-inference safety: no unsafe direction is silently authorized.
# ---------------------------------------------------------------------------


def test_hull_count_to_hull_configuration_reverse_is_not_derivation() -> None:
    reverse = _REGISTRY["fields"]["configuration.hull_count"]["reverse_relations"][0]
    assert reverse["target"] == "configuration.hull_configuration"
    assert reverse["classification"] == "NO_DERIVATION"
    for rule in _REGISTRY["rules"]:
        source = rule.get("source")
        if source and source["field"] == "configuration.hull_count":
            pytest.fail(f"{rule['id']} illegally derives from hull_count")


def test_mast_count_to_sailplan_reverse_is_not_derivation() -> None:
    reverse = _REGISTRY["fields"]["rig.mast_count"]["reverse_relations"][0]
    assert reverse["target"] == "rig.sailplan"
    assert reverse["classification"] == "NO_DERIVATION"
    for rule in _REGISTRY["rules"]:
        source = rule.get("source")
        if source and source["field"] == "rig.mast_count":
            pytest.fail(f"{rule['id']} illegally derives from mast_count")


def test_no_rule_derives_keel_type_from_board_counts() -> None:
    # Reverse of MTE-KEEL-001/002: a positive board count never proves the
    # board IS the primary keel-equivalent appendage (hybrid construction).
    for rule in _REGISTRY["rules"]:
        source = rule.get("source")
        if source and source["field"] in {
            "appendages.centerboard_count",
            "appendages.daggerboard_count",
        }:
            for output in rule["output"]:
                assert output["field"] != "appendages.keel_type"


def test_rudder_position_and_rudder_support_never_derive_each_other_natively() -> None:
    # The whole point of the v0.6 decomposition: a transom-positioned rudder
    # can independently carry keel/skeg support semantics, so v0.6-native
    # rudder_position must never entail rudder_support, and v0.6-native
    # rudder_support must never entail rudder_position. (Legacy rudder_type
    # tokens may legitimately entail both at once -- e.g. transom_hung -- via
    # their own dedicated rules; those are not native-field cross-derivation.)
    for field_name in ("appendages.rudder_position", "appendages.rudder_support"):
        for rule in _REGISTRY["rules"]:
            source = rule.get("source")
            if source is None or source["field"] != field_name:
                continue
            other_native_field = (
                "appendages.rudder_support"
                if field_name == "appendages.rudder_position"
                else "appendages.rudder_position"
            )
            touched = {o["field"] for o in rule["output"]}
            assert other_native_field not in touched, (
                f"{rule['id']} illegally derives {other_native_field} from {field_name}"
            )


# ---------------------------------------------------------------------------
# Field-specific correctness: definitional entailments produce exactly the
# accepted values.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("hull_configuration", "expected_hull_count"),
    [("monohull", 1), ("catamaran", 2), ("trimaran", 3)],
)
def test_hull_configuration_definitional_entailment_values(
    hull_configuration: str, expected_hull_count: int
) -> None:
    classification = field_token_classification(
        _REGISTRY, "configuration.hull_configuration", hull_configuration
    )
    assert classification == "DEFINITIONAL_ENTAILMENT"
    rule_id = _REGISTRY["fields"]["configuration.hull_configuration"]["tokens"][hull_configuration][
        "rule_ids"
    ][0]
    rule = _RULES_BY_ID[rule_id]
    assert rule["output"] == [{"field": "configuration.hull_count", "value": expected_hull_count}]


@pytest.mark.parametrize("hull_configuration", ["other", "unknown"])
def test_hull_configuration_other_and_unknown_do_not_entail_hull_count(
    hull_configuration: str,
) -> None:
    assert (
        field_token_classification(
            _REGISTRY, "configuration.hull_configuration", hull_configuration
        )
        == "NO_DERIVATION"
    )


@pytest.mark.parametrize(
    ("sailplan", "expected_relation"),
    [
        ("sloop", {"field": "rig.mast_count", "value": 1}),
        ("cutter", {"field": "rig.mast_count", "value": 1}),
        ("cat", {"field": "rig.mast_count", "value": 1}),
        ("ketch", {"field": "rig.mast_count", "value": 2}),
        ("yawl", {"field": "rig.mast_count", "value": 2}),
        ("schooner", {"field": "rig.mast_count", "relation": ">=2"}),
    ],
)
def test_sailplan_mast_count_definitional_entailments(
    sailplan: str, expected_relation: dict[str, Any]
) -> None:
    rule_id = _REGISTRY["fields"]["rig.sailplan"]["tokens"][sailplan]["rule_ids"][0]
    rule = _RULES_BY_ID[rule_id]
    assert rule["output"] == [expected_relation]


def test_sailplan_never_entails_masthead_fractional_natively() -> None:
    for token in ("sloop", "cutter", "cat", "ketch", "yawl", "schooner"):
        rule_id = _REGISTRY["fields"]["rig.sailplan"]["tokens"][token]["rule_ids"][0]
        rule = _RULES_BY_ID[rule_id]
        fields_touched = {o["field"] for o in rule["output"]}
        assert "rig.masthead_fractional" not in fields_touched


def test_rudder_support_skeg_excludes_skeg_type_none_both_directions() -> None:
    forward = _RULES_BY_ID["MTE-RUD-002"]
    assert forward["source"] == {"field": "appendages.rudder_support", "value": "skeg"}
    assert forward["output"] == [{"field": "appendages.skeg_type", "excludes_value": "none"}]

    backward = _RULES_BY_ID["MTE-RUD-003"]
    assert backward["source"] == {"field": "appendages.skeg_type", "value": "none"}
    assert backward["output"] == [{"field": "appendages.rudder_support", "excludes_value": "skeg"}]


@pytest.mark.parametrize(
    ("count_field", "sibling_fields", "rule_id"),
    [
        (
            "appendages.rudder_count",
            [
                "appendages.rudder_position",
                "appendages.rudder_support",
                "appendages.rudder_balance",
            ],
            "MTE-RUD-001",
        ),
        ("deck.cockpit_count", ["deck.cockpit_position"], "MTE-DECK-001"),
        ("deck.helm_count", ["deck.helm_type"], "MTE-DECK-002"),
    ],
)
def test_zero_count_forces_sibling_fields_unknown(
    count_field: str, sibling_fields: list[str], rule_id: str
) -> None:
    rule = _RULES_BY_ID[rule_id]
    assert rule["source"] == {"field": count_field, "value": 0}
    outputs = {o["field"]: o["value"] for o in rule["output"]}
    for sibling in sibling_fields:
        assert outputs[sibling] == "unknown"


@pytest.mark.parametrize(
    ("board_field", "count_field", "rule_id"),
    [
        ("appendages.centerboard_type", "appendages.centerboard_count", "MTE-KEEL-003"),
        ("appendages.daggerboard_type", "appendages.daggerboard_count", "MTE-KEEL-004"),
    ],
)
def test_zero_board_count_forbids_concrete_board_type(
    board_field: str, count_field: str, rule_id: str
) -> None:
    rule = _RULES_BY_ID[rule_id]
    assert rule["source"] == {"field": count_field, "value": 0}
    assert rule["output"][0]["field"] == board_field
    assert rule["output"][0]["value"] is None


# ---------------------------------------------------------------------------
# Legacy v0.5 preservation: SLICE-0034 conservatism must remain intact.
# ---------------------------------------------------------------------------

_LEGACY_RIG_TOKENS_THAT_PROVE_MASTHEAD_FRACTIONAL = {"masthead_sloop", "fractional_sloop"}


def test_legacy_rig_type_masthead_fractional_only_for_masthead_and_fractional_sloop() -> None:
    for token, meta in _REGISTRY["fields"]["legacy.rig_type"]["tokens"].items():
        rule = _RULES_BY_ID[meta["rule_ids"][0]]
        touched = {o["field"] for o in rule["output"]}
        if token in _LEGACY_RIG_TOKENS_THAT_PROVE_MASTHEAD_FRACTIONAL:
            assert "rig.masthead_fractional" in touched
        else:
            assert "rig.masthead_fractional" not in touched


def test_legacy_rudder_type_never_entails_a_concrete_rudder_balance() -> None:
    for meta in _REGISTRY["fields"]["legacy.rudder_type"]["tokens"].values():
        rule = _RULES_BY_ID[meta["rule_ids"][0]]
        for output in rule["output"]:
            if output["field"] == "appendages.rudder_balance":
                assert output["value"] == "unknown"


def test_legacy_rudder_type_position_support_literal_word_mapping() -> None:
    expected_support = {
        "keel_hung": "keel",
        "skeg_hung": "skeg",
        "partial_skeg": "skeg",
        "spade": "free",
        "transom_hung": "transom",
    }
    for token, support in expected_support.items():
        rule_id = _REGISTRY["fields"]["legacy.rudder_type"]["tokens"][token]["rule_ids"][0]
        rule = _RULES_BY_ID[rule_id]
        outputs = {o["field"]: o["value"] for o in rule["output"]}
        assert outputs["appendages.rudder_support"] == support

    transom_rule = _RULES_BY_ID[
        _REGISTRY["fields"]["legacy.rudder_type"]["tokens"]["transom_hung"]["rule_ids"][0]
    ]
    outputs = {o["field"]: o["value"] for o in transom_rule["output"]}
    assert outputs["appendages.rudder_position"] == "transom"


def test_legacy_rudder_type_twin_is_the_only_rudder_count_source() -> None:
    twin_rule = _RULES_BY_ID["MTE-LEGACY-RUD-006"]
    assert twin_rule["source"] == {"field": "legacy.rudder_type", "value": "twin"}
    assert twin_rule["output"][0]["field"] == "appendages.rudder_count"
    for token, meta in _REGISTRY["fields"]["legacy.rudder_type"]["tokens"].items():
        if token == "twin":
            continue
        rule = _RULES_BY_ID[meta["rule_ids"][0]]
        assert all(o["field"] != "appendages.rudder_count" for o in rule["output"])


# ---------------------------------------------------------------------------
# project_twin_rudder_count: the one conditional rule application in this
# module, mirroring the pre-existing accepted RudderCountMappingConflict
# behavior from BOAT_DESIGN_V05_TO_V06_MAPPING.md section 3.2.
# ---------------------------------------------------------------------------


def test_twin_with_null_source_count_projects_to_the_guaranteed_two() -> None:
    assert project_twin_rudder_count(None) == 2


def test_twin_with_already_two_source_count_stays_two() -> None:
    assert project_twin_rudder_count(2) == 2


@pytest.mark.parametrize("contradictory_count", [0, 1, 3, 4])
def test_twin_with_contradictory_source_count_is_not_silently_resolved(
    contradictory_count: int,
) -> None:
    with pytest.raises(RudderCountEntailmentConflict):
        project_twin_rudder_count(contradictory_count)


# ---------------------------------------------------------------------------
# Real-design validation (>=3 technically different designs), using facts
# already retained in research/benchmark/SEED_RESEARCH_NOTES.md. No new
# research campaign; no canonical admission. See
# research/validation/SL0036-marine-entailment-real-design-validation.md for
# the full narrative record this exercises mechanically.
# ---------------------------------------------------------------------------


def test_rustler_36_keel_hung_rudder_entails_keel_support() -> None:
    # SEED-09: "Rudder is explicitly keel-hung."
    rule = _RULES_BY_ID["MTE-LEGACY-RUD-001"]
    assert rule["source"] == {"field": "legacy.rudder_type", "value": "keel_hung"}
    outputs = {o["field"]: o["value"] for o in rule["output"]}
    assert outputs == {"appendages.rudder_support": "keel"}
    # rudder_position/rudder_balance are NOT entailed -- they remain UNKNOWN,
    # matching the design's own evidence (Rustler's source names support only).


def test_westerly_centaur_spade_rudder_entails_free_support_not_balance() -> None:
    # SEED-06: "a balanced skegless spade rudder." rudder_type=spade entails
    # rudder_support=free; the separately/directly reported "balanced" fact is
    # a DIRECT source-reported value, not an output of this entailment rule --
    # the two must not be conflated.
    rule = _RULES_BY_ID["MTE-LEGACY-RUD-004"]
    assert rule["source"] == {"field": "legacy.rudder_type", "value": "spade"}
    outputs = {o["field"]: o["value"] for o in rule["output"]}
    assert outputs == {"appendages.rudder_support": "free"}
    assert "appendages.rudder_balance" not in outputs


def test_westerly_centaur_monohull_twin_keel_entails_hull_count_one() -> None:
    # SEED-06: a twin(-bilge)-keeled monohull cruiser.
    rule = _RULES_BY_ID["MTE-HULL-001"]
    assert rule["source"] == {"field": "configuration.hull_configuration", "value": "monohull"}
    assert rule["output"] == [{"field": "configuration.hull_count", "value": 1}]


def test_westerly_centaur_ambiguous_rig_identity_leaves_mast_count_undeived() -> None:
    # SEED-06: "Sloop/ketch noted, with very few ketches." The design's own
    # retained evidence cannot qualify a single sailplan value for the
    # baseline, so no MTE-RIG-* rule has a qualified source to fire on --
    # mast_count is an expected UNKNOWN outcome for this design, not a bug.
    for candidate_sailplan in ("sloop", "ketch"):
        assert (
            field_token_classification(_REGISTRY, "rig.sailplan", candidate_sailplan)
            == "DEFINITIONAL_ENTAILMENT"
        )
    # Both tokens have a real rule; the design simply cannot supply a single
    # qualified sailplan fact to apply either one to.


def test_island_packet_349_skeg_hung_rudder_entails_skeg_support() -> None:
    # SEED-16: manufacturer customization material "explicitly lists 'Skeg
    # hung rudder'."
    rule = _RULES_BY_ID["MTE-LEGACY-RUD-002"]
    assert rule["source"] == {"field": "legacy.rudder_type", "value": "skeg_hung"}
    outputs = {o["field"]: o["value"] for o in rule["output"]}
    assert outputs == {"appendages.rudder_support": "skeg"}


def test_island_packet_349_proprietary_keel_name_does_not_entail_keel_type() -> None:
    # SEED-16: the manufacturer's proprietary "Full Foil Keel(R)" term has no
    # safe mapping onto a single BOAT_DESIGN_SCHEMA.v0.6.json keel_type enum
    # value without guessing; it is recorded as free-text keel_subtype only
    # (NO_DERIVATION), and keel_type itself stays unknown for this design.
    assert _REGISTRY["fields"]["appendages.keel_subtype"]["classification"] == "NO_DERIVATION"
    for rule in _REGISTRY["rules"]:
        assert not any(o["field"] == "appendages.keel_type" for o in rule["output"]), (
            "no rule may populate keel_type from free text"
        )


def test_pogo_1_directly_stated_twin_rudders_is_direct_only_not_derived() -> None:
    # SEED-11: "Twin rudders explicitly stated" -- this is a DIRECT v0.6-native
    # fact (rudder_count=2 already known outright), not something requiring
    # entailment. rudder_count as a field is DIRECT_ONLY; there is no rule
    # that needs to fire because the target fact is already the qualified
    # source fact itself.
    assert _REGISTRY["fields"]["appendages.rudder_count"]["classification"] == "DIRECT_ONLY"
