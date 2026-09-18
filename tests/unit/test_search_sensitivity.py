"""Unit tests for hullq.application.search_sensitivity — SLICE-0057.

Covers contract §11's validation boundary purely at the decision level: every
case here is rejected before any Search evaluation is attempted, so `conn` is
passed as `None` to prove these paths never touch it. The OK path (which
needs real persisted state and a real PostgreSQL connection for the coherent
`REPEATABLE READ` pair) is covered separately by
`tests/persistence/test_search_sensitivity_api.py`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from hullq.application.search_sensitivity import (
    SensitivityErrorKind,
    SensitivityOutcomeKind,
    evaluate_requirement_sensitivity,
)

_AS_OF = datetime(2026, 1, 1, tzinfo=UTC)


def test_unknown_current_key_is_invalid() -> None:
    outcome = evaluate_requirement_sensitivity(
        None,
        locale="en",
        current={"draft_max": "1.6", "foo": "bar"},
        changed_criterion="draft_max",
        changed_value="1.7",
        as_of=_AS_OF,
    )
    assert outcome.kind is SensitivityOutcomeKind.INVALID
    assert outcome.error is SensitivityErrorKind.UNKNOWN_CURRENT_KEY


def test_empty_current_is_invalid() -> None:
    outcome = evaluate_requirement_sensitivity(
        None,
        locale="en",
        current={},
        changed_criterion="draft_max",
        changed_value="1.7",
        as_of=_AS_OF,
    )
    assert outcome.kind is SensitivityOutcomeKind.INVALID
    assert outcome.error is SensitivityErrorKind.NO_ACTIVE_CRITERIA


def test_unsupported_changed_criterion_is_invalid() -> None:
    outcome = evaluate_requirement_sensitivity(
        None,
        locale="en",
        current={"draft_max": "1.6"},
        changed_criterion="loa_max",
        changed_value="10",
        as_of=_AS_OF,
    )
    assert outcome.kind is SensitivityOutcomeKind.INVALID
    assert outcome.error is SensitivityErrorKind.UNSUPPORTED_CHANGED_CRITERION


def test_changed_criterion_not_active_is_invalid() -> None:
    outcome = evaluate_requirement_sensitivity(
        None,
        locale="en",
        current={"draft_max": "1.6"},
        changed_criterion="keel_configuration",
        changed_value="FIN",
        as_of=_AS_OF,
    )
    assert outcome.kind is SensitivityOutcomeKind.INVALID
    assert outcome.error is SensitivityErrorKind.CHANGED_CRITERION_NOT_ACTIVE


def test_malformed_current_draft_max_is_invalid() -> None:
    outcome = evaluate_requirement_sensitivity(
        None,
        locale="en",
        current={"draft_max": "1e0"},
        changed_criterion="draft_max",
        changed_value="1.7",
        as_of=_AS_OF,
    )
    assert outcome.kind is SensitivityOutcomeKind.INVALID
    assert outcome.error is SensitivityErrorKind.INVALID_DRAFT_MAX


def test_malformed_current_keel_configuration_is_invalid() -> None:
    outcome = evaluate_requirement_sensitivity(
        None,
        locale="en",
        current={"keel_configuration": "LONG_KEEL"},
        changed_criterion="keel_configuration",
        changed_value="FIN",
        as_of=_AS_OF,
    )
    assert outcome.kind is SensitivityOutcomeKind.INVALID
    assert outcome.error is SensitivityErrorKind.INVALID_KEEL_CONFIGURATION


def test_malformed_changed_draft_max_is_invalid() -> None:
    outcome = evaluate_requirement_sensitivity(
        None,
        locale="en",
        current={"draft_max": "1.6"},
        changed_criterion="draft_max",
        changed_value="1e0",
        as_of=_AS_OF,
    )
    assert outcome.kind is SensitivityOutcomeKind.INVALID
    assert outcome.error is SensitivityErrorKind.INVALID_DRAFT_MAX


def test_unsupported_changed_keel_configuration_is_invalid() -> None:
    outcome = evaluate_requirement_sensitivity(
        None,
        locale="en",
        current={"keel_configuration": "FIN"},
        changed_criterion="keel_configuration",
        changed_value="LONG_KEEL",
        as_of=_AS_OF,
    )
    assert outcome.kind is SensitivityOutcomeKind.INVALID
    assert outcome.error is SensitivityErrorKind.INVALID_KEEL_CONFIGURATION


def test_mixed_current_preserves_untouched_criterion_validation() -> None:
    # A mixed current requirement with a malformed *unchanged* keel value
    # must still fail closed even though the buyer is only changing draft_max
    # (contract §11 applies to every current value, not only the changed one).
    outcome = evaluate_requirement_sensitivity(
        None,
        locale="en",
        current={"draft_max": "1.6", "keel_configuration": "LONG_KEEL"},
        changed_criterion="draft_max",
        changed_value="1.7",
        as_of=_AS_OF,
    )
    assert outcome.kind is SensitivityOutcomeKind.INVALID
    assert outcome.error is SensitivityErrorKind.INVALID_KEEL_CONFIGURATION
