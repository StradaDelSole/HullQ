"""Unit tests for scripts/search_oceanis_30_1.py — SLICE-0037.

Confirms the retained real (non-fixture) BENETEAU Oceanis 30.1 projection
loads correctly, that the unchanged locked Q1-Q10 suite produces the exact
hand-verified real-evidence outcome distribution, that the one required
configuration-sensitive CONFIRMED_MATCH (Q10) identifies the exact shallow-
keel configuration and never the deep-keel or retractable-keel configuration,
and that missing/ambiguous facts in the retained projection cannot be
promoted to confirmed Search truth merely by loosely editing the artifact
(FALSE_CONFIRMED_RESULT = 0 adversarial coverage).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hullq.search.configuration import DesignConfigurationSet
from hullq.search.configuration_engine import run_configuration_query
from hullq.search.types import ReasonCode, ResultClass, TruthState
from hullq.search.values import ValueQualification
from scripts.search_oceanis_30_1 import (
    PROJECTION_PATH,
    QUERIES_FIXTURE,
    _categorical_field,
    _numeric_field,
    load_locked_queries,
    load_oceanis_30_1_configuration_set,
    main,
)

DEEP = "oceanis-30-1-deep-keel"
SHALLOW = "oceanis-30-1-shallow-keel"
RETRACTABLE = "oceanis-30-1-retractable-keel"


# ---------------------------------------------------------------------------
# Retained package / loader integrity
# ---------------------------------------------------------------------------


def test_projection_and_queries_fixtures_exist() -> None:
    assert PROJECTION_PATH.is_file()
    assert QUERIES_FIXTURE.is_file()


def test_loaded_configuration_set_is_real_not_fixture() -> None:
    config_set = load_oceanis_30_1_configuration_set()
    assert config_set.is_fixture is False
    assert config_set.design_id == "beneteau-oceanis-30-1"


def test_loaded_configuration_set_has_exactly_the_three_evidenced_configurations() -> None:
    config_set = load_oceanis_30_1_configuration_set()
    ids = {c.identity.configuration_id for c in config_set.configurations}
    assert ids == {DEEP, SHALLOW, RETRACTABLE}


def test_configuration_space_is_not_claimed_complete() -> None:
    config_set = load_oceanis_30_1_configuration_set()
    assert config_set.configuration_space_complete is False


def test_locked_queries_are_the_unchanged_q1_to_q10_shapes() -> None:
    queries = load_locked_queries()
    assert [q[0] for q in queries] == [f"Q{i}" for i in range(1, 11)]


# ---------------------------------------------------------------------------
# Real Q1-Q10 outcome distribution (hand-verified against the retained
# evidence in research/benchmark/waves/sl0037-oceanis-30-1/REPORT.md)
# ---------------------------------------------------------------------------

_EXPECTED_RESULT_CLASSES = {
    "Q1": ResultClass.CONFIRMED_MATCH,
    "Q2": ResultClass.CONFIRMED_MATCH,
    "Q3": ResultClass.INSUFFICIENT_DATA,
    "Q4": ResultClass.INSUFFICIENT_DATA,
    "Q5": ResultClass.INSUFFICIENT_DATA,
    "Q6": ResultClass.INSUFFICIENT_DATA,
    "Q7": ResultClass.INSUFFICIENT_DATA,
    "Q8": ResultClass.INSUFFICIENT_DATA,
    "Q9": ResultClass.INSUFFICIENT_DATA,
    "Q10": ResultClass.CONFIRMED_MATCH,
}


def test_real_q1_to_q10_outcome_distribution_matches_hand_verified_evidence() -> None:
    results = main()
    assert {qid: ev.result_class for qid, ev in results.items()} == _EXPECTED_RESULT_CLASSES


def test_no_query_returns_confirmed_non_match() -> None:
    # configuration_space_complete=False uniformly blocks CONFIRMED_NON_MATCH
    # for this retained package; this is expected, not a defect.
    results = main()
    assert all(ev.result_class is not ResultClass.CONFIRMED_NON_MATCH for ev in results.values())


def test_at_least_one_query_is_confirmed_match_from_real_data() -> None:
    results = main()
    assert any(ev.result_class is ResultClass.CONFIRMED_MATCH for ev in results.values())


# ---------------------------------------------------------------------------
# Required configuration-sensitive proof — Q10
# ---------------------------------------------------------------------------


def test_q10_configuration_sensitive_match_is_exactly_the_shallow_keel_configuration() -> None:
    results = main()
    q10 = results["Q10"]
    assert q10.result_class is ResultClass.CONFIRMED_MATCH
    assert q10.matching_configuration_ids == (SHALLOW,)

    deep_eval = next(ce for ce in q10.configuration_evaluations if ce.configuration_id == DEEP)
    retractable_eval = next(
        ce for ce in q10.configuration_evaluations if ce.configuration_id == RETRACTABLE
    )
    assert deep_eval.truth is TruthState.FALSE
    assert retractable_eval.truth is TruthState.UNKNOWN


def test_q1_is_also_a_genuine_configuration_sensitive_match() -> None:
    # Corroborates Q10: deep-keel FALSE, shallow-keel TRUE, on real draft
    # evidence, not a flattened design-wide value.
    results = main()
    q1 = results["Q1"]
    assert q1.matching_configuration_ids == (SHALLOW,)
    deep_eval = next(ce for ce in q1.configuration_evaluations if ce.configuration_id == DEEP)
    assert deep_eval.truth is TruthState.FALSE


# ---------------------------------------------------------------------------
# FALSE_CONFIRMED_RESULT = 0 adversarial coverage
# ---------------------------------------------------------------------------


def test_retractable_keel_missing_draft_is_never_true_or_false_across_all_draft_queries() -> None:
    results = main()
    for query_id in ("Q1", "Q2", "Q5", "Q7", "Q9", "Q10"):
        evaluation = results[query_id]
        retractable_eval = next(
            ce for ce in evaluation.configuration_evaluations if ce.configuration_id == RETRACTABLE
        )
        assert retractable_eval.truth is TruthState.UNKNOWN
        draft_criterion = next(
            c for c in retractable_eval.criterion_evaluations if c.field == "draft_max_m"
        )
        assert draft_criterion.truth is TruthState.UNKNOWN
        assert draft_criterion.reason is ReasonCode.VALUE_MISSING


def test_tampered_json_with_stray_value_alongside_unknown_state_does_not_leak() -> None:
    """Prove a loosely-tampered retained artifact cannot smuggle a value past
    the fail-closed ValueQualification boundary merely by adding a "value"
    key next to a non-resolved "state" -- the loader/values.py choke point
    must still discard it, exactly as it would for the real, untampered file.
    """
    tampered_numeric = _numeric_field({"state": "unknown", "value": 1.2})
    assert tampered_numeric.qualification is ValueQualification.MISSING
    assert tampered_numeric.value is None

    tampered_categorical = _categorical_field({"state": "unknown", "value": "aft"})
    assert tampered_categorical.qualification is ValueQualification.MISSING
    assert tampered_categorical.value is None


def test_forced_configuration_space_complete_still_cannot_manufacture_a_false_non_match() -> None:
    """Even a maliciously/carelessly tampered configuration_space_complete=True
    must not turn the genuinely UNKNOWN retractable-keel configuration into a
    confirmed non-match for Q10 -- the existing engine's own universal-FALSE
    requirement (not just the completeness flag) is what actually gates
    CONFIRMED_NON_MATCH, and this retained data never satisfies it.
    """
    real_config_set = load_oceanis_30_1_configuration_set()
    tampered_config_set = DesignConfigurationSet(
        design_id=real_config_set.design_id,
        configurations=real_config_set.configurations,
        configuration_space_complete=True,
        is_fixture=False,
    )
    queries = {q[0]: q[3] for q in load_locked_queries()}
    outcome = run_configuration_query(queries["Q10"], [tampered_config_set])
    evaluation = (
        outcome.confirmed_matches + outcome.confirmed_non_matches + outcome.insufficient_data
    )[0]
    # The shallow-keel configuration is a genuine TRUE, so this remains a
    # real CONFIRMED_MATCH either way -- tampering completeness cannot even
    # incidentally manufacture a *non*-match here.
    assert evaluation.result_class is ResultClass.CONFIRMED_MATCH
    assert evaluation.matching_configuration_ids == (SHALLOW,)


# ---------------------------------------------------------------------------
# Retained package content — evidence/MTE bookkeeping is present and honest
# ---------------------------------------------------------------------------


def test_retained_package_records_zero_materialized_derived_facts() -> None:
    payload = json.loads(Path(PROJECTION_PATH).read_text(encoding="utf-8"))
    assert payload["mte_classification"]["derived_facts_materialized"] == []


def test_retained_package_excludes_the_robots_txt_blocked_source_from_evidence() -> None:
    log_path = PROJECTION_PATH.parent / "source_retrieval_log.json"
    payload = json.loads(log_path.read_text(encoding="utf-8"))
    blocked = next(s for s in payload["sources"] if s["id"] == "SRC-4")
    assert blocked["used_as_positive_evidence"] is False
    assert blocked["sr_6_6_disposition"] == "EXCLUDED_robots_txt_disallow"


def test_every_evaluation_is_a_valid_result_class() -> None:
    results = main()
    for evaluation in results.values():
        assert evaluation.result_class in {
            ResultClass.CONFIRMED_MATCH,
            ResultClass.CONFIRMED_NON_MATCH,
            ResultClass.INSUFFICIENT_DATA,
        }


@pytest.mark.parametrize("query_id", [f"Q{i}" for i in range(1, 11)])
def test_every_confirmed_match_reports_at_least_one_matching_configuration_id(
    query_id: str,
) -> None:
    evaluation = main()[query_id]
    if evaluation.result_class is ResultClass.CONFIRMED_MATCH:
        assert len(evaluation.matching_configuration_ids) >= 1
    else:
        assert evaluation.matching_configuration_ids == ()
