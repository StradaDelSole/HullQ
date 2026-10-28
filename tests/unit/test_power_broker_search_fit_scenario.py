"""Unit tests for `hullq.application.power_broker_search_fit
.parse_power_search_fit_scenario` — SLICE-0095.

Pure parsing/validation boundary tests, no PostgreSQL dependency -- mirrors
`tests/unit/test_broker_search_fit_scenario.py`'s discipline for the
structurally separate Power preview. The full authorized/owned Search-fit
evaluation (which needs real persisted state) is covered by
`tests/persistence/test_power_broker_search_fit_api.py`.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from hullq.application.power_broker_search_fit import (
    InvalidPowerSearchFitScenarioError,
    parse_power_search_fit_scenario,
)


def test_empty_scenario_is_invalid() -> None:
    with pytest.raises(InvalidPowerSearchFitScenarioError):
        parse_power_search_fit_scenario({})


def test_unknown_parameter_is_invalid() -> None:
    with pytest.raises(InvalidPowerSearchFitScenarioError):
        parse_power_search_fit_scenario({"power_fuel_type": ["DIESEL"]})


def test_sail_parameter_is_invalid() -> None:
    # The Power parser never accepts a Sail scenario key -- two entirely
    # separate parsers (contract §3: never widen one to accept the other's
    # keys).
    with pytest.raises(InvalidPowerSearchFitScenarioError):
        parse_power_search_fit_scenario({"draft_max": ["1.5"]})


def test_power_drive_only_scenario_parses() -> None:
    scenario = parse_power_search_fit_scenario({"power_drive": ["SHAFT"]})
    assert scenario.power_drive == "SHAFT"
    assert scenario.power_engine_count is None


def test_power_engine_count_only_scenario_parses() -> None:
    scenario = parse_power_search_fit_scenario({"power_engine_count": ["2"]})
    assert scenario.power_engine_count == Decimal("2")
    assert scenario.power_drive is None


def test_combined_scenario_parses() -> None:
    scenario = parse_power_search_fit_scenario(
        {"power_drive": ["SHAFT"], "power_engine_count": ["2"]}
    )
    assert scenario.power_drive == "SHAFT"
    assert scenario.power_engine_count == Decimal("2")


def test_unsupported_drive_value_is_invalid() -> None:
    # MIXED/OTHER remain valid PhysicalBoat claim vocabulary but are never
    # an accepted scenario input.
    with pytest.raises(InvalidPowerSearchFitScenarioError):
        parse_power_search_fit_scenario({"power_drive": ["MIXED"]})


def test_duplicate_drive_is_invalid() -> None:
    with pytest.raises(InvalidPowerSearchFitScenarioError):
        parse_power_search_fit_scenario({"power_drive": ["SHAFT", "SHAFT"]})


def test_noncanonical_engine_count_is_invalid() -> None:
    # Unlike the public canonical-URL surface, this private preview has no
    # redirect identity -- a non-canonical spelling fails closed directly.
    with pytest.raises(InvalidPowerSearchFitScenarioError):
        parse_power_search_fit_scenario({"power_engine_count": ["02"]})


def test_engine_count_out_of_range_is_invalid() -> None:
    with pytest.raises(InvalidPowerSearchFitScenarioError):
        parse_power_search_fit_scenario({"power_engine_count": ["9"]})


def test_duplicate_engine_count_is_invalid() -> None:
    with pytest.raises(InvalidPowerSearchFitScenarioError):
        parse_power_search_fit_scenario({"power_engine_count": ["2", "3"]})
