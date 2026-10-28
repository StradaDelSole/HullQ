"""Unit tests for hullq.application.power_search_read — SLICE-0093.

Covers the Power-only request-state boundary purely at the decision-boundary
level: BASE / REDIRECT / INVALID never touch `conn` (passed as `None` here
to prove it), mirroring `tests/unit/test_search_read.py`'s identical
discipline. The RESULT path (which does need real persisted state) is
covered separately by
`tests/persistence/test_power_inventory_query_slice_0093.py`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from hullq.application.power_search_read import (
    PowerSearchOutcomeKind,
    build_canonical_power_search_path,
    evaluate_power_search_request,
)

_AS_OF = datetime(2026, 1, 1, tzinfo=UTC)


def test_base_state_zero_params_never_touches_conn() -> None:
    outcome = evaluate_power_search_request(None, locale="de", query_params={}, as_of=_AS_OF)
    assert outcome.kind is PowerSearchOutcomeKind.BASE
    assert outcome.canonical_path is None
    assert outcome.power_drive is None


def test_unknown_parameter_is_invalid() -> None:
    outcome = evaluate_power_search_request(
        None, locale="de", query_params={"foo": ["bar"]}, as_of=_AS_OF
    )
    assert outcome.kind is PowerSearchOutcomeKind.INVALID


def test_sail_key_is_invalid_on_power_surface() -> None:
    """Required Behavior §3: the Power parser never accepts a Sail key."""
    outcome = evaluate_power_search_request(
        None, locale="de", query_params={"draft_max": ["1.6"]}, as_of=_AS_OF
    )
    assert outcome.kind is PowerSearchOutcomeKind.INVALID


def test_unsupported_power_drive_value_is_invalid() -> None:
    outcome = evaluate_power_search_request(
        None, locale="de", query_params={"power_drive": ["DIESEL_ELECTRIC"]}, as_of=_AS_OF
    )
    assert outcome.kind is PowerSearchOutcomeKind.INVALID


def test_claim_only_vocabulary_mixed_other_unknown_are_invalid_filter_values() -> None:
    """MIXED/OTHER/UNKNOWN are real claim values but never public filter tokens."""
    for value in ("MIXED", "OTHER", "UNKNOWN"):
        outcome = evaluate_power_search_request(
            None, locale="de", query_params={"power_drive": [value]}, as_of=_AS_OF
        )
        assert outcome.kind is PowerSearchOutcomeKind.INVALID


def test_conflicting_duplicate_values_are_invalid() -> None:
    outcome = evaluate_power_search_request(
        None, locale="de", query_params={"power_drive": ["SHAFT", "POD"]}, as_of=_AS_OF
    )
    assert outcome.kind is PowerSearchOutcomeKind.INVALID


def test_equal_duplicate_values_collapse_via_redirect() -> None:
    outcome = evaluate_power_search_request(
        None, locale="de", query_params={"power_drive": ["SHAFT", "SHAFT"]}, as_of=_AS_OF
    )
    assert outcome.kind is PowerSearchOutcomeKind.REDIRECT
    assert outcome.canonical_path == "/de/power/search?power_drive=SHAFT"


def test_redirect_canonical_path_is_locale_prefixed() -> None:
    assert build_canonical_power_search_path("fr", power_drive="OUTBOARD") == (
        "/fr/power/search?power_drive=OUTBOARD"
    )
    assert build_canonical_power_search_path("fr", power_drive=None) == "/fr/power/search"


def test_empty_locale_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="locale"):
        evaluate_power_search_request(None, locale="", query_params={}, as_of=_AS_OF)
