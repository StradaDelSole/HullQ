"""Unit tests for hullq.application.search_read — SLICE-0051.

Covers Required Behavior §1 (request-state separation) purely at the
decision-boundary level: BASE / REDIRECT / INVALID never touch `conn` (passed
as `None` here to prove it), so these tests need no PostgreSQL instance. The
RESULT path (which does need real persisted state) is covered separately by
`tests/persistence/test_inventory_search_draft_max_api.py`.
"""

from __future__ import annotations

from decimal import Decimal

from hullq.application.search_read import SearchOutcomeKind, evaluate_search_request


def test_base_state_zero_params_never_touches_conn() -> None:
    outcome = evaluate_search_request(None, locale="de", query_params={})
    assert outcome.kind is SearchOutcomeKind.BASE
    assert outcome.canonical_path is None
    assert outcome.draft_max is None


def test_unknown_parameter_is_invalid_even_with_no_draft_max() -> None:
    outcome = evaluate_search_request(None, locale="de", query_params={"foo": ["bar"]})
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_nonsemantic_allowlist_is_empty_utm_source_is_invalid() -> None:
    outcome = evaluate_search_request(None, locale="de", query_params={"utm_source": ["x"]})
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_unknown_parameter_alongside_valid_draft_max_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="de", query_params={"draft_max": ["1.6"], "foo": ["bar"]}
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_malformed_draft_max_is_invalid() -> None:
    outcome = evaluate_search_request(None, locale="de", query_params={"draft_max": ["1e0"]})
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_empty_draft_max_value_is_invalid() -> None:
    outcome = evaluate_search_request(None, locale="de", query_params={"draft_max": [""]})
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_conflicting_duplicate_values_are_invalid() -> None:
    outcome = evaluate_search_request(None, locale="de", query_params={"draft_max": ["1.6", "1.7"]})
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_equal_duplicate_values_collapse_via_redirect() -> None:
    outcome = evaluate_search_request(
        None, locale="de", query_params={"draft_max": ["1.6", "1.60"]}
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/de/search?draft_max=1.6"


def test_noncanonical_single_value_redirects_to_canonical() -> None:
    outcome = evaluate_search_request(None, locale="de", query_params={"draft_max": ["1.600"]})
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/de/search?draft_max=1.6"


def test_redirect_canonical_path_is_locale_prefixed() -> None:
    outcome = evaluate_search_request(None, locale="fr", query_params={"draft_max": ["10.000"]})
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/fr/search?draft_max=10"


def test_canonical_single_value_proceeds_to_result(monkeypatch) -> None:
    import hullq.application.search_read as module

    sentinel_outcome = object()
    captured: dict[str, object] = {}

    def fake_evaluate(conn: object, draft_max: Decimal) -> object:
        captured["conn"] = conn
        captured["draft_max"] = draft_max
        return sentinel_outcome

    monkeypatch.setattr(module, "evaluate_draft_max_requirement", fake_evaluate)

    conn_marker = object()
    outcome = evaluate_search_request(conn_marker, locale="en", query_params={"draft_max": ["1.6"]})

    assert outcome.kind is SearchOutcomeKind.RESULT
    assert outcome.draft_max == Decimal("1.6")
    assert outcome.search_outcome is sentinel_outcome
    assert captured["conn"] is conn_marker
    assert captured["draft_max"] == Decimal("1.6")
