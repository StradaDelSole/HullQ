"""Unit tests for hullq.application.search_read — SLICE-0087 (beam/hull_material).

Mirrors `tests/unit/test_search_read_slice_0086.py`'s discipline exactly:
BASE/REDIRECT/INVALID never touch `conn` (passed as `None` here to prove it).
The RESULT path needing real persisted state is covered by
`tests/persistence/test_native_inventory_query_slice_0087.py`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from hullq.application.search_read import SearchOutcomeKind, evaluate_search_request

_AS_OF = datetime(2026, 1, 1, tzinfo=UTC)


def test_unsupported_hull_material_value_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="en", query_params={"hull_material": ["FERROCEMENT"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_unsupported_hull_material_other_token_is_invalid() -> None:
    """`OTHER`/`CARBON_COMPOSITE` are valid PhysicalBoat claim vocabulary but
    never a public Search filter value -- must fail closed, not be silently
    accepted."""
    outcome = evaluate_search_request(
        None, locale="en", query_params={"hull_material": ["OTHER"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID
    outcome2 = evaluate_search_request(
        None, locale="en", query_params={"hull_material": ["CARBON_COMPOSITE"]}, as_of=_AS_OF
    )
    assert outcome2.kind is SearchOutcomeKind.INVALID


def test_conflicting_duplicate_hull_material_is_invalid() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"hull_material": ["STEEL", "WOOD"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_duplicate_identical_hull_material_redirects() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"hull_material": ["WOOD", "WOOD"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/en/search?hull_material=WOOD"


def test_noncanonical_beam_min_redirects() -> None:
    outcome = evaluate_search_request(
        None, locale="en", query_params={"beam_min": ["3.200"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/en/search?beam_min=3.2"


def test_beam_min_greater_than_beam_max_is_invalid() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"beam_min": ["4.5"], "beam_max": ["3.2"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_beam_max_and_hull_material_out_of_order_redirects() -> None:
    # Canonical order places beam_max before hull_material
    # (hullq.search.criteria_registry.CANONICAL_PARAM_KEY_ORDER); supplying
    # hull_material first is a non-canonical key order and must redirect,
    # never be evaluated as-is.
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"hull_material": ["WOOD"], "beam_max": ["4.4"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/en/search?beam_max=4.4&hull_material=WOOD"


def test_all_eleven_keys_out_of_order_redirects_to_canonical_order() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={
            "rudder_configuration": ["SKEG_HUNG"],
            "loa_min": ["10"],
            "loa_max": ["15"],
            "keel_configuration": ["FIN"],
            "draft_max": ["1.6"],
            "hull_configuration": ["CATAMARAN"],
            "cockpit_position": ["CENTER"],
            "deck_saloon": ["DECK_SALOON"],
            "beam_min": ["3.2"],
            "beam_max": ["4.4"],
            "hull_material": ["WOOD"],
        },
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == (
        "/en/search?beam_max=4.4&beam_min=3.2&cockpit_position=CENTER&deck_saloon=DECK_SALOON"
        "&draft_max=1.6&hull_configuration=CATAMARAN&hull_material=WOOD&keel_configuration=FIN"
        "&loa_max=15&loa_min=10&rudder_configuration=SKEG_HUNG"
    )


def test_unknown_query_param_key_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="en", query_params={"hull_thickness": ["5"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_empty_query_is_base() -> None:
    outcome = evaluate_search_request(None, locale="en", query_params={}, as_of=_AS_OF)
    assert outcome.kind is SearchOutcomeKind.BASE
