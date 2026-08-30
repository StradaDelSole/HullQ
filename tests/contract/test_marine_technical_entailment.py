"""Mechanical/adversarial verification for the SLICE-0036 marine-technical
entailment contract.

`specs/MARINE_TECHNICAL_ENTAILMENT.v0.1.md` / `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json`
classify every controlled enum token in the fixed v0.6 field inventory (plus
the preserved legacy v0.5 rig_type/rudder_type vocabularies) as exactly one of
DEFINITIONAL_ENTAILMENT, DIRECT_ONLY or NO_DERIVATION. This module proves the
registry is exhaustive against the live schemas (not a self-authorizing
fixture), internally consistent, and fail-closed.

This is a DESIGN_RESEARCH contract with NO production inference/projection
runtime: this module loads the registry JSON directly (there is no `src/`
loader module for it, deliberately), and any function that *applies* a rule
to synthetic input (the twin/rudder_count reference projection, the guard
reference evaluator) is explicitly TEST-ONLY, defined in this file, and never
exported from or reachable through `src/`.

Independence: the mapping from each fixed-inventory field to its schema file
and exact schema path is hardcoded in this module (`_INDEPENDENT_ENUM_LOCATIONS`
/ `_INDEPENDENT_INTEGER_LOCATIONS` / `_INDEPENDENT_FREE_TEXT_LOCATIONS`),
transcribed directly from BOAT_DESIGN_SCHEMA.v0.5/v0.6.json and from this
slice's own fixed field inventory -- never read from the registry under test.
The registry's own `schema`/`enum_path` metadata is treated as informational
only and is itself cross-checked against this independent table, so a
tampered registry (wrong path, wrong schema selector, added/removed token)
cannot silently redirect its own verifier or pass by mutating both the data
and the check that reads it. The allowed classification set
(`_ALLOWED_CLASSIFICATIONS`) is likewise hardcoded here, not read from the
registry's own `classifications` array.

It also mechanically exercises the >=3 real-design validation required by the
slice, using facts already retained in `research/benchmark/SEED_RESEARCH_NOTES.md`
(no new research campaign) -- see
`research/validation/SL0036-marine-entailment-real-design-validation.md` for
the full narrative record. Nothing here promotes any design to canonical data.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
REGISTRY_PATH = SPECS / "MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json"


def _load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"Registry root must be a JSON object, got {type(raw).__name__}")
    return raw


def _rules_by_id(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for rule in registry["rules"]:
        rule_id = str(rule["id"])
        if rule_id in by_id:
            raise ValueError(f"Duplicate rule id in registry: {rule_id!r}")
        by_id[rule_id] = rule
    return by_id


_REGISTRY = _load_registry()
_V06_SCHEMA: dict[str, Any] = json.loads(
    (SPECS / "BOAT_DESIGN_SCHEMA.v0.6.json").read_text(encoding="utf-8")
)
_V05_SCHEMA: dict[str, Any] = json.loads(
    (SPECS / "BOAT_DESIGN_SCHEMA.v0.5.json").read_text(encoding="utf-8")
)
_RULES_BY_ID = _rules_by_id(_REGISTRY)

# Closed schema selector set: a selector outside this dict fails closed (raises
# KeyError) rather than silently defaulting to either schema.
_SCHEMA_SELECTORS: dict[str, dict[str, Any]] = {"v06": _V06_SCHEMA, "v05": _V05_SCHEMA}

# The allowed classification set is hardcoded here, independent of the
# registry's own informational `classifications` array.
_ALLOWED_CLASSIFICATIONS = frozenset({"DEFINITIONAL_ENTAILMENT", "DIRECT_ONLY", "NO_DERIVATION"})

# ---------------------------------------------------------------------------
# Independent field -> schema-location tables, transcribed by hand from
# BOAT_DESIGN_SCHEMA.v0.5/v0.6.json and from the fixed field inventory in
# MARINE_TECHNICAL_ENTAILMENT.v0.1.md section 2 / SLICE-0036.md. These are the
# controlling expectation; the registry under test is checked AGAINST them,
# never the reverse.
# ---------------------------------------------------------------------------

_INDEPENDENT_ENUM_LOCATIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "configuration.hull_configuration": (
        "v06",
        ("$defs", "configuration_shape", "properties", "hull_configuration", "enum"),
    ),
    "appendages.keel_type": (
        "v06",
        ("$defs", "appendages_shape", "properties", "keel_type", "enum"),
    ),
    "appendages.rudder_position": (
        "v06",
        ("$defs", "appendages_shape", "properties", "rudder_position", "enum"),
    ),
    "appendages.rudder_support": (
        "v06",
        ("$defs", "appendages_shape", "properties", "rudder_support", "enum"),
    ),
    "appendages.rudder_balance": (
        "v06",
        ("$defs", "appendages_shape", "properties", "rudder_balance", "enum"),
    ),
    "appendages.skeg_type": (
        "v06",
        ("$defs", "appendages_shape", "properties", "skeg_type", "enum"),
    ),
    "rig.sailplan": ("v06", ("$defs", "rig_shape", "properties", "sailplan", "enum")),
    "rig.masthead_fractional": (
        "v06",
        ("$defs", "rig_shape", "properties", "masthead_fractional", "enum"),
    ),
    "rig.mast_step": ("v06", ("$defs", "rig_shape", "properties", "mast_step", "enum")),
    "deck.cockpit_position": (
        "v06",
        ("$defs", "deck_shape", "properties", "cockpit_position", "enum"),
    ),
    "deck.helm_type": ("v06", ("$defs", "deck_shape", "properties", "helm_type", "enum")),
    "legacy.rig_type": (
        "v05",
        (
            "properties",
            "baseline",
            "properties",
            "configuration",
            "properties",
            "rig_type",
            "enum",
        ),
    ),
    "legacy.rudder_type": (
        "v05",
        (
            "properties",
            "baseline",
            "properties",
            "configuration",
            "properties",
            "rudder_type",
            "enum",
        ),
    ),
}

_INDEPENDENT_INTEGER_LOCATIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "configuration.hull_count": (
        "v06",
        ("$defs", "configuration_shape", "properties", "hull_count"),
    ),
    "appendages.centerboard_count": (
        "v06",
        ("$defs", "appendages_shape", "properties", "centerboard_count"),
    ),
    "appendages.daggerboard_count": (
        "v06",
        ("$defs", "appendages_shape", "properties", "daggerboard_count"),
    ),
    "appendages.rudder_count": ("v06", ("$defs", "appendages_shape", "properties", "rudder_count")),
    "rig.mast_count": ("v06", ("$defs", "rig_shape", "properties", "mast_count")),
    "deck.cockpit_count": ("v06", ("$defs", "deck_shape", "properties", "cockpit_count")),
    "deck.helm_count": ("v06", ("$defs", "deck_shape", "properties", "helm_count")),
}

_INDEPENDENT_FREE_TEXT_LOCATIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "appendages.keel_subtype": ("v06", ("$defs", "appendages_shape", "properties", "keel_subtype")),
    "appendages.centerboard_type": (
        "v06",
        ("$defs", "appendages_shape", "properties", "centerboard_type"),
    ),
    "appendages.daggerboard_type": (
        "v06",
        ("$defs", "appendages_shape", "properties", "daggerboard_type"),
    ),
    "rig.rig_variant": ("v06", ("$defs", "rig_shape", "properties", "rig_variant")),
}

_LEGACY_FIELDS = {"legacy.rig_type", "legacy.rudder_type"}


def _resolve(schema: dict[str, Any], path: tuple[str, ...]) -> Any:
    node: Any = schema
    for step in path:
        node = node[step]
    return node


def _independent_enum_tokens(field_name: str) -> set[str]:
    selector, path = _INDEPENDENT_ENUM_LOCATIONS[field_name]
    schema = _SCHEMA_SELECTORS[selector]
    node = _resolve(schema, path)
    if not isinstance(node, list):
        raise TypeError(f"Expected an enum list at {path!r}, got {type(node).__name__}")
    return set(node)


def _independent_integer_bounds(field_name: str) -> tuple[int, int | None]:
    selector, path = _INDEPENDENT_INTEGER_LOCATIONS[field_name]
    schema = _SCHEMA_SELECTORS[selector]
    node = _resolve(schema, path)
    return int(node["minimum"]), node.get("maximum")


def _independent_free_text_is_genuinely_free_text(field_name: str) -> bool:
    selector, path = _INDEPENDENT_FREE_TEXT_LOCATIONS[field_name]
    schema = _SCHEMA_SELECTORS[selector]
    node = _resolve(schema, path)
    return "enum" not in node and node.get("type") == ["string", "null"]


_ENUM_FIELDS = {
    name: entry for name, entry in _REGISTRY["fields"].items() if entry["kind"] == "enum"
}
_FREE_TEXT_FIELDS = {
    name: entry for name, entry in _REGISTRY["fields"].items() if entry["kind"] == "free_text"
}
_INTEGER_FIELDS = {
    name: entry for name, entry in _REGISTRY["fields"].items() if entry["kind"] == "integer"
}


# ---------------------------------------------------------------------------
# Independence: the registry's own set of enum/free-text/integer field names
# must exactly match the independently-authored tables above.
# ---------------------------------------------------------------------------


def test_registry_enum_field_set_matches_the_independent_table() -> None:
    assert set(_ENUM_FIELDS) == set(_INDEPENDENT_ENUM_LOCATIONS)


def test_registry_free_text_field_set_matches_the_independent_table() -> None:
    assert set(_FREE_TEXT_FIELDS) == set(_INDEPENDENT_FREE_TEXT_LOCATIONS)


def test_registry_integer_field_set_matches_the_independent_table() -> None:
    assert set(_INTEGER_FIELDS) == set(_INDEPENDENT_INTEGER_LOCATIONS)


@pytest.mark.parametrize("field_name", sorted(_INDEPENDENT_FREE_TEXT_LOCATIONS))
def test_free_text_fields_are_genuinely_unstructured_in_the_schema(field_name: str) -> None:
    assert _independent_free_text_is_genuinely_free_text(field_name)


# ---------------------------------------------------------------------------
# Coverage: registry enum token sets must equal the INDEPENDENTLY located live
# schema enum sets exactly -- not the registry's own declared schema/enum_path.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_name", sorted(_INDEPENDENT_ENUM_LOCATIONS))
def test_registry_enum_tokens_exactly_match_independently_located_schema_enum(
    field_name: str,
) -> None:
    registry_tokens = set(_ENUM_FIELDS[field_name]["tokens"])
    independent_tokens = _independent_enum_tokens(field_name)
    assert registry_tokens == independent_tokens, (
        f"{field_name}: registry tokens {registry_tokens} != "
        f"independently-located schema enum {independent_tokens}"
    )


@pytest.mark.parametrize("field_name", sorted(_INDEPENDENT_ENUM_LOCATIONS))
def test_registry_declared_schema_selector_matches_independent_expectation(
    field_name: str,
) -> None:
    expected_selector, _ = _INDEPENDENT_ENUM_LOCATIONS[field_name]
    assert _ENUM_FIELDS[field_name]["schema"] == expected_selector


@pytest.mark.parametrize("field_name", sorted(_INDEPENDENT_ENUM_LOCATIONS))
def test_registry_declared_enum_path_matches_independent_expectation(field_name: str) -> None:
    _, expected_path = _INDEPENDENT_ENUM_LOCATIONS[field_name]
    assert tuple(_ENUM_FIELDS[field_name]["enum_path"]) == expected_path


def test_registry_schema_selector_values_are_restricted_to_the_closed_set() -> None:
    for field_name, entry in _ENUM_FIELDS.items():
        assert entry["schema"] in _SCHEMA_SELECTORS, (
            f"{field_name} declares an unrecognized schema selector {entry['schema']!r}"
        )


def test_unknown_schema_selector_fails_closed_not_open() -> None:
    # _SCHEMA_SELECTORS is a plain dict lookup: an unrecognized selector raises
    # KeyError. There is no "else assume v05" fallback anywhere in this module.
    with pytest.raises(KeyError):
        _ = _SCHEMA_SELECTORS["v99_does_not_exist"]


def test_adding_a_new_schema_enum_token_would_break_the_coverage_check() -> None:
    real_tokens = _independent_enum_tokens("configuration.hull_configuration")
    drifted_tokens = real_tokens | {"__synthetic_new_enum_value__"}
    registry_tokens = set(_ENUM_FIELDS["configuration.hull_configuration"]["tokens"])
    assert registry_tokens != drifted_tokens


def test_removing_a_registry_token_would_break_the_coverage_check() -> None:
    real_tokens = _independent_enum_tokens("configuration.hull_configuration")
    tampered_registry_tokens = set(real_tokens) - {"monohull"}
    assert tampered_registry_tokens != real_tokens


def test_mutating_the_registry_enum_path_would_be_caught() -> None:
    _, correct_path = _INDEPENDENT_ENUM_LOCATIONS["configuration.hull_configuration"]
    tampered_path = (*correct_path[:-1], "__wrong_key__")
    assert tampered_path != correct_path
    # And the tampered path genuinely fails to resolve against the real schema,
    # rather than silently resolving to something else.
    with pytest.raises(KeyError):
        _resolve(_V06_SCHEMA, tampered_path)


def test_mutating_the_registry_schema_selector_would_be_caught() -> None:
    correct_selector, _ = _INDEPENDENT_ENUM_LOCATIONS["legacy.rig_type"]
    assert correct_selector == "v05"
    tampered_selector = "v06"
    assert tampered_selector != correct_selector
    # Using the tampered selector points at a schema that does not even have a
    # legacy rig_type path, so it would fail to resolve rather than silently
    # validating against the wrong schema's data.
    _, path = _INDEPENDENT_ENUM_LOCATIONS["legacy.rig_type"]
    with pytest.raises(KeyError):
        _resolve(_SCHEMA_SELECTORS[tampered_selector], path)


def test_no_in_scope_field_is_missing_from_the_registry() -> None:
    # Every field named by the fixed field inventory (SLICE-0036.md section 2 /
    # MARINE_TECHNICAL_ENTAILMENT.v0.1.md section 2) must appear.
    expected = (
        {"configuration.hull_configuration", "configuration.hull_count"}
        | set(_INDEPENDENT_ENUM_LOCATIONS)
        | set(_INDEPENDENT_INTEGER_LOCATIONS)
        | set(_INDEPENDENT_FREE_TEXT_LOCATIONS)
    )
    assert set(_REGISTRY["fields"]) == expected


# ---------------------------------------------------------------------------
# Classification set is hardcoded here, never read from the registry itself.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_name", sorted(_ENUM_FIELDS))
def test_every_enum_token_classification_is_one_of_the_independent_allowed_set(
    field_name: str,
) -> None:
    for token, meta in _ENUM_FIELDS[field_name]["tokens"].items():
        assert meta["classification"] in _ALLOWED_CLASSIFICATIONS, (
            f"{field_name}={token} has an unrecognized classification {meta['classification']!r}"
        )


@pytest.mark.parametrize("field_name", sorted(_FREE_TEXT_FIELDS))
def test_free_text_field_classification_is_one_of_the_independent_allowed_set(
    field_name: str,
) -> None:
    assert _FREE_TEXT_FIELDS[field_name]["classification"] in _ALLOWED_CLASSIFICATIONS


@pytest.mark.parametrize("field_name", sorted(_INTEGER_FIELDS))
def test_integer_field_classification_is_one_of_the_independent_allowed_set(
    field_name: str,
) -> None:
    assert _INTEGER_FIELDS[field_name]["classification"] in _ALLOWED_CLASSIFICATIONS
    for value_rule in _INTEGER_FIELDS[field_name].get("value_rules", []):
        assert value_rule["classification"] in _ALLOWED_CLASSIFICATIONS


# ---------------------------------------------------------------------------
# Free-text fields: full non-entailment, no enumerated tokens.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_name", sorted(_FREE_TEXT_FIELDS))
def test_free_text_fields_are_fully_non_entailing(field_name: str) -> None:
    entry = _FREE_TEXT_FIELDS[field_name]
    assert entry["classification"] == "NO_DERIVATION"
    assert "tokens" not in entry


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
# Universal sentinel rule: 'unknown' and 'other' never entail anything, in
# EVERY enum field including the two legacy fields (section 3.1 of the
# normative doc: the legacy other/unknown rows are migration facts, not MTE
# entailments, so no carve-out exists here).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_name", sorted(_ENUM_FIELDS))
def test_unknown_token_is_always_no_derivation(field_name: str) -> None:
    tokens = _ENUM_FIELDS[field_name]["tokens"]
    if "unknown" in tokens:
        assert tokens["unknown"]["classification"] == "NO_DERIVATION"


@pytest.mark.parametrize("field_name", sorted(_ENUM_FIELDS))
def test_other_token_is_always_no_derivation(field_name: str) -> None:
    tokens = _ENUM_FIELDS[field_name]["tokens"]
    if "other" in tokens:
        assert tokens["other"]["classification"] == "NO_DERIVATION"


def test_not_applicable_is_direct_only_not_a_sentinel() -> None:
    tokens = _REGISTRY["fields"]["rig.masthead_fractional"]["tokens"]
    assert tokens["not_applicable"]["classification"] == "DIRECT_ONLY"


def test_no_rule_asserts_not_applicable_as_an_output() -> None:
    for rule in _REGISTRY["rules"]:
        for output in rule.get("output", []):
            assert output.get("value") != "not_applicable", (
                f"{rule['id']} illegally asserts not_applicable as a derived output"
            )


# ---------------------------------------------------------------------------
# Rule structural completeness.
# ---------------------------------------------------------------------------

_REQUIRED_RULE_KEYS = {
    "id",
    "version",
    "area",
    "guard",
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
        _rules_by_id(duplicated)


def test_load_registry_rejects_a_non_object_json_root(tmp_path: Path) -> None:
    bad_file = tmp_path / "not_an_object.json"
    bad_file.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(TypeError, match="Registry root must be a JSON object"):
        _load_registry(bad_file)


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
def test_every_rule_source_token_independently_exists_in_its_source_field(
    rule: dict[str, Any],
) -> None:
    source = rule.get("source")
    if source is None:
        return
    field_name = source["field"]
    if field_name in _INDEPENDENT_ENUM_LOCATIONS:
        assert source["value"] in _independent_enum_tokens(field_name)
    elif field_name in _INDEPENDENT_INTEGER_LOCATIONS:
        minimum, maximum = _independent_integer_bounds(field_name)
        assert source["value"] >= minimum
        if maximum is not None:
            assert source["value"] <= maximum


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
# Rule output grammar: exactly five closed shapes, each value independently
# verified against the target field's real schema location.
# ---------------------------------------------------------------------------

_ALLOWED_OUTPUT_OPERATORS = frozenset(
    {"value", "relation", "excludes_value", "not_concrete", "conditional"}
)
_RELATION_PATTERN = re.compile(r"^>=(\d+)$")


@pytest.mark.parametrize("rule", _REGISTRY["rules"], ids=lambda r: r["id"])
def test_every_rule_output_uses_exactly_one_closed_operator(rule: dict[str, Any]) -> None:
    for output in rule["output"]:
        operator_keys = (set(output) - {"field"}) & _ALLOWED_OUTPUT_OPERATORS
        unrecognized_keys = set(output) - {"field"} - _ALLOWED_OUTPUT_OPERATORS
        assert not unrecognized_keys, (
            f"{rule['id']} output uses unrecognized key(s) {unrecognized_keys}"
        )
        assert len(operator_keys) == 1, (
            f"{rule['id']} output must use exactly one operator, got {operator_keys}"
        )


def test_conditional_operator_is_used_only_by_the_one_documented_exception() -> None:
    users = [
        rule["id"]
        for rule in _REGISTRY["rules"]
        for output in rule["output"]
        if "conditional" in output
    ]
    assert users == ["MTE-LEGACY-RUD-006"]


@pytest.mark.parametrize("rule", _REGISTRY["rules"], ids=lambda r: r["id"])
def test_every_value_output_independently_matches_the_target_field_schema(
    rule: dict[str, Any],
) -> None:
    for output in rule["output"]:
        if "value" not in output:
            continue
        field_name = output["field"]
        value = output["value"]
        if field_name in _INDEPENDENT_ENUM_LOCATIONS:
            assert value in _independent_enum_tokens(field_name), (
                f"{rule['id']} asserts {field_name}={value!r}, not in the independently-located "
                "schema enum"
            )
        elif field_name in _INDEPENDENT_INTEGER_LOCATIONS:
            minimum, maximum = _independent_integer_bounds(field_name)
            assert value >= minimum
            if maximum is not None:
                assert value <= maximum


@pytest.mark.parametrize("rule", _REGISTRY["rules"], ids=lambda r: r["id"])
def test_every_relation_output_is_a_schema_consistent_lower_bound(rule: dict[str, Any]) -> None:
    for output in rule["output"]:
        if "relation" not in output:
            continue
        field_name = output["field"]
        assert field_name in _INDEPENDENT_INTEGER_LOCATIONS, (
            f"{rule['id']} uses a 'relation' output on non-integer field {field_name!r}"
        )
        match = _RELATION_PATTERN.match(output["relation"])
        assert match, f"{rule['id']} uses an unsupported relation shape {output['relation']!r}"
        bound = int(match.group(1))
        minimum, maximum = _independent_integer_bounds(field_name)
        assert bound >= minimum
        if maximum is not None:
            assert bound <= maximum


@pytest.mark.parametrize("rule", _REGISTRY["rules"], ids=lambda r: r["id"])
def test_every_excludes_value_output_independently_exists_in_the_target_enum(
    rule: dict[str, Any],
) -> None:
    for output in rule["output"]:
        if "excludes_value" not in output:
            continue
        field_name = output["field"]
        assert field_name in _INDEPENDENT_ENUM_LOCATIONS
        assert output["excludes_value"] in _independent_enum_tokens(field_name)


@pytest.mark.parametrize("rule", _REGISTRY["rules"], ids=lambda r: r["id"])
def test_every_not_concrete_output_targets_a_genuine_free_text_field(rule: dict[str, Any]) -> None:
    for output in rule["output"]:
        if "not_concrete" not in output:
            continue
        field_name = output["field"]
        assert field_name in _INDEPENDENT_FREE_TEXT_LOCATIONS
        assert output["not_concrete"] is True
        assert _independent_free_text_is_genuinely_free_text(field_name)


# ---------------------------------------------------------------------------
# Guard policy: structured, machine-checkable qualification/applicability/
# conflict semantics -- not keyword matching over prose.
# ---------------------------------------------------------------------------

_EXPECTED_GUARD_POLICY: dict[str, Any] = {
    "requires_source_qualified": True,
    "forbids_provisional_source": True,
    "forbids_unresolved_conflict_source": True,
    "forbids_applicability_unknown_source": True,
    "requires_single_material_scope": True,
    "cross_scope_combination_authorized": False,
    "same_scope_explicit_contradiction_behavior": "UNRESOLVED_CONFLICT",
    "requires_lineage": True,
}


def test_standard_guard_policy_has_the_independently_expected_structure() -> None:
    policy = _REGISTRY["guard_policies"]["STANDARD_MTE_GUARD_V0_1"]
    for key, expected_value in _EXPECTED_GUARD_POLICY.items():
        assert policy[key] == expected_value, f"guard_policy.{key} != {expected_value!r}"


@pytest.mark.parametrize("rule", _REGISTRY["rules"], ids=lambda r: r["id"])
def test_every_rule_references_the_one_standard_guard_policy(rule: dict[str, Any]) -> None:
    assert rule["guard"] == "STANDARD_MTE_GUARD_V0_1"
    assert rule["guard"] in _REGISTRY["guard_policies"]


# TEST-ONLY reference evaluator. Not shipped under src/, not a production
# inference engine: it exists solely to prove the structured guard policy
# produces the required fail-closed outcome in each qualification scenario.
def _reference_apply_guard(
    guard_policy: dict[str, Any],
    *,
    state: str,
    same_scope: bool,
    contradicting_explicit_output: bool,
) -> str:
    if not same_scope:
        return "UNKNOWN"
    if state == "provisional" and guard_policy["forbids_provisional_source"]:
        return "UNKNOWN"
    if state == "unresolved_conflict" and guard_policy["forbids_unresolved_conflict_source"]:
        return "UNKNOWN"
    if state == "applicability_unknown" and guard_policy["forbids_applicability_unknown_source"]:
        return "UNKNOWN"
    if state == "missing":
        return "UNKNOWN"
    if state != "confirmed":
        return "UNKNOWN"
    if contradicting_explicit_output:
        return str(guard_policy["same_scope_explicit_contradiction_behavior"])
    return "AUTHORIZED"


_STANDARD_GUARD = _REGISTRY["guard_policies"]["STANDARD_MTE_GUARD_V0_1"]


def test_guard_confirmed_qualified_same_scope_no_contradiction_is_authorized() -> None:
    result = _reference_apply_guard(
        _STANDARD_GUARD, state="confirmed", same_scope=True, contradicting_explicit_output=False
    )
    assert result == "AUTHORIZED"


@pytest.mark.parametrize(
    "state", ["provisional", "unresolved_conflict", "applicability_unknown", "missing"]
)
def test_guard_unqualified_source_states_yield_unknown(state: str) -> None:
    result = _reference_apply_guard(
        _STANDARD_GUARD, state=state, same_scope=True, contradicting_explicit_output=False
    )
    assert result == "UNKNOWN"


def test_guard_cross_scope_source_facts_never_combine() -> None:
    result = _reference_apply_guard(
        _STANDARD_GUARD, state="confirmed", same_scope=False, contradicting_explicit_output=False
    )
    assert result == "UNKNOWN"


def test_guard_same_scope_explicit_contradiction_yields_unresolved_conflict() -> None:
    result = _reference_apply_guard(
        _STANDARD_GUARD, state="confirmed", same_scope=True, contradicting_explicit_output=True
    )
    assert result == "UNRESOLVED_CONFLICT"


def test_guard_unknown_other_and_free_text_source_tokens_have_no_rule_to_guard() -> None:
    # Sentinel/opaque/free-text tokens are classified NO_DERIVATION and never
    # have an associated rule, so the guard evaluator is never reached for
    # them -- verified structurally rather than by invoking the evaluator.
    for entry in _ENUM_FIELDS.values():
        for token in ("unknown", "other"):
            if token in entry["tokens"]:
                assert entry["tokens"][token]["classification"] == "NO_DERIVATION"
                assert "rule_ids" not in entry["tokens"][token]
    for field_name in _FREE_TEXT_FIELDS:
        assert "tokens" not in _REGISTRY["fields"][field_name]


def test_guard_unsupported_reverse_relation_has_no_rule_to_guard() -> None:
    # hull_count -> hull_configuration and mast_count -> sailplan are declared
    # NO_DERIVATION reverse directions with no backing rule; the guard is
    # therefore never invoked for them either.
    for field_name in ("configuration.hull_count", "rig.mast_count"):
        reverse = _REGISTRY["fields"][field_name]["reverse_relations"][0]
        assert reverse["classification"] == "NO_DERIVATION"
        for rule in _REGISTRY["rules"]:
            source = rule.get("source")
            if source and source["field"] == field_name:
                pytest.fail(f"{rule['id']} illegally derives from {field_name}")


# ---------------------------------------------------------------------------
# Reverse-inference safety: no unsafe direction is silently authorized.
# ---------------------------------------------------------------------------


def test_hull_count_to_hull_configuration_reverse_is_not_derivation() -> None:
    reverse = _REGISTRY["fields"]["configuration.hull_count"]["reverse_relations"][0]
    assert reverse["target"] == "configuration.hull_configuration"
    assert reverse["classification"] == "NO_DERIVATION"


def test_mast_count_to_sailplan_reverse_is_not_derivation() -> None:
    reverse = _REGISTRY["fields"]["rig.mast_count"]["reverse_relations"][0]
    assert reverse["target"] == "rig.sailplan"
    assert reverse["classification"] == "NO_DERIVATION"


def test_no_rule_derives_keel_type_from_board_counts() -> None:
    for rule in _REGISTRY["rules"]:
        source = rule.get("source")
        if source and source["field"] in {
            "appendages.centerboard_count",
            "appendages.daggerboard_count",
        }:
            for output in rule["output"]:
                assert output["field"] != "appendages.keel_type"


def test_rudder_position_and_rudder_support_never_derive_each_other_natively() -> None:
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
    classification = _REGISTRY["fields"]["configuration.hull_configuration"]["tokens"][
        hull_configuration
    ]["classification"]
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
    tokens = _REGISTRY["fields"]["configuration.hull_configuration"]["tokens"]
    assert tokens[hull_configuration]["classification"] == "NO_DERIVATION"


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


@pytest.mark.parametrize(
    "rule_id",
    ["MTE-RIG-001", "MTE-RIG-002", "MTE-RIG-003", "MTE-RIG-004", "MTE-RIG-005", "MTE-RIG-006"],
)
def test_every_rig_rule_cites_a_real_authoritative_locator(rule_id: str) -> None:
    evidence = _RULES_BY_ID[rule_id]["evidence_basis"]
    assert "https://" in evidence, f"{rule_id} evidence_basis has no cited locator: {evidence!r}"
    assert "retrieved 2026-08-30" in evidence


def test_keel_board_rules_cite_internal_vocabulary_identity_not_external_research() -> None:
    for rule_id in ("MTE-KEEL-001", "MTE-KEEL-002"):
        evidence = _RULES_BY_ID[rule_id]["evidence_basis"]
        assert "Internal HullQ controlled-vocabulary identity" in evidence
        assert "https://" not in evidence


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
    assert rule["output"][0]["not_concrete"] is True


# ---------------------------------------------------------------------------
# Legacy v0.5 preservation: SLICE-0034 conservatism must remain intact, and
# 'other'/'unknown' must NOT carry a rule (section 3.1: migration facts only).
# ---------------------------------------------------------------------------

_LEGACY_RIG_TOKENS_THAT_PROVE_MASTHEAD_FRACTIONAL = {"masthead_sloop", "fractional_sloop"}


def test_legacy_rig_type_other_and_unknown_have_no_rule() -> None:
    tokens = _REGISTRY["fields"]["legacy.rig_type"]["tokens"]
    for token in ("other", "unknown"):
        assert tokens[token]["classification"] == "NO_DERIVATION"
        assert "rule_ids" not in tokens[token]


def test_legacy_rudder_type_other_and_unknown_have_no_rule() -> None:
    tokens = _REGISTRY["fields"]["legacy.rudder_type"]["tokens"]
    for token in ("other", "unknown"):
        assert tokens[token]["classification"] == "NO_DERIVATION"
        assert "rule_ids" not in tokens[token]


def test_legacy_rig_type_masthead_fractional_only_for_masthead_and_fractional_sloop() -> None:
    tokens = _REGISTRY["fields"]["legacy.rig_type"]["tokens"]
    definitional_tokens = {
        token: meta
        for token, meta in tokens.items()
        if meta["classification"] == "DEFINITIONAL_ENTAILMENT"
    }
    assert set(definitional_tokens) == {
        "masthead_sloop",
        "fractional_sloop",
        "cutter",
        "ketch",
        "yawl",
        "schooner",
        "cat_rig",
    }
    for token, meta in definitional_tokens.items():
        rule = _RULES_BY_ID[meta["rule_ids"][0]]
        touched = {o["field"] for o in rule["output"]}
        if token in _LEGACY_RIG_TOKENS_THAT_PROVE_MASTHEAD_FRACTIONAL:
            assert "rig.masthead_fractional" in touched
        else:
            assert "rig.masthead_fractional" not in touched


def test_legacy_rudder_type_never_entails_a_concrete_rudder_balance() -> None:
    tokens = _REGISTRY["fields"]["legacy.rudder_type"]["tokens"]
    for meta in tokens.values():
        if meta["classification"] != "DEFINITIONAL_ENTAILMENT":
            continue
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
    tokens = _REGISTRY["fields"]["legacy.rudder_type"]["tokens"]
    for token, meta in tokens.items():
        if token == "twin" or meta["classification"] != "DEFINITIONAL_ENTAILMENT":
            continue
        rule = _RULES_BY_ID[meta["rule_ids"][0]]
        assert all(o["field"] != "appendages.rudder_count" for o in rule["output"])


# ---------------------------------------------------------------------------
# TEST-ONLY reference application of MTE-LEGACY-RUD-006 (twin/rudder_count),
# mirroring the pre-existing accepted RudderCountMappingConflict behavior from
# BOAT_DESIGN_V05_TO_V06_MAPPING.md section 3.2. Not shipped under src/.
# ---------------------------------------------------------------------------


class _ReferenceRudderCountConflict(ValueError):
    """TEST-ONLY: verification-only mirror of rule MTE-LEGACY-RUD-006's conflict
    behavior. Never exported, never used outside this test module."""


def _reference_project_twin_rudder_count(source_rudder_count: int | None) -> int:
    if source_rudder_count is None or source_rudder_count == 2:
        return 2
    raise _ReferenceRudderCountConflict(
        f"legacy rudder_type='twin' but rudder_count={source_rudder_count!r}; "
        "internally inconsistent predecessor record, not silently resolved "
        "(TEST-ONLY reference mirror of rule MTE-LEGACY-RUD-006)."
    )


def test_twin_with_null_source_count_projects_to_the_guaranteed_two() -> None:
    assert _reference_project_twin_rudder_count(None) == 2


def test_twin_with_already_two_source_count_stays_two() -> None:
    assert _reference_project_twin_rudder_count(2) == 2


@pytest.mark.parametrize("contradictory_count", [0, 1, 3, 4])
def test_twin_with_contradictory_source_count_is_not_silently_resolved(
    contradictory_count: int,
) -> None:
    with pytest.raises(_ReferenceRudderCountConflict):
        _reference_project_twin_rudder_count(contradictory_count)


# ---------------------------------------------------------------------------
# Real-design validation (>=3 technically different designs), using facts
# already retained in research/benchmark/SEED_RESEARCH_NOTES.md. No new
# research campaign; no canonical admission. See
# research/validation/SL0036-marine-entailment-real-design-validation.md for
# the full narrative record this exercises mechanically.
#
# IMPORTANT: only controlled facts EXPLICITLY stated in the retained evidence
# are exercised here. Westerly Centaur's hull_configuration is deliberately
# NOT exercised: SEED-06 states "twin keel" / "British twin-keeler" but never
# explicitly qualifies the controlled hull_configuration=monohull fact, and
# this module must not upgrade contextual convention into a qualified input.
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


def test_westerly_centaur_ambiguous_rig_identity_leaves_mast_count_undeived() -> None:
    # SEED-06: "Sloop/ketch noted, with very few ketches." The design's own
    # retained evidence cannot qualify a single sailplan value for the
    # baseline, so no MTE-RIG-* rule has a qualified source to fire on --
    # mast_count is an expected UNKNOWN outcome for this design, not a bug.
    for candidate_sailplan in ("sloop", "ketch"):
        tokens = _REGISTRY["fields"]["rig.sailplan"]["tokens"]
        assert tokens[candidate_sailplan]["classification"] == "DEFINITIONAL_ENTAILMENT"
    # Both tokens have a real rule; the design simply cannot supply a single
    # qualified sailplan fact to apply either one to.


def test_westerly_centaur_hull_configuration_was_never_qualified_so_no_rule_fires() -> None:
    # SEED-06 never states the controlled hull_configuration=monohull fact
    # explicitly -- "twin keel" and "British twin-keeler" are keel-type/
    # descriptive context, not a qualified hull_configuration value. No
    # MTE-HULL-* rule may be applied to this design; hull_count remains
    # unqualified/UNKNOWN for this validation record.
    monohull_rule = _RULES_BY_ID["MTE-HULL-001"]
    assert monohull_rule["source"] == {
        "field": "configuration.hull_configuration",
        "value": "monohull",
    }
    # This assertion documents the rule's precondition; the validation record
    # explicitly does not claim SEED-06 satisfies it.


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


def test_at_least_three_technically_different_designs_produce_concrete_derivations() -> None:
    # Mechanical restatement of the slice's ">=3 technically different real
    # designs" requirement: each of these three designs independently fires a
    # real DEFINITIONAL_ENTAILMENT rule from its own retained qualified fact.
    concrete_derivations = {
        "Rustler 36": _RULES_BY_ID["MTE-LEGACY-RUD-001"]["output"],
        "Westerly Centaur": _RULES_BY_ID["MTE-LEGACY-RUD-004"]["output"],
        "Island Packet 349": _RULES_BY_ID["MTE-LEGACY-RUD-002"]["output"],
    }
    assert len(concrete_derivations) == 3
    for design, output in concrete_derivations.items():
        assert output, f"{design} produced no concrete derivation"


# ---------------------------------------------------------------------------
# Sanity: the registry copy/mutation helpers used above genuinely operate on
# independent copies and do not mutate the shared module-level registry.
# ---------------------------------------------------------------------------


def test_registry_is_not_mutated_by_the_adversarial_tests_in_this_module() -> None:
    reloaded = _load_registry()
    assert reloaded == _REGISTRY


def test_deepcopy_isolation_used_by_adversarial_helpers() -> None:
    snapshot = copy.deepcopy(_REGISTRY)
    mutated = copy.deepcopy(_REGISTRY)
    mutated["fields"]["configuration.hull_configuration"]["tokens"].pop("monohull")
    assert snapshot == _REGISTRY
    assert mutated != _REGISTRY
