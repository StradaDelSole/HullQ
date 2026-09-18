"""Unit tests for hullq.application.search_read — SLICE-0051.

Covers Required Behavior §1 (request-state separation) purely at the
decision-boundary level: BASE / REDIRECT / INVALID never touch `conn` (passed
as `None` here to prove it), so these tests need no PostgreSQL instance. The
RESULT path (which does need real persisted state) is covered separately by
`tests/persistence/test_inventory_search_draft_max_api.py`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from hullq.application.search_read import SearchOutcomeKind, evaluate_search_request

_AS_OF = datetime(2026, 1, 1, tzinfo=UTC)


def test_base_state_zero_params_never_touches_conn() -> None:
    outcome = evaluate_search_request(None, locale="de", query_params={}, as_of=_AS_OF)
    assert outcome.kind is SearchOutcomeKind.BASE
    assert outcome.canonical_path is None
    assert outcome.draft_max is None


def test_unknown_parameter_is_invalid_even_with_no_draft_max() -> None:
    outcome = evaluate_search_request(
        None, locale="de", query_params={"foo": ["bar"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_nonsemantic_allowlist_is_empty_utm_source_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="de", query_params={"utm_source": ["x"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_unknown_parameter_alongside_valid_draft_max_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="de", query_params={"draft_max": ["1.6"], "foo": ["bar"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_malformed_draft_max_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="de", query_params={"draft_max": ["1e0"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_empty_draft_max_value_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="de", query_params={"draft_max": [""]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_conflicting_duplicate_values_are_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="de", query_params={"draft_max": ["1.6", "1.7"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_equal_duplicate_values_collapse_via_redirect() -> None:
    outcome = evaluate_search_request(
        None, locale="de", query_params={"draft_max": ["1.6", "1.60"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/de/search?draft_max=1.6"


def test_noncanonical_single_value_redirects_to_canonical() -> None:
    outcome = evaluate_search_request(
        None, locale="de", query_params={"draft_max": ["1.600"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/de/search?draft_max=1.6"


def test_redirect_canonical_path_is_locale_prefixed() -> None:
    outcome = evaluate_search_request(
        None, locale="fr", query_params={"draft_max": ["10.000"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/fr/search?draft_max=10"


def test_canonical_single_value_proceeds_to_result(monkeypatch) -> None:
    import hullq.application.search_read as module

    sentinel_outcome = object()
    captured: dict[str, object] = {}

    def fake_evaluate(conn: object, draft_max: Decimal, *, as_of: datetime) -> object:
        captured["conn"] = conn
        captured["draft_max"] = draft_max
        captured["as_of"] = as_of
        return sentinel_outcome

    monkeypatch.setattr(module, "evaluate_draft_max_requirement", fake_evaluate)

    conn_marker = object()
    outcome = evaluate_search_request(
        conn_marker, locale="en", query_params={"draft_max": ["1.6"]}, as_of=_AS_OF
    )

    assert outcome.kind is SearchOutcomeKind.RESULT
    assert outcome.draft_max == Decimal("1.6")
    assert outcome.keel_configuration is None
    assert outcome.search_outcome is sentinel_outcome
    assert captured["conn"] is conn_marker
    assert captured["draft_max"] == Decimal("1.6")
    assert captured["as_of"] == _AS_OF


# ---------------------------------------------------------------------------
# SLICE-0055 keel_configuration criterion #2
# ---------------------------------------------------------------------------


def test_unsupported_keel_configuration_value_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="de", query_params={"keel_configuration": ["LONG_KEEL"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_empty_keel_configuration_value_is_invalid() -> None:
    outcome = evaluate_search_request(
        None, locale="de", query_params={"keel_configuration": [""]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_conflicting_keel_configuration_duplicates_are_invalid() -> None:
    outcome = evaluate_search_request(
        None,
        locale="de",
        query_params={"keel_configuration": ["FIN", "WING"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_duplicate_equal_keel_configuration_redirects_to_canonical_single_value() -> None:
    outcome = evaluate_search_request(
        None,
        locale="de",
        query_params={"keel_configuration": ["FIN", "FIN"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/de/search?keel_configuration=FIN"


def test_keel_configuration_alone_proceeds_to_result_via_native_inventory_funnel(
    monkeypatch,
) -> None:
    import hullq.application.search_read as module

    sentinel_outcome = object()
    captured: dict[str, object] = {}

    def fake_evaluate(
        conn: object, *, draft_max: Decimal | None, keel_configuration: str | None, as_of: datetime
    ) -> object:
        captured["conn"] = conn
        captured["draft_max"] = draft_max
        captured["keel_configuration"] = keel_configuration
        captured["as_of"] = as_of
        return sentinel_outcome

    monkeypatch.setattr(module, "evaluate_native_inventory_requirements", fake_evaluate)

    conn_marker = object()
    outcome = evaluate_search_request(
        conn_marker, locale="en", query_params={"keel_configuration": ["FIN"]}, as_of=_AS_OF
    )

    assert outcome.kind is SearchOutcomeKind.RESULT
    assert outcome.draft_max is None
    assert outcome.keel_configuration == "FIN"
    assert outcome.search_outcome is sentinel_outcome
    assert captured["conn"] is conn_marker
    assert captured["draft_max"] is None
    assert captured["keel_configuration"] == "FIN"
    assert captured["as_of"] == _AS_OF


def test_mixed_draft_and_keel_proceeds_to_result_via_native_inventory_funnel(
    monkeypatch,
) -> None:
    import hullq.application.search_read as module

    sentinel_outcome = object()
    captured: dict[str, object] = {}

    def fake_evaluate(
        conn: object, *, draft_max: Decimal | None, keel_configuration: str | None, as_of: datetime
    ) -> object:
        captured["draft_max"] = draft_max
        captured["keel_configuration"] = keel_configuration
        return sentinel_outcome

    monkeypatch.setattr(module, "evaluate_native_inventory_requirements", fake_evaluate)

    outcome = evaluate_search_request(
        object(),
        locale="en",
        query_params={"draft_max": ["1.6"], "keel_configuration": ["FIN"]},
        as_of=_AS_OF,
    )

    assert outcome.kind is SearchOutcomeKind.RESULT
    assert outcome.draft_max == Decimal("1.6")
    assert outcome.keel_configuration == "FIN"
    assert outcome.search_outcome is sentinel_outcome
    assert captured["draft_max"] == Decimal("1.6")
    assert captured["keel_configuration"] == "FIN"


def test_mixed_noncanonical_draft_redirects_preserving_canonical_keel() -> None:
    outcome = evaluate_search_request(
        None,
        locale="de",
        query_params={"draft_max": ["1.600"], "keel_configuration": ["FIN"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/de/search?draft_max=1.6&keel_configuration=FIN"


def test_mixed_request_with_invalid_keel_value_is_invalid_even_with_valid_draft() -> None:
    outcome = evaluate_search_request(
        None,
        locale="de",
        query_params={"draft_max": ["1.6"], "keel_configuration": ["NOT_A_KEEL"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


# ---------------------------------------------------------------------------
# SLICE-0056 independent review Finding 2: canonical parameter *order*
# (docs/OQ_018_SEARCH_PARAMETER_ORDERING_DECISION_2026-09-11.md,
# docs/OQ_018_SEARCH_NONCANONICAL_REDIRECT_DECISION_2026-09-11.md)
# ---------------------------------------------------------------------------


def test_canonical_mixed_order_remains_result(monkeypatch) -> None:
    import hullq.application.search_read as module

    sentinel_outcome = object()
    monkeypatch.setattr(
        module,
        "evaluate_native_inventory_requirements",
        lambda conn, *, draft_max, keel_configuration, as_of: sentinel_outcome,
    )

    # dict literal insertion order is itself the incoming raw key order here
    # -- draft_max before keel_configuration is already canonical.
    outcome = evaluate_search_request(
        object(),
        locale="en",
        query_params={"draft_max": ["1.6"], "keel_configuration": ["FIN"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.RESULT
    assert outcome.search_outcome is sentinel_outcome


def test_reversed_valid_mixed_order_redirects_to_canonical_order() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"keel_configuration": ["FIN"], "draft_max": ["1.6"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/en/search?draft_max=1.6&keel_configuration=FIN"


def test_reversed_order_plus_noncanonical_value_redirects_to_full_canonical() -> None:
    # Reversed key order AND a non-canonical draft_max numeral together must
    # still collapse to exactly one 308 to the fully canonical URL -- not two
    # separate corrections and not a 200.
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"keel_configuration": ["FIN"], "draft_max": ["1.600"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/en/search?draft_max=1.6&keel_configuration=FIN"


def test_reversed_order_with_invalid_keel_value_is_invalid_not_redirect() -> None:
    # INVALID precedence: a reversed-order request must not be redirected
    # merely because its order is also non-canonical when its content is
    # ambiguous/invalid.
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"keel_configuration": ["LONG_KEEL"], "draft_max": ["1.6"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_reversed_order_with_conflicting_duplicate_is_invalid_not_redirect() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"keel_configuration": ["FIN"], "draft_max": ["1.6", "1.7"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_reversed_order_with_unknown_parameter_is_invalid_not_redirect() -> None:
    outcome = evaluate_search_request(
        None,
        locale="en",
        query_params={"keel_configuration": ["FIN"], "draft_max": ["1.6"], "foo": ["bar"]},
        as_of=_AS_OF,
    )
    assert outcome.kind is SearchOutcomeKind.INVALID


def test_draft_only_single_key_order_is_unaffected(monkeypatch) -> None:
    import hullq.application.search_read as module

    monkeypatch.setattr(
        module, "evaluate_draft_max_requirement", lambda conn, draft_max, *, as_of: object()
    )
    outcome = evaluate_search_request(
        object(), locale="de", query_params={"draft_max": ["1.6"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.RESULT


def test_keel_only_single_key_order_is_unaffected(monkeypatch) -> None:
    import hullq.application.search_read as module

    monkeypatch.setattr(
        module,
        "evaluate_native_inventory_requirements",
        lambda conn, *, draft_max, keel_configuration, as_of: object(),
    )
    outcome = evaluate_search_request(
        object(), locale="en", query_params={"keel_configuration": ["FIN"]}, as_of=_AS_OF
    )
    assert outcome.kind is SearchOutcomeKind.RESULT
