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
        parse_search_fit_scenario({"displacement_kg": ["5000"]})


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


# ---------------------------------------------------------------------------
# SLICE-0086: hull_configuration / cockpit_position / deck_saloon
# ---------------------------------------------------------------------------


def test_hull_configuration_only_scenario_parses() -> None:
    scenario = parse_search_fit_scenario({"hull_configuration": ["CATAMARAN"]})
    assert scenario.hull_configuration == "CATAMARAN"
    assert scenario.cockpit_position is None
    assert scenario.deck_saloon is None


def test_unsupported_hull_configuration_value_is_invalid() -> None:
    # OTHER is a valid PhysicalBoat claim token but never an accepted public
    # Search-fit scenario value.
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"hull_configuration": ["OTHER"]})


def test_duplicate_hull_configuration_is_invalid() -> None:
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"hull_configuration": ["MONOHULL", "CATAMARAN"]})


def test_cockpit_position_only_scenario_parses() -> None:
    scenario = parse_search_fit_scenario({"cockpit_position": ["MULTIPLE"]})
    assert scenario.cockpit_position == "MULTIPLE"


def test_unsupported_cockpit_position_value_is_invalid() -> None:
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"cockpit_position": ["OTHER"]})


def test_deck_saloon_only_scenario_parses() -> None:
    scenario = parse_search_fit_scenario({"deck_saloon": ["PILOTHOUSE"]})
    assert scenario.deck_saloon == "PILOTHOUSE"


def test_unsupported_deck_saloon_none_value_is_invalid() -> None:
    # NONE is a real claim value but never a public Search-fit scenario value.
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"deck_saloon": ["NONE"]})


def test_duplicate_deck_saloon_is_invalid() -> None:
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"deck_saloon": ["DECK_SALOON", "PILOTHOUSE"]})


def test_all_eight_criteria_scenario_parses() -> None:
    scenario = parse_search_fit_scenario(
        {
            "draft_max": ["1.6"],
            "keel_configuration": ["FIN"],
            "loa_min": ["10"],
            "loa_max": ["15"],
            "rudder_configuration": ["SKEG_HUNG"],
            "hull_configuration": ["MONOHULL"],
            "cockpit_position": ["AFT"],
            "deck_saloon": ["DECK_SALOON"],
        }
    )
    assert scenario.draft_max == Decimal("1.6")
    assert scenario.keel_configuration == "FIN"
    assert scenario.loa_min == Decimal("10")
    assert scenario.loa_max == Decimal("15")
    assert scenario.rudder_configuration == "SKEG_HUNG"
    assert scenario.hull_configuration == "MONOHULL"
    assert scenario.cockpit_position == "AFT"
    assert scenario.deck_saloon == "DECK_SALOON"


# ---------------------------------------------------------------------------
# SLICE-0087: beam / hull_material
# ---------------------------------------------------------------------------


def test_beam_min_only_scenario_parses() -> None:
    scenario = parse_search_fit_scenario({"beam_min": ["3.2"]})
    assert scenario.beam_min == Decimal("3.2")
    assert scenario.beam_max is None
    assert scenario.hull_material is None


def test_beam_min_and_max_scenario_parses() -> None:
    scenario = parse_search_fit_scenario({"beam_min": ["3.2"], "beam_max": ["4.4"]})
    assert scenario.beam_min == Decimal("3.2")
    assert scenario.beam_max == Decimal("4.4")


def test_beam_min_greater_than_max_is_invalid() -> None:
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"beam_min": ["4.4"], "beam_max": ["3.2"]})


def test_noncanonical_beam_value_is_invalid() -> None:
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"beam_min": ["3.20"]})


def test_duplicate_beam_min_is_invalid() -> None:
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"beam_min": ["3.2", "3.5"]})


def test_hull_material_only_scenario_parses() -> None:
    scenario = parse_search_fit_scenario({"hull_material": ["GRP_FIBERGLASS"]})
    assert scenario.hull_material == "GRP_FIBERGLASS"


def test_unsupported_hull_material_value_is_invalid() -> None:
    # FERROCEMENT/OTHER remain valid PhysicalBoat claim tokens but are never
    # accepted public Search-fit scenario values.
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"hull_material": ["FERROCEMENT"]})
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"hull_material": ["OTHER"]})


def test_duplicate_hull_material_is_invalid() -> None:
    with pytest.raises(InvalidSearchFitScenarioError):
        parse_search_fit_scenario({"hull_material": ["STEEL", "WOOD"]})


def test_all_eleven_criteria_scenario_parses() -> None:
    scenario = parse_search_fit_scenario(
        {
            "draft_max": ["1.6"],
            "keel_configuration": ["FIN"],
            "loa_min": ["10"],
            "loa_max": ["15"],
            "rudder_configuration": ["SKEG_HUNG"],
            "hull_configuration": ["MONOHULL"],
            "cockpit_position": ["AFT"],
            "deck_saloon": ["DECK_SALOON"],
            "beam_min": ["3.2"],
            "beam_max": ["4.4"],
            "hull_material": ["WOOD"],
        }
    )
    assert scenario.beam_min == Decimal("3.2")
    assert scenario.beam_max == Decimal("4.4")
    assert scenario.hull_material == "WOOD"
