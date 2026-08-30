"""Unit tests for scripts/search_demo_configuration_aware.py — SLICE-0035.

Confirms the local demonstration fixture set visibly exercises every case
required by slice In-scope item 11 (categorical confirmed match/non-match/
unknown; a design where only a shallow-draft configuration matches; a design
with one matching and one non-matching configuration; a genuinely
configuration-ambiguous design that remains insufficient; a mixed
categorical + numeric AND query) across the ten Q1-Q10 benchmark
operator/field-shape fixtures, that every loaded design-configuration set is
explicitly labeled a fixture, and that result distributions match the
deterministic truth table by hand-verified expectation.
"""

from __future__ import annotations

from hullq.search.types import ReasonCode, ResultClass
from scripts.search_demo_configuration_aware import (
    load_fixture_design_configuration_sets,
    load_fixture_queries,
    main,
)


def test_fixture_design_configuration_sets_are_all_labeled_fixtures() -> None:
    design_sets = load_fixture_design_configuration_sets()
    assert design_sets
    assert all(s.is_fixture for s in design_sets)


def test_fixture_queries_cover_all_ten_benchmark_shapes() -> None:
    queries = load_fixture_queries()
    query_ids = [q[0] for q in queries]
    assert query_ids == [f"Q{i}" for i in range(1, 11)]


def test_fixture_queries_roles_match_locked_benchmark_role_split() -> None:
    queries = load_fixture_queries()
    roles = {query_id: role for query_id, role, _description, _query in queries}
    assert roles["Q9"] == "SYSTEM_CHALLENGE"
    assert roles["Q10"] == "SYSTEM_CHALLENGE"
    for query_id in [f"Q{i}" for i in range(1, 9)]:
        assert roles[query_id] == "USER_INTENT"


def test_demo_produces_all_ten_query_outcomes() -> None:
    outcomes = main()
    assert set(outcomes) == {f"Q{i}" for i in range(1, 11)}


# ---------------------------------------------------------------------------
# Categorical confirmed match / non-match / unknown — Q4 (Masthead AND Draft<=1.80)
# ---------------------------------------------------------------------------


def test_q4_categorical_confirmed_match() -> None:
    outcome = main()["Q4"]
    match_ids = {e.design_id for e in outcome.confirmed_matches}
    assert "fx-design-01-broad-match" in match_ids


def test_q4_categorical_confirmed_non_match() -> None:
    outcome = main()["Q4"]
    non_match_ids = {e.design_id for e in outcome.confirmed_non_matches}
    assert non_match_ids == {"fx-design-02-rig-non-match"}


def test_q4_categorical_unknown_is_insufficient() -> None:
    outcome = main()["Q4"]
    insufficient = {e.design_id: e for e in outcome.insufficient_data}
    assert "fx-design-03-categorical-unknown" in insufficient


# ---------------------------------------------------------------------------
# Shallow-draft-only match — Q10 (Draft<=1.60m)
# ---------------------------------------------------------------------------


def test_q10_shallow_draft_option_is_the_only_matching_configuration() -> None:
    outcome = main()["Q10"]
    evaluation = next(
        e for e in outcome.confirmed_matches if e.design_id == "fx-design-04-shallow-draft-option"
    )
    assert evaluation.matching_configuration_ids == (
        "fx-design-04-shallow-draft-option::shallow-draft",
    )
    baseline_eval = next(
        ce
        for ce in evaluation.configuration_evaluations
        if ce.configuration_id == "fx-design-04-shallow-draft-option::baseline"
    )
    assert baseline_eval.truth.value == "FALSE"


# ---------------------------------------------------------------------------
# Matching and non-matching confirmed configurations coexist — Q8 (Cutter AND Skeg)
# ---------------------------------------------------------------------------


def test_q8_cutter_rig_option_matches_while_baseline_does_not() -> None:
    outcome = main()["Q8"]
    evaluation = next(
        e for e in outcome.confirmed_matches if e.design_id == "fx-design-05-cutter-rig-option"
    )
    assert evaluation.matching_configuration_ids == ("fx-design-05-cutter-rig-option::cutter-rig",)
    baseline_eval = next(
        ce
        for ce in evaluation.configuration_evaluations
        if ce.configuration_id == "fx-design-05-cutter-rig-option::baseline"
    )
    assert baseline_eval.truth.value == "FALSE"


# ---------------------------------------------------------------------------
# Genuinely configuration-ambiguous design remains insufficient — Q9 and Q3
# ---------------------------------------------------------------------------


def test_q9_ambiguous_design_is_insufficient_with_configuration_ambiguous_reason() -> None:
    outcome = main()["Q9"]
    evaluation = next(
        e
        for e in outcome.insufficient_data
        if e.design_id == "fx-design-06-ambiguous-configuration-space"
    )
    assert evaluation.reason is ReasonCode.CONFIGURATION_AMBIGUOUS


def test_q3_ambiguous_design_still_confirmed_match_when_known_baseline_already_qualifies() -> None:
    # An incomplete configuration space never blocks a match the known
    # baseline configuration already establishes.
    outcome = main()["Q3"]
    match_ids = {e.design_id for e in outcome.confirmed_matches}
    assert "fx-design-06-ambiguous-configuration-space" in match_ids


# ---------------------------------------------------------------------------
# Mixed categorical + numeric AND — Q5, Q9
# ---------------------------------------------------------------------------


def test_q5_mixed_categorical_and_numeric_query_produces_all_three_surfaces() -> None:
    outcome = main()["Q5"]
    assert outcome.confirmed_match_count > 0
    assert outcome.confirmed_non_match_count > 0
    assert outcome.insufficient_data_count > 0


# ---------------------------------------------------------------------------
# Primary-result-surface boundary
# ---------------------------------------------------------------------------


def test_no_query_outcome_double_counts_a_design_across_surfaces() -> None:
    outcomes = main()
    for outcome in outcomes.values():
        match_ids = {e.design_id for e in outcome.confirmed_matches}
        non_match_ids = {e.design_id for e in outcome.confirmed_non_matches}
        insufficient_ids = {e.design_id for e in outcome.insufficient_data}
        assert match_ids.isdisjoint(non_match_ids)
        assert match_ids.isdisjoint(insufficient_ids)
        assert non_match_ids.isdisjoint(insufficient_ids)


def test_every_evaluation_is_a_valid_result_class() -> None:
    outcomes = main()
    for outcome in outcomes.values():
        for evaluation in outcome.confirmed_matches:
            assert evaluation.result_class is ResultClass.CONFIRMED_MATCH
        for evaluation in outcome.confirmed_non_matches:
            assert evaluation.result_class is ResultClass.CONFIRMED_NON_MATCH
        for evaluation in outcome.insufficient_data:
            assert evaluation.result_class is ResultClass.INSUFFICIENT_DATA
