"""Unit tests for `hullq.application.broker_search_fit.parse_search_fit_scenario`
— SLICE-0084 (+ SLICE-0085 LOA/rudder extension).

Pure parsing/validation boundary tests, no PostgreSQL dependency -- mirrors
`tests/unit/test_search_read.py`'s discipline. The full authorized/owned
Search-fit evaluation (which needs real persisted state) is covered by
`tests/persistence/test_broker_search_fit_api.py`.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from hullq.application.broker_search_fit import (
    InvalidSearchFitScenarioError,
    parse_search_fit_scenario,
)


def test_empty_scenario_is_invalid() -> None:
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({})


def test_unknown_parameter_is_invalid() -> None:
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"beam_max": ["10"]})


def test_draft_max_and_keel_only_scenario_parses() -> None:
    scenario = parse_search_fit_scenario({"draft_max": ["1.6"], "keel_configuration": ["FIN"]})
    assert scenario.draft_max == Decimal("1.6")
    assert scenario.keel_configuration == "FIN"
    assert scenario.loa_min is None
    assert scenario.loa_max is None
    assert scenario.rudder_configuration is None


def test_loa_min_only_scenario_parses() -> None:
    scenario = parse_search_fit_scenario({"loa_min": ["10"]})
    assert scenario.loa_min == Decimal("10")
    assert scenario.loa_max is None


def test_loa_min_and_max_scenario_parses() -> None:
    scenario = parse_search_fit_scenario({"loa_min": ["10"], "loa_max": ["15"]})
    assert scenario.loa_min == Decimal("10")
    assert scenario.loa_max == Decimal("15")


def test_loa_min_greater_than_max_is_invalid() -> None:
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"loa_min": ["15"], "loa_max": ["10"]})


def test_noncanonical_loa_value_is_invalid() -> None:
    # Unlike the public canonical-URL surface, this private preview has no
    # redirect identity -- a non-canonical spelling fails closed directly.
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"loa_min": ["10.00"]})


def test_duplicate_loa_min_is_invalid() -> None:
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"loa_min": ["10", "11"]})


def test_rudder_configuration_only_scenario_parses() -> None:
    scenario = parse_search_fit_scenario({"rudder_configuration": ["SKEG_HUNG"]})
    assert scenario.rudder_configuration == "SKEG_HUNG"


def test_unsupported_rudder_configuration_value_is_invalid() -> None:
    # OTHER is a valid PhysicalBoat claim token but never an accepted public
    # Search-fit scenario value.
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"rudder_configuration": ["OTHER"]})


def test_duplicate_rudder_configuration_is_invalid() -> None:
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"rudder_configuration": ["SKEG_HUNG", "SPADE"]})


def test_all_five_criteria_scenario_parses() -> None:
    scenario = parse_search_fit_scenario(
        {
            "draft_max": ["1.6"],
            "keel_configuration": ["FIN"],
            "loa_min": ["10"],
            "loa_max": ["15"],
            "rudder_configuration": ["SKEG_HUNG"],
        }
    )
    assert scenario.draft_max == Decimal("1.6")
    assert scenario.keel_configuration == "FIN"
    assert scenario.loa_min == Decimal("10")
    assert scenario.loa_max == Decimal("15")
    assert scenario.rudder_configuration == "SKEG_HUNG"
