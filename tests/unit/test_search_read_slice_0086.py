"""Unit tests for hullq.application.search_read — SLICE-0086 (hull_configuration/
cockpit_position/deck_saloon).

Mirrors `tests/unit/test_search_read_multicriteria.py`'s discipline exactly:
BASE/REDIRECT/INVALID never touch `conn` (passed as `None` here to prove it).
The RESULT path needing real persisted state is covered by
`tests/persistence/test_native_inventory_query_multicriteria.py`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from hullq.application.search_read import SearchOutcomeKind, evaluate_search_request

_AS_OF = datetime(2026, 1, 1, tzinfo=UTC)


def test_unsupported_hull_configuration_value_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="en", query_params={"hull_configuration": ["OTHER"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_unsupported_hull_configuration_unknown_claim_only_token_is_invalid() -> None:
    """`OTHER` is valid PhysicalBoat claim vocabulary but never a public
    Search filter value -- must fail closed, not be silently accepted."""
    outcome = evaluate_search_request(
        None, locale="en", query_params={"hull_configuration": ["UNKNOWN"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_conflicting_duplicate_hull_configuration_is_invalid() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"hull_configuration": ["MONOHULL", "CATAMARAN"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_duplicate_identical_hull_configuration_redirects() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"hull_configuration": ["CATAMARAN", "CATAMARAN"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/en/search?hull_configuration=CATAMARAN"


def test_unsupported_cockpit_position_value_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="en", query_params={"cockpit_position": ["OTHER"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_unsupported_deck_saloon_none_value_is_invalid() -> None:
    """`NONE` is a real claim value but never a public Search filter value
    in this slice -- must fail closed."""
    outcome = evaluate_search_request(
        None, locale="en", query_params={"deck_saloon": ["NONE"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_unsupported_deck_saloon_unknown_value_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="en", query_params={"deck_saloon": ["UNKNOWN"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_deck_saloon_and_hull_configuration_out_of_order_redirects() -> None:
    # Canonical order places deck_saloon before hull_configuration
    # (hullq.search.criteria_registry.CANONICAL_PARAM_KEY_ORDER); supplying
    # hull_configuration first is a non-canonical key order and must
    # redirect, never be evaluated as-is.
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"hull_configuration": ["CATAMARAN"], "deck_saloon": ["DECK_SALOON"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert (
        outcome.canonical_path == "/en/search?deck_saloon=DECK_SALOON&hull_configuration=CATAMARAN"
    )


def test_all_eight_keys_out_of_order_redirects_to_canonical_order() -> None:
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
        },
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == (
        "/en/search?cockpit_position=CENTER&deck_saloon=DECK_SALOON&draft_max=1.6"
        "&hull_configuration=CATAMARAN&keel_configuration=FIN&loa_max=15&loa_min=10"
        "&rudder_configuration=SKEG_HUNG"
    )


def test_unknown_query_param_key_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="en", query_params={"deck_layout": ["FLYBRIDGE"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_empty_query_is_base() -> None:
    outcome = evaluate_search_request(None, locale="en", query_params={}, as_of=_AS_OF)
    assert outcome.kind is SearchOutcomeKind.BASE
