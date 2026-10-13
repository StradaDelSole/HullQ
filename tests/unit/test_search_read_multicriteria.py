"""Unit tests for hullq.application.search_read — SLICE-0085 (LOA/rudder).

Mirrors `tests/unit/test_search_read.py`'s discipline exactly: BASE/
REDIRECT/INVALID never touch `conn` (passed as `None` here to prove it). The
RESULT path needing real persisted state is covered by
`tests/persistence/test_native_inventory_query.py`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from hullq.application.search_read import SearchOutcomeKind, evaluate_search_request

_AS_OF = datetime(2026, 1, 1, tzinfo=UTC)


def test_loa_min_and_max_noncanonical_order_redirects() -> None:
    # Canonical order is loa_max before loa_min
    # (hullq.search.criteria_registry.CANONICAL_PARAM_KEY_ORDER) -- supplying
    # loa_min first is a non-canonical key order and must redirect, never be
    # evaluated as-is.
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"loa_min": ["10"], "loa_max": ["15"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/en/search?loa_max=15&loa_min=10"


def test_noncanonical_loa_value_redirects() -> None:
    outcome = evaluate_search_request(
        None, locale="en", query_params={"loa_min": ["10.00"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/en/search?loa_min=10"


def test_malformed_loa_min_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="en", query_params={"loa_min": ["1e0"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_loa_min_greater_than_loa_max_is_invalid() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"loa_min": ["15"], "loa_max": ["10"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_conflicting_duplicate_loa_min_is_invalid() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"loa_min": ["10", "11"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_unsupported_rudder_configuration_value_is_invalid() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"rudder_configuration": ["LONG_KEEL"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_conflicting_duplicate_rudder_configuration_is_invalid() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"rudder_configuration": ["SKEG_HUNG", "SPADE"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_duplicate_identical_rudder_configuration_redirects() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"rudder_configuration": ["SKEG_HUNG", "SKEG_HUNG"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/en/search?rudder_configuration=SKEG_HUNG"


def test_five_keys_out_of_order_redirects_to_canonical_order() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={
            "rudder_configuration": ["SKEG_HUNG"],
            "loa_min": ["10"],
            "loa_max": ["15"],
            "keel_configuration": ["FIN"],
            "draft_max": ["1.6"],
        },
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == (
        "/en/search?draft_max=1.6&keel_configuration=FIN&loa_max=15&loa_min=10"
        "&rudder_configuration=SKEG_HUNG"
    )
