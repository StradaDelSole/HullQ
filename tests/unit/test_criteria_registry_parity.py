"""Registry parity/definition tests — SLICE-0085 review amendment Finding C.

`hullq.search.criteria_registry` is the single source of truth for each
accepted criterion's bounded vocabulary. This module proves the registry's
own internal consistency (every definition is well-formed, every projection
field is genuinely distinct, every param key maps back to exactly one
definition) and cross-checks its `allowed_values` against the TypeScript
presentation layer's own real exported constants
(`web/src/lib/searchApi.ts::SEARCH_KEEL_CONFIGURATION_VALUES`/
`SEARCH_RUDDER_CONFIGURATION_VALUES`) -- the one place this registry's
"cannot be unified across languages" constraint (this module's own
docstring) is explicitly guarded against silent drift.

Review amendment (PR #345 review 5509994284, Finding C parity gap): the
previous version of this module hardcoded a Python copy of the TS values
(`_TS_KEEL_CONFIGURATION_VALUES`/`_TS_RUDDER_CONFIGURATION_VALUES`) and
compared the Python registry against that copy -- a silent TS-side edit
would never be caught, since both "sides" of the comparison lived in this
same Python file. `_extract_ts_const_string_array`, below, instead reads
`web/src/lib/searchApi.ts`'s actual on-disk source text and extracts the
real `export const ... = [...] as const;` string literals via a bounded
regex (no Node/TypeScript runtime invocation, no new runtime dependency, no
dynamic search registry -- purely a static text read, exactly the
"deterministically generated metadata" the review's own remediation
describes). `test_extraction_detects_a_deliberately_divergent_ts_fixture`/
`test_extraction_detects_a_deliberately_missing_value_in_ts_fixture` prove
this mechanism actually distinguishes a genuinely divergent TS source from
the real one -- not merely that parsing succeeds.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest

from hullq.search.criteria_registry import (
    BEAM_DEFINITION,
    CANONICAL_PARAM_KEY_ORDER,
    COCKPIT_POSITION_DEFINITION,
    CRITERION_DEFINITIONS,
    DECK_SALOON_DEFINITION,
    DRAFT_MAX_DEFINITION,
    HULL_CONFIGURATION_DEFINITION,
    HULL_MATERIAL_DEFINITION,
    KEEL_CONFIGURATION_DEFINITION,
    LOA_DEFINITION,
    RUDDER_CONFIGURATION_DEFINITION,
    SUPPORTED_PARAM_KEYS,
    CriterionKind,
    parse_categorical_param,
    parse_numeric_param,
)

_SEARCH_API_TS_PATH = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "searchApi.ts"


def _extract_ts_const_string_array(source_text: str, export_name: str) -> frozenset[str]:
    """Extract the real string literals of a TypeScript
    `export const <export_name> = [...] as const;` array from *source_text*.

    Fails closed (raises `AssertionError`) when *export_name* cannot be
    found at all -- a renamed/removed export must never be silently read as
    an empty, trivially "matching" set. Pure text extraction: never imports,
    executes, or type-checks TypeScript.
    """
    pattern = re.compile(
        rf"export const {re.escape(export_name)}\s*=\s*\[(?P<body>.*?)\]\s*as const;", re.DOTALL
    )
    match = pattern.search(source_text)
    if match is None:
        raise AssertionError(
            f"could not find `export const {export_name} = [...] as const;` in source"
        )
    return frozenset(re.findall(r'"([^"]*)"', match.group("body")))


def _read_search_api_ts_source() -> str:
    return _SEARCH_API_TS_PATH.read_text(encoding="utf-8")


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


def test_keel_allowed_values_match_the_actual_typescript_export() -> None:
    ts_values = _extract_ts_const_string_array(
        _read_search_api_ts_source(), "SEARCH_KEEL_CONFIGURATION_VALUES"
    )
    assert KEEL_CONFIGURATION_DEFINITION.allowed_values == ts_values


def test_rudder_allowed_values_match_the_actual_typescript_export() -> None:
    ts_values = _extract_ts_const_string_array(
        _read_search_api_ts_source(), "SEARCH_RUDDER_CONFIGURATION_VALUES"
    )
    assert RUDDER_CONFIGURATION_DEFINITION.allowed_values == ts_values


def test_hull_configuration_allowed_values_match_the_actual_typescript_export() -> None:
    ts_values = _extract_ts_const_string_array(
        _read_search_api_ts_source(), "SEARCH_HULL_CONFIGURATION_VALUES"
    )
    assert HULL_CONFIGURATION_DEFINITION.allowed_values == ts_values


def test_cockpit_position_allowed_values_match_the_actual_typescript_export() -> None:
    ts_values = _extract_ts_const_string_array(
        _read_search_api_ts_source(), "SEARCH_COCKPIT_POSITION_VALUES"
    )
    assert COCKPIT_POSITION_DEFINITION.allowed_values == ts_values


def test_deck_saloon_allowed_values_match_the_actual_typescript_export() -> None:
    ts_values = _extract_ts_const_string_array(
        _read_search_api_ts_source(), "SEARCH_DECK_SALOON_VALUES"
    )
    assert DECK_SALOON_DEFINITION.allowed_values == ts_values


def test_hull_material_allowed_values_match_the_actual_typescript_export() -> None:
    ts_values = _extract_ts_const_string_array(
        _read_search_api_ts_source(), "SEARCH_HULL_MATERIAL_VALUES"
    )
    assert HULL_MATERIAL_DEFINITION.allowed_values == ts_values


def test_extraction_raises_when_the_export_cannot_be_found() -> None:
    with pytest.raises(AssertionError):
        _extract_ts_const_string_array(
            'export const SOMETHING_ELSE = ["X"] as const;', "SEARCH_KEEL_CONFIGURATION_VALUES"
        )


def test_extraction_detects_a_deliberately_divergent_ts_fixture() -> None:
    """Proves the parity mechanism itself is sensitive to drift -- a
    fixture TS source carrying one extra, real-file-absent value must
    produce a set that does NOT equal the Python registry's own
    `allowed_values`, exactly the failure a genuine TS-side addition would
    trigger in `test_rudder_allowed_values_match_the_actual_typescript_export`."""
    divergent_source = (
        "export const SEARCH_RUDDER_CONFIGURATION_VALUES = [\n"
        '  "SKEG_HUNG",\n'
        '  "TRANSOM_HUNG",\n'
        '  "SPADE",\n'
        '  "TWIN",\n'
        '  "BOGUS_DIVERGENT_VALUE",\n'
        "] as const;\n"
    )
    ts_values = _extract_ts_const_string_array(
        divergent_source, "SEARCH_RUDDER_CONFIGURATION_VALUES"
    )
    assert ts_values != RUDDER_CONFIGURATION_DEFINITION.allowed_values
    assert ts_values - RUDDER_CONFIGURATION_DEFINITION.allowed_values == {"BOGUS_DIVERGENT_VALUE"}


def test_extraction_detects_a_deliberately_missing_value_in_ts_fixture() -> None:
    """Mirrors the divergent-addition test above for the opposite drift
    direction -- a fixture TS source missing a real accepted value."""
    divergent_source = (
        'export const SEARCH_KEEL_CONFIGURATION_VALUES = [\n  "FIN",\n  "WING",\n] as const;\n'
    )
    ts_values = _extract_ts_const_string_array(divergent_source, "SEARCH_KEEL_CONFIGURATION_VALUES")
    assert ts_values != KEEL_CONFIGURATION_DEFINITION.allowed_values
    assert KEEL_CONFIGURATION_DEFINITION.allowed_values - ts_values == {
        "FIN_WITH_BULB",
        "CENTERBOARD",
        "LIFTING_KEEL",
        "TWIN_KEEL",
    }


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


def test_beam_definition_parses_both_bound_keys_against_the_same_projection_field() -> None:
    assert BEAM_DEFINITION.param_keys == ("beam_max", "beam_min")
    assert parse_numeric_param(BEAM_DEFINITION, ["3.2"]) == (Decimal("3.2"), True)


def test_hull_material_rejects_unsupported_actual_claim_vocabulary() -> None:
    # FERROCEMENT/CARBON_COMPOSITE/OTHER remain valid PhysicalBoat claim
    # vocabulary but are never accepted public hard-filter tokens.
    assert parse_categorical_param(HULL_MATERIAL_DEFINITION, ["FERROCEMENT"]) is None
    assert parse_categorical_param(HULL_MATERIAL_DEFINITION, ["CARBON_COMPOSITE"]) is None
    assert parse_categorical_param(HULL_MATERIAL_DEFINITION, ["OTHER"]) is None


@pytest.mark.parametrize(
    "definition",
    [
        DRAFT_MAX_DEFINITION,
        KEEL_CONFIGURATION_DEFINITION,
        LOA_DEFINITION,
        RUDDER_CONFIGURATION_DEFINITION,
        HULL_CONFIGURATION_DEFINITION,
        COCKPIT_POSITION_DEFINITION,
        DECK_SALOON_DEFINITION,
        BEAM_DEFINITION,
        HULL_MATERIAL_DEFINITION,
    ],
)
def test_every_definition_design_set_builder_and_read_claim_are_callable(
    definition: object,
) -> None:
    assert callable(definition.design_set_builder)  # type: ignore[attr-defined]
    assert callable(definition.read_claim)  # type: ignore[attr-defined]
