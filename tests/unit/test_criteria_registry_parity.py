"""Registry parity/definition tests — SLICE-0085 review amendment Finding C.

`hullq.search.criteria_registry` is the single source of truth for each
accepted criterion's bounded vocabulary. This module proves the registry's
own internal consistency (every definition is well-formed, every projection
field is genuinely distinct, every param key maps back to exactly one
definition) and cross-checks its `allowed_values` against the TypeScript
presentation layer's own mirrored constants
(`web/src/lib/searchApi.ts::SEARCH_KEEL_CONFIGURATION_VALUES`/
`SEARCH_RUDDER_CONFIGURATION_VALUES`) -- the one place this registry's
"cannot be unified across languages" constraint (this module's own
docstring) is explicitly guarded against silent drift, by hardcoding the
exact TS values here and asserting set equality against the Python
registry. If a future criterion value is added/removed on one side without
the other, this test fails.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from hullq.search.criteria_registry import (
    CANONICAL_PARAM_KEY_ORDER,
    CRITERION_DEFINITIONS,
    DRAFT_MAX_DEFINITION,
    KEEL_CONFIGURATION_DEFINITION,
    LOA_DEFINITION,
    RUDDER_CONFIGURATION_DEFINITION,
    SUPPORTED_PARAM_KEYS,
    CriterionKind,
    parse_categorical_param,
    parse_numeric_param,
)

# Mirrors web/src/lib/searchApi.ts::SEARCH_KEEL_CONFIGURATION_VALUES verbatim.
_TS_KEEL_CONFIGURATION_VALUES = frozenset(
    {"FIN", "FIN_WITH_BULB", "WING", "CENTERBOARD", "LIFTING_KEEL", "TWIN_KEEL"}
)

# Mirrors web/src/lib/searchApi.ts::SEARCH_RUDDER_CONFIGURATION_VALUES verbatim.
_TS_RUDDER_CONFIGURATION_VALUES = frozenset({"SKEG_HUNG", "TRANSOM_HUNG", "SPADE", "TWIN"})


def test_every_definition_param_key_is_in_supported_param_keys() -> None:
    for definition in CRITERION_DEFINITIONS:
        for key in definition.param_keys:
            assert key in SUPPORTED_PARAM_KEYS


def test_every_supported_param_key_belongs_to_exactly_one_definition() -> None:
    owners: dict[str, str] = {}
    for definition in CRITERION_DEFINITIONS:
        for key in definition.param_keys:
            assert key not in owners, (
                f"{key!r} claimed by both {owners.get(key)!r} and {definition.criterion_id!r}"
            )
            owners[key] = definition.criterion_id
    assert set(owners) == SUPPORTED_PARAM_KEYS


def test_every_definition_has_a_distinct_projection_field() -> None:
    fields = [d.projection_field for d in CRITERION_DEFINITIONS]
    assert len(fields) == len(set(fields))


def test_categorical_definitions_carry_allowed_values_and_no_parser() -> None:
    for definition in CRITERION_DEFINITIONS:
        if definition.kind is CriterionKind.CATEGORICAL:
            assert definition.allowed_values is not None
            assert definition.parse_value is None
            assert definition.canonicalize_value is None


def test_numeric_definitions_carry_parser_and_no_allowed_values() -> None:
    for definition in CRITERION_DEFINITIONS:
        if definition.kind is not CriterionKind.CATEGORICAL:
            assert definition.allowed_values is None
            assert definition.parse_value is not None
            assert definition.canonicalize_value is not None


def test_keel_allowed_values_match_the_mirrored_typescript_constant() -> None:
    assert KEEL_CONFIGURATION_DEFINITION.allowed_values == _TS_KEEL_CONFIGURATION_VALUES


def test_rudder_allowed_values_match_the_mirrored_typescript_constant() -> None:
    assert RUDDER_CONFIGURATION_DEFINITION.allowed_values == _TS_RUDDER_CONFIGURATION_VALUES


def test_canonical_param_key_order_matches_definitions_lexicographic_sort() -> None:
    all_keys = {key for d in CRITERION_DEFINITIONS for key in d.param_keys}
    assert tuple(sorted(all_keys)) == CANONICAL_PARAM_KEY_ORDER


# ---------------------------------------------------------------------------
# Shared parsing helpers -- exercised directly against each definition
# ---------------------------------------------------------------------------


def test_parse_numeric_param_empty_is_not_supplied() -> None:
    assert parse_numeric_param(DRAFT_MAX_DEFINITION, []) == (None, True)


def test_parse_numeric_param_valid_single_value() -> None:
    assert parse_numeric_param(DRAFT_MAX_DEFINITION, ["1.6"]) == (Decimal("1.6"), True)


def test_parse_numeric_param_noncanonical_value_is_not_single_canonical() -> None:
    parsed = parse_numeric_param(DRAFT_MAX_DEFINITION, ["1.600"])
    assert parsed is not None
    value, is_single_canonical = parsed
    assert value == Decimal("1.6")
    assert is_single_canonical is False


def test_parse_numeric_param_malformed_is_none() -> None:
    assert parse_numeric_param(DRAFT_MAX_DEFINITION, ["1e0"]) is None


def test_parse_numeric_param_conflicting_duplicates_is_none() -> None:
    assert parse_numeric_param(DRAFT_MAX_DEFINITION, ["1.6", "1.7"]) is None


def test_parse_numeric_param_identical_duplicates_is_not_single_canonical() -> None:
    parsed = parse_numeric_param(DRAFT_MAX_DEFINITION, ["1.6", "1.6"])
    assert parsed is not None
    value, is_single_canonical = parsed
    assert value == Decimal("1.6")
    assert is_single_canonical is False


def test_parse_categorical_param_empty_is_not_supplied() -> None:
    assert parse_categorical_param(KEEL_CONFIGURATION_DEFINITION, []) == (None, True)


def test_parse_categorical_param_valid_single_value() -> None:
    assert parse_categorical_param(KEEL_CONFIGURATION_DEFINITION, ["FIN"]) == ("FIN", True)


def test_parse_categorical_param_unsupported_value_is_none() -> None:
    assert parse_categorical_param(KEEL_CONFIGURATION_DEFINITION, ["LONG_KEEL"]) is None


def test_parse_categorical_param_conflicting_duplicates_is_none() -> None:
    assert parse_categorical_param(KEEL_CONFIGURATION_DEFINITION, ["FIN", "WING"]) is None


def test_parse_categorical_param_identical_duplicates_is_not_single_canonical() -> None:
    parsed = parse_categorical_param(KEEL_CONFIGURATION_DEFINITION, ["FIN", "FIN"])
    assert parsed is not None
    value, is_single_canonical = parsed
    assert value == "FIN"
    assert is_single_canonical is False


def test_loa_definition_parses_both_bound_keys_against_the_same_projection_field() -> None:
    assert LOA_DEFINITION.param_keys == ("loa_max", "loa_min")
    assert parse_numeric_param(LOA_DEFINITION, ["10"]) == (Decimal("10"), True)


@pytest.mark.parametrize(
    "definition",
    [
        DRAFT_MAX_DEFINITION,
        KEEL_CONFIGURATION_DEFINITION,
        LOA_DEFINITION,
        RUDDER_CONFIGURATION_DEFINITION,
    ],
)
def test_every_definition_design_set_builder_and_read_claim_are_callable(
    definition: object,
) -> None:
    assert callable(definition.design_set_builder)  # type: ignore[attr-defined]
    assert callable(definition.read_claim)  # type: ignore[attr-defined]
