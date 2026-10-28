"""Unit tests for hullq.search.power_criteria_registry — SLICE-0093.

Proves the bounded five-token public whitelist and that this module reuses
the identical shared `CriterionDefinition`/`parse_categorical_param` kernel
the Sail registry already established, rather than a second ad hoc parser.
"""

from __future__ import annotations

import re
from pathlib import Path

from hullq.search.criteria_registry import CriterionDefinition, CriterionKind
from hullq.search.power_criteria_registry import (
    POWER_DRIVE_CONFIGURATION_DEFINITION,
    POWER_DRIVE_PARAM_KEY,
    SEARCH_POWER_DRIVE_VALUES,
    active_power_definitions,
    parse_categorical_param,
)

_POWER_SEARCH_API_TS_PATH = (
    Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "powerSearchApi.ts"
)


def _extract_ts_const_string_array(source_text: str, export_name: str) -> frozenset[str]:
    """Mirrors `test_criteria_registry_parity.py`'s identical extraction
    mechanism -- pure text read, never imports/executes TypeScript."""
    pattern = re.compile(
        rf"export const {re.escape(export_name)}\s*=\s*\[(?P<body>.*?)\]\s*as const;", re.DOTALL
    )
    match = pattern.search(source_text)
    if match is None:
        raise AssertionError(
            f"could not find `export const {export_name} = [...] as const;` in source"
        )
    return frozenset(re.findall(r'"([^"]*)"', match.group("body")))


def test_power_drive_allowed_values_match_the_actual_typescript_export() -> None:
    ts_values = _extract_ts_const_string_array(
        _POWER_SEARCH_API_TS_PATH.read_text(encoding="utf-8"), "SEARCH_POWER_DRIVE_VALUES"
    )
    assert ts_values == SEARCH_POWER_DRIVE_VALUES


def test_five_token_exact_whitelist() -> None:
    assert {"SHAFT", "STERNDRIVE", "POD", "WATERJET", "OUTBOARD"} == SEARCH_POWER_DRIVE_VALUES


def test_mixed_other_unknown_are_not_public_filter_values() -> None:
    assert "MIXED" not in SEARCH_POWER_DRIVE_VALUES
    assert "OTHER" not in SEARCH_POWER_DRIVE_VALUES
    assert "UNKNOWN" not in SEARCH_POWER_DRIVE_VALUES


def test_definition_reuses_shared_criterion_definition_type() -> None:
    assert isinstance(POWER_DRIVE_CONFIGURATION_DEFINITION, CriterionDefinition)
    assert POWER_DRIVE_CONFIGURATION_DEFINITION.kind is CriterionKind.CATEGORICAL
    assert POWER_DRIVE_CONFIGURATION_DEFINITION.param_keys == (POWER_DRIVE_PARAM_KEY,)
    assert POWER_DRIVE_CONFIGURATION_DEFINITION.allowed_values == SEARCH_POWER_DRIVE_VALUES


def test_active_power_definitions_is_exactly_one() -> None:
    assert active_power_definitions() == (POWER_DRIVE_CONFIGURATION_DEFINITION,)


def test_parse_categorical_param_rejects_unsupported_value() -> None:
    assert parse_categorical_param(POWER_DRIVE_CONFIGURATION_DEFINITION, ["DIESEL_ELECTRIC"]) is None


def test_parse_categorical_param_accepts_every_whitelisted_token() -> None:
    for value in SEARCH_POWER_DRIVE_VALUES:
        result = parse_categorical_param(POWER_DRIVE_CONFIGURATION_DEFINITION, [value])
        assert result == (value, True)


def test_parse_categorical_param_empty_is_not_supplied() -> None:
    assert parse_categorical_param(POWER_DRIVE_CONFIGURATION_DEFINITION, []) == (None, True)
