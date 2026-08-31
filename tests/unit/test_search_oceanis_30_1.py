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

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from hullq.search.configuration import DesignConfigurationSet
from hullq.search.configuration_engine import run_configuration_query
from hullq.search.types import ReasonCode, ResultClass, TruthState
from hullq.search.values import ValueQualification
from scripts.search_oceanis_30_1 import (
    PROJECTION_PATH,
    QUERIES_FIXTURE,
    OceanisProjectionAdmissionError,
    _categorical_field,
    _numeric_field,
    load_locked_queries,
    load_oceanis_30_1_configuration_set,
    main,
    validate_oceanis_30_1_projection,
)

DEEP = "oceanis-30-1-deep-keel"
SHALLOW = "oceanis-30-1-shallow-keel"
RETRACTABLE = "oceanis-30-1-retractable-keel"


def _real_payload() -> dict[str, Any]:
    """A fresh, independently-loaded, mutable copy of the retained JSON.

    Every admission-boundary test below starts from this genuinely-passing
    payload and mutates exactly one thing, so a failure always isolates the
    single tampered fact rather than some unrelated pre-existing defect.
    """
    return copy.deepcopy(json.loads(Path(PROJECTION_PATH).read_text(encoding="utf-8")))


def _configuration(payload: dict[str, Any], configuration_id: str) -> dict[str, Any]:
    return next(c for c in payload["configurations"] if c["configuration_id"] == configuration_id)


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
    """Supplementary engine-level check (kept alongside the direct admission-
    boundary test below, which is the actual proof of independence): even a
    tampered `DesignConfigurationSet.configuration_space_complete=True` must
    not turn the genuinely UNKNOWN retractable-keel configuration into a
    confirmed non-match for Q10 -- the existing engine's own universal-FALSE
    requirement (not just the completeness flag) is what actually gates
    CONFIRMED_NON_MATCH, and this retained data never satisfies it. This test
    exercises Q10 specifically, where a genuine TRUE (shallow-keel) already
    exists, so on its own it does NOT prove tampered completeness is
    rejected in general -- see
    `test_configuration_space_complete_true_is_rejected_before_admission`
    for that direct proof.
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
    assert evaluation.result_class is ResultClass.CONFIRMED_MATCH
    assert evaluation.matching_configuration_ids == (SHALLOW,)


# ---------------------------------------------------------------------------
# Independent retained-projection admission boundary — REVIEW amendment
# (review 5067543634): the retained JSON must not be able to self-authorize
# its own CONFIRMED state merely by being internally self-consistent. Every
# test below starts from the genuinely-passing retained payload and mutates
# exactly one fact, proving `validate_oceanis_30_1_projection` rejects it
# independently of whether the mutation would change any Q1-Q10 result.
# ---------------------------------------------------------------------------


def test_legitimate_retained_payload_passes_admission() -> None:
    validate_oceanis_30_1_projection(_real_payload())  # must not raise


def test_configuration_space_complete_true_is_rejected_before_admission() -> None:
    payload = _real_payload()
    payload["configuration_space_complete"] = True
    with pytest.raises(OceanisProjectionAdmissionError, match="configuration_space_complete"):
        validate_oceanis_30_1_projection(payload)


def test_shallow_draft_evidence_changed_to_src4_is_rejected() -> None:
    payload = _real_payload()
    _configuration(payload, SHALLOW)["numeric_fields"]["draft_max_m"]["evidence_refs"] = ["SRC-4"]
    with pytest.raises(OceanisProjectionAdmissionError, match="SRC-4"):
        validate_oceanis_30_1_projection(payload)


def test_shallow_draft_evidence_changed_to_bogus_source_is_rejected() -> None:
    payload = _real_payload()
    _configuration(payload, SHALLOW)["numeric_fields"]["draft_max_m"]["evidence_refs"] = ["BOGUS"]
    with pytest.raises(OceanisProjectionAdmissionError, match="BOGUS"):
        validate_oceanis_30_1_projection(payload)


def test_deep_draft_evidence_narrowed_to_an_allowed_but_insufficient_source_is_rejected() -> None:
    # SRC-1 is an allowed source in general, but the independently authorized
    # deep-keel draft fact requires SRC-6 specifically -- an allowed-but-
    # wrong source must still fail, not merely a blocklisted one.
    payload = _real_payload()
    _configuration(payload, DEEP)["numeric_fields"]["draft_max_m"]["evidence_refs"] = ["SRC-1"]
    with pytest.raises(OceanisProjectionAdmissionError, match="evidence_refs"):
        validate_oceanis_30_1_projection(payload)


def test_shallow_draft_value_changed_on_the_same_threshold_side_is_still_rejected() -> None:
    # 1.55 is still <=1.60 (same Q1/Q10 Search result as 1.30), but the
    # independent oracle must reject any value mismatch regardless.
    payload = _real_payload()
    _configuration(payload, SHALLOW)["numeric_fields"]["draft_max_m"]["value"] = 1.55
    with pytest.raises(OceanisProjectionAdmissionError, match="does not match"):
        validate_oceanis_30_1_projection(payload)


def test_loa_value_changed_to_another_still_matching_number_is_rejected() -> None:
    payload = _real_payload()
    _configuration(payload, DEEP)["numeric_fields"]["loa_m"]["value"] = 9.60
    with pytest.raises(OceanisProjectionAdmissionError, match="does not match"):
        validate_oceanis_30_1_projection(payload)


def test_extra_resolved_numeric_field_injected_is_rejected() -> None:
    payload = _real_payload()
    _configuration(payload, DEEP)["numeric_fields"]["displacement_kg"] = {
        "state": "resolved",
        "value": 4120.0,
        "evidence_refs": ["SRC-1"],
    }
    with pytest.raises(OceanisProjectionAdmissionError, match="displacement_kg"):
        validate_oceanis_30_1_projection(payload)


def test_extra_resolved_categorical_field_injected_is_rejected() -> None:
    payload = _real_payload()
    _configuration(payload, SHALLOW)["categorical_fields"]["deck.cockpit_position"] = {
        "state": "resolved",
        "value": "aft",
        "evidence_refs": ["SRC-1"],
    }
    with pytest.raises(OceanisProjectionAdmissionError, match="cockpit_position"):
        validate_oceanis_30_1_projection(payload)


def test_retractable_draft_injected_as_resolved_is_rejected() -> None:
    payload = _real_payload()
    _configuration(payload, RETRACTABLE)["numeric_fields"]["draft_max_m"] = {
        "state": "resolved",
        "value": 1.20,
        "evidence_refs": ["SRC-1"],
    }
    with pytest.raises(OceanisProjectionAdmissionError, match="draft_max_m"):
        validate_oceanis_30_1_projection(payload)


def test_configuration_id_altered_is_rejected() -> None:
    payload = _real_payload()
    _configuration(payload, DEEP)["configuration_id"] = "oceanis-30-1-deep-keel-v2"
    with pytest.raises(OceanisProjectionAdmissionError, match="configuration_id"):
        validate_oceanis_30_1_projection(payload)


def test_named_variant_id_altered_is_rejected() -> None:
    payload = _real_payload()
    _configuration(payload, DEEP)["named_variant_id"] = "deep-draft-keel-v2"
    with pytest.raises(OceanisProjectionAdmissionError, match="named_variant_id"):
        validate_oceanis_30_1_projection(payload)


def test_required_configuration_evidence_ref_removed_is_rejected() -> None:
    payload = _real_payload()
    _configuration(payload, SHALLOW)["configuration_evidence_refs"] = []
    with pytest.raises(OceanisProjectionAdmissionError):
        validate_oceanis_30_1_projection(payload)


def test_unexpected_fourth_configuration_is_rejected() -> None:
    payload = _real_payload()
    extra = copy.deepcopy(_configuration(payload, SHALLOW))
    extra["configuration_id"] = "oceanis-30-1-mystery-keel"
    payload["configurations"].append(extra)
    with pytest.raises(OceanisProjectionAdmissionError, match="mystery-keel"):
        validate_oceanis_30_1_projection(payload)


def test_missing_configuration_is_rejected() -> None:
    payload = _real_payload()
    payload["configurations"] = [
        c for c in payload["configurations"] if c["configuration_id"] != RETRACTABLE
    ]
    with pytest.raises(OceanisProjectionAdmissionError, match="configuration_id set"):
        validate_oceanis_30_1_projection(payload)


def test_design_id_altered_is_rejected() -> None:
    payload = _real_payload()
    payload["design_id"] = "beneteau-oceanis-30-1-v2"
    with pytest.raises(OceanisProjectionAdmissionError, match="design_id"):
        validate_oceanis_30_1_projection(payload)


def test_admission_runs_before_configuration_set_materialization() -> None:
    """The loader must fail closed at the JSON layer, not merely at
    `DesignConfigurationSet` construction -- corrupting the retained file on
    disk must make `load_oceanis_30_1_configuration_set` itself raise.
    """
    payload = _real_payload()
    payload["configuration_space_complete"] = True
    tampered_path = PROJECTION_PATH.parent / "_tampered_for_test.v1.json"
    tampered_path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        with pytest.raises(OceanisProjectionAdmissionError):
            load_oceanis_30_1_configuration_set(path=tampered_path)
    finally:
        tampered_path.unlink()


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


def _retrieval_log() -> dict[str, Any]:
    return json.loads(
        (PROJECTION_PATH.parent / "source_retrieval_log.json").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("source_id", ["SRC-1", "SRC-5", "SRC-6"])
def test_positive_evidence_sources_record_honest_automated_access_disposition(
    source_id: str,
) -> None:
    """REVIEW amendment (review 5067543634) point 2: automated access must be
    recorded honestly using the SOURCE_SCHEMA.v0.2 vocabulary, not glossed as
    "manual-style" -- every source actually used as positive evidence must
    carry a structured `rights.access.automated_access` disposition that is
    `conditional` (bounded/reviewed), never the unassessed default `unknown`
    and never an unqualified blanket `allowed`.
    """
    source = next(s for s in _retrieval_log()["sources"] if s["id"] == source_id)
    assert source["used_as_positive_evidence"] is True
    assert source["rights"]["access"]["automated_access"] == "conditional"
    assert source["rights"]["clearance"]["production_value"] == "conditional"


@pytest.mark.parametrize("source_id", ["SRC-1", "SRC-5", "SRC-6"])
def test_positive_evidence_sources_do_not_claim_bulk_or_recurring_clearance(
    source_id: str,
) -> None:
    source = next(s for s in _retrieval_log()["sources"] if s["id"] == source_id)
    clearance = source["rights"]["clearance"]
    assert clearance["bulk_bootstrap"] != "allowed"
    assert clearance["automated_ingestion"] != "allowed"


def test_beneteau_legal_notices_terms_surface_was_reviewed() -> None:
    log = _retrieval_log()
    src7 = next(s for s in log["sources"] if s["id"] == "SRC-7")
    assert src7["url"] == "https://www.beneteau.com/en-us/legal-notices"
    src1 = next(s for s in log["sources"] if s["id"] == "SRC-1")
    assert src1["rights"]["access"]["terms_url"] == "https://www.beneteau.com/en-us/legal-notices"
    assert src1["rights"]["access"]["terms_reviewed_at"] is not None


def test_finot_conq_terms_surface_bounded_check_is_recorded_not_silently_skipped() -> None:
    src6 = next(s for s in _retrieval_log()["sources"] if s["id"] == "SRC-6")
    assert "terms_page_search_result" in src6
    assert src6["rights"]["access"]["terms_url"] is None


def test_retrieval_ceiling_is_not_exceeded() -> None:
    log = _retrieval_log()
    assert log["semantic_retrievals_used"] == len(log["sources"])
    assert log["semantic_retrievals_used"] <= log["retrieval_ceiling"]


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
