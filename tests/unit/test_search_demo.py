"""Unit tests for scripts/search_demo.py — SLICE-0033.

Confirms the local demonstration fixture set visibly exercises all three
outcome classes (slice acceptance criterion), that every loaded projection
is explicitly labeled a fixture, and that the provisional/conflict fixture
designs never enter the confirmed-match set.
"""

from __future__ import annotations

from hullq.search.types import ResultClass
from scripts.search_demo import load_fixture_projections, main


def test_fixture_projections_are_all_labeled_fixtures() -> None:
    projections = load_fixture_projections()
    assert projections
    assert all(p.is_fixture for p in projections)


def test_demo_produces_all_three_outcome_classes() -> None:
    outcome = main()
    assert outcome.confirmed_match_count == 2
    assert outcome.confirmed_non_match_count == 1
    assert outcome.insufficient_data_count == 3


def test_demo_confirmed_matches_are_exactly_the_two_qualifying_fixtures() -> None:
    outcome = main()
    match_ids = {e.design_id for e in outcome.confirmed_matches}
    assert match_ids == {
        "fixture-design-001-confirmed-match",
        "fixture-design-002-confirmed-match-boundary",
    }


def test_demo_non_match_fixture_never_enters_confirmed_matches() -> None:
    outcome = main()
    match_ids = {e.design_id for e in outcome.confirmed_matches}
    assert "fixture-design-003-confirmed-non-match-loa" not in match_ids


def test_demo_missing_conflict_and_provisional_fixtures_are_insufficient_data() -> None:
    outcome = main()
    insufficient_ids = {e.design_id for e in outcome.insufficient_data}
    assert insufficient_ids == {
        "fixture-design-004-insufficient-data-missing",
        "fixture-design-005-insufficient-data-conflict",
        "fixture-design-006-insufficient-data-provisional",
    }
    match_ids = {e.design_id for e in outcome.confirmed_matches}
    assert insufficient_ids.isdisjoint(match_ids)


def test_result_classes_are_the_expected_enum_members() -> None:
    outcome = main()
    for evaluation in outcome.confirmed_matches:
        assert evaluation.result_class is ResultClass.CONFIRMED_MATCH
    for evaluation in outcome.confirmed_non_matches:
        assert evaluation.result_class is ResultClass.CONFIRMED_NON_MATCH
    for evaluation in outcome.insufficient_data:
        assert evaluation.result_class is ResultClass.INSUFFICIENT_DATA
