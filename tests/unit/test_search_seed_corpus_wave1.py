"""Unit tests for scripts/search_seed_corpus_wave1.py — SLICE-0039.

Confirms the locked four-design Wave-1 cohort (BENETEAU Oceanis 30.1 reused
unchanged from SLICE-0037, plus real BAVARIA Cruiser 34 / Contessa 32 /
Lagoon 42 projections) is built entirely from real (`is_fixture=False`)
retained evidence, that Q1/Q2/Q10 are loaded unchanged and executed through
the existing `hullq.search.configuration_engine.run_configuration_query`
kernel, that the accepted Oceanis 30.1 Q10 regression still holds exactly,
that each new design's admission oracle fails closed under adversarial
tampering, and that the minimum 3/4 evaluability gate and
`FALSE_CONFIRMED_RESULT = 0` invariant both hold for the real evidence
actually admitted.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from hullq.search.configuration_engine import run_configuration_query
from hullq.search.types import TruthState
from scripts.search_seed_corpus_wave1 import (
    BAVARIA_PROJECTION_PATH,
    BAVARIA_SHOAL,
    BAVARIA_STANDARD,
    CONTESSA_BASELINE,
    CONTESSA_PROJECTION_PATH,
    LAGOON_PROJECTION_PATH,
    LAGOON_STANDARD,
    WAVE1_QUERY_IDS,
    SeedCorpusProjectionAdmissionError,
    load_bavaria_cruiser_34_configuration_set,
    load_contessa_32_configuration_set,
    load_lagoon_42_configuration_set,
    load_wave1_cohort,
    load_wave1_queries,
    main,
)

OCEANIS_DESIGN_ID = "beneteau-oceanis-30-1"
BAVARIA_DESIGN_ID = "bavaria-cruiser-34"
CONTESSA_DESIGN_ID = "contessa-32"
LAGOON_DESIGN_ID = "lagoon-42"

LOCKED_DESIGN_IDS = frozenset(
    {OCEANIS_DESIGN_ID, BAVARIA_DESIGN_ID, CONTESSA_DESIGN_ID, LAGOON_DESIGN_ID}
)


def _payload(path: Path) -> dict[str, Any]:
    return copy.deepcopy(json.loads(path.read_text(encoding="utf-8")))


def _configuration(payload: dict[str, Any], configuration_id: str) -> dict[str, Any]:
    return next(c for c in payload["configurations"] if c["configuration_id"] == configuration_id)


# ---------------------------------------------------------------------------
# Cohort composition
# ---------------------------------------------------------------------------


def test_cohort_contains_exactly_the_four_locked_wave1_designs() -> None:
    cohort = load_wave1_cohort()
    assert {c.design_id for c in cohort} == LOCKED_DESIGN_IDS
    assert len(cohort) == 4


def test_every_cohort_design_configuration_set_is_real_not_fixture() -> None:
    for config_set in load_wave1_cohort():
        assert config_set.is_fixture is False


def test_only_q1_q2_q10_are_loaded_for_this_wave() -> None:
    queries = load_wave1_queries()
    assert [q[0] for q in queries] == list(WAVE1_QUERY_IDS) == ["Q1", "Q2", "Q10"]


# ---------------------------------------------------------------------------
# Oceanis 30.1 — reused unchanged; Q10 regression
# ---------------------------------------------------------------------------


def test_oceanis_is_reused_unchanged_with_its_three_evidenced_configurations() -> None:
    cohort = load_wave1_cohort()
    oceanis = next(c for c in cohort if c.design_id == OCEANIS_DESIGN_ID)
    ids = {c.identity.configuration_id for c in oceanis.configurations}
    assert ids == {
        "oceanis-30-1-deep-keel",
        "oceanis-30-1-shallow-keel",
        "oceanis-30-1-retractable-keel",
    }
    assert oceanis.configuration_space_complete is False


def test_oceanis_q10_regression_confirmed_match_exact_shallow_keel_only() -> None:
    queries = {q[0]: q[3] for q in load_wave1_queries()}
    cohort = load_wave1_cohort()
    outcome = run_configuration_query(queries["Q10"], cohort)
    oceanis_eval = next(e for e in outcome.confirmed_matches if e.design_id == OCEANIS_DESIGN_ID)
    assert oceanis_eval.matching_configuration_ids == ("oceanis-30-1-shallow-keel",)
    deep_eval = next(
        ce
        for ce in oceanis_eval.configuration_evaluations
        if ce.configuration_id == "oceanis-30-1-deep-keel"
    )
    retractable_eval = next(
        ce
        for ce in oceanis_eval.configuration_evaluations
        if ce.configuration_id == "oceanis-30-1-retractable-keel"
    )
    assert deep_eval.truth is TruthState.FALSE
    assert retractable_eval.truth is TruthState.UNKNOWN


# ---------------------------------------------------------------------------
# Real Q1/Q2/Q10 outcome distribution for the three new designs
# ---------------------------------------------------------------------------


def test_bavaria_confirmed_match_on_q1_q2_q10_via_shoal_draft_option() -> None:
    queries = {q[0]: q[3] for q in load_wave1_queries()}
    cohort = load_wave1_cohort()
    for query_id in WAVE1_QUERY_IDS:
        outcome = run_configuration_query(queries[query_id], cohort)
        evaluation = next(e for e in outcome.confirmed_matches if e.design_id == BAVARIA_DESIGN_ID)
        assert evaluation.matching_configuration_ids == (BAVARIA_SHOAL,)
        standard_eval = next(
            ce
            for ce in evaluation.configuration_evaluations
            if ce.configuration_id == BAVARIA_STANDARD
        )
        assert standard_eval.truth is TruthState.FALSE


def test_contessa_insufficient_data_on_all_three_queries() -> None:
    queries = {q[0]: q[3] for q in load_wave1_queries()}
    cohort = load_wave1_cohort()
    for query_id in WAVE1_QUERY_IDS:
        outcome = run_configuration_query(queries[query_id], cohort)
        evaluation = next(e for e in outcome.insufficient_data if e.design_id == CONTESSA_DESIGN_ID)
        assert evaluation.matching_configuration_ids == ()
        config_eval = next(
            ce
            for ce in evaluation.configuration_evaluations
            if ce.configuration_id == CONTESSA_BASELINE
        )
        assert config_eval.truth is TruthState.UNKNOWN


def test_lagoon_confirmed_non_match_on_q1_and_q2_confirmed_match_on_q10() -> None:
    queries = {q[0]: q[3] for q in load_wave1_queries()}
    cohort = load_wave1_cohort()

    q1_outcome = run_configuration_query(queries["Q1"], cohort)
    lagoon_q1 = next(e for e in q1_outcome.confirmed_non_matches if e.design_id == LAGOON_DESIGN_ID)
    assert lagoon_q1.matching_configuration_ids == ()

    q2_outcome = run_configuration_query(queries["Q2"], cohort)
    lagoon_q2 = next(e for e in q2_outcome.confirmed_non_matches if e.design_id == LAGOON_DESIGN_ID)
    assert lagoon_q2.matching_configuration_ids == ()

    q10_outcome = run_configuration_query(queries["Q10"], cohort)
    lagoon_q10 = next(e for e in q10_outcome.confirmed_matches if e.design_id == LAGOON_DESIGN_ID)
    assert lagoon_q10.matching_configuration_ids == (LAGOON_STANDARD,)


# ---------------------------------------------------------------------------
# Result partition — every design exactly once per query
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("query_id", list(WAVE1_QUERY_IDS))
def test_every_design_appears_exactly_once_in_the_partition(query_id: str) -> None:
    queries = {q[0]: q[3] for q in load_wave1_queries()}
    cohort = load_wave1_cohort()
    outcome = run_configuration_query(queries[query_id], cohort)
    all_evaluations = (
        outcome.confirmed_matches + outcome.confirmed_non_matches + outcome.insufficient_data
    )
    design_ids = [e.design_id for e in all_evaluations]
    assert sorted(design_ids) == sorted(LOCKED_DESIGN_IDS)
    assert len(design_ids) == len(set(design_ids)) == 4


@pytest.mark.parametrize("query_id", list(WAVE1_QUERY_IDS))
def test_every_confirmed_match_identifies_at_least_one_matching_configuration(
    query_id: str,
) -> None:
    queries = {q[0]: q[3] for q in load_wave1_queries()}
    cohort = load_wave1_cohort()
    outcome = run_configuration_query(queries[query_id], cohort)
    for evaluation in outcome.confirmed_matches:
        assert len(evaluation.matching_configuration_ids) >= 1
    for evaluation in outcome.confirmed_non_matches + outcome.insufficient_data:
        assert evaluation.matching_configuration_ids == ()


# ---------------------------------------------------------------------------
# Minimum utility gate — 3/4 evaluability per query
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("query_id", list(WAVE1_QUERY_IDS))
def test_minimum_3_of_4_evaluability_gate(query_id: str) -> None:
    queries = {q[0]: q[3] for q in load_wave1_queries()}
    cohort = load_wave1_cohort()
    outcome = run_configuration_query(queries[query_id], cohort)
    evaluable = outcome.confirmed_match_count + outcome.confirmed_non_match_count
    assert evaluable >= 3


def test_false_confirmed_result_is_zero_across_the_locked_wave1_suite() -> None:
    """Independent expected-control check: every confirmed match/non-match
    above is cross-checked against the hand-verified evidence in REPORT.md.
    """
    queries = {q[0]: q[3] for q in load_wave1_queries()}
    cohort = load_wave1_cohort()

    expected_matches = {
        "Q1": {OCEANIS_DESIGN_ID, BAVARIA_DESIGN_ID},
        "Q2": {OCEANIS_DESIGN_ID, BAVARIA_DESIGN_ID},
        "Q10": {OCEANIS_DESIGN_ID, BAVARIA_DESIGN_ID, LAGOON_DESIGN_ID},
    }
    expected_non_matches = {
        "Q1": {LAGOON_DESIGN_ID},
        "Q2": {LAGOON_DESIGN_ID},
        "Q10": set(),
    }
    expected_insufficient = {
        "Q1": {CONTESSA_DESIGN_ID},
        "Q2": {CONTESSA_DESIGN_ID},
        "Q10": {CONTESSA_DESIGN_ID},
    }

    for query_id in WAVE1_QUERY_IDS:
        outcome = run_configuration_query(queries[query_id], cohort)
        assert {e.design_id for e in outcome.confirmed_matches} == expected_matches[query_id]
        assert {e.design_id for e in outcome.confirmed_non_matches} == expected_non_matches[
            query_id
        ]
        assert {e.design_id for e in outcome.insufficient_data} == expected_insufficient[query_id]


def test_owner_test_main_output_is_deterministic() -> None:
    first = main()
    second = main()
    for query_id in WAVE1_QUERY_IDS:
        first_ids = {e.design_id for e in first[query_id].confirmed_matches}
        second_ids = {e.design_id for e in second[query_id].confirmed_matches}
        assert first_ids == second_ids


# ---------------------------------------------------------------------------
# Bavaria Cruiser 34 admission-boundary adversarial coverage
# ---------------------------------------------------------------------------


def test_bavaria_legitimate_payload_loads() -> None:
    load_bavaria_cruiser_34_configuration_set()  # must not raise


def test_bavaria_design_id_tampered_is_rejected(tmp_path: Path) -> None:
    payload = _payload(BAVARIA_PROJECTION_PATH)
    payload["design_id"] = "bavaria-cruiser-34-v2"
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="design_id"):
        load_bavaria_cruiser_34_configuration_set(path=tampered)


def test_bavaria_standard_draft_value_tampered_is_rejected(tmp_path: Path) -> None:
    payload = _payload(BAVARIA_PROJECTION_PATH)
    _configuration(payload, BAVARIA_STANDARD)["numeric_fields"]["draft_max_m"]["value"] = 1.79
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="does not match"):
        load_bavaria_cruiser_34_configuration_set(path=tampered)


def test_bavaria_shoal_draft_configuration_id_tampered_is_rejected(tmp_path: Path) -> None:
    payload = _payload(BAVARIA_PROJECTION_PATH)
    _configuration(payload, BAVARIA_SHOAL)["configuration_id"] = "bavaria-cruiser-34-shoal-draft-v2"
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError):
        load_bavaria_cruiser_34_configuration_set(path=tampered)


def test_bavaria_scope_id_widened_is_rejected(tmp_path: Path) -> None:
    payload = _payload(BAVARIA_PROJECTION_PATH)
    _configuration(payload, BAVARIA_STANDARD)["numeric_fields"]["draft_max_m"]["scope_id"] = (
        "design_wide"
    )
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="scope_id"):
        load_bavaria_cruiser_34_configuration_set(path=tampered)


def test_bavaria_evidence_ref_replaced_with_bogus_source_is_rejected(tmp_path: Path) -> None:
    payload = _payload(BAVARIA_PROJECTION_PATH)
    _configuration(payload, BAVARIA_SHOAL)["numeric_fields"]["draft_max_m"]["evidence_refs"] = [
        "BOGUS"
    ]
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="BOGUS"):
        load_bavaria_cruiser_34_configuration_set(path=tampered)


def test_bavaria_configuration_space_complete_forced_true_is_rejected(tmp_path: Path) -> None:
    payload = _payload(BAVARIA_PROJECTION_PATH)
    payload["configuration_space_complete"] = True
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="configuration_space_complete"):
        load_bavaria_cruiser_34_configuration_set(path=tampered)


def test_bavaria_extra_unauthorized_field_injected_is_rejected(tmp_path: Path) -> None:
    payload = _payload(BAVARIA_PROJECTION_PATH)
    _configuration(payload, BAVARIA_STANDARD)["numeric_fields"]["displacement_kg"] = {
        "state": "resolved",
        "value": 5298.0,
        "evidence_refs": ["BAV-1"],
        "direct_or_derived": "direct",
        "scope_id": "design_wide",
    }
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="displacement_kg"):
        load_bavaria_cruiser_34_configuration_set(path=tampered)


def test_bavaria_missing_configuration_is_rejected(tmp_path: Path) -> None:
    payload = _payload(BAVARIA_PROJECTION_PATH)
    payload["configurations"] = [
        c for c in payload["configurations"] if c["configuration_id"] != BAVARIA_SHOAL
    ]
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="configuration_id set"):
        load_bavaria_cruiser_34_configuration_set(path=tampered)


def test_bavaria_applied_option_ids_nonempty_is_rejected(tmp_path: Path) -> None:
    payload = _payload(BAVARIA_PROJECTION_PATH)
    _configuration(payload, BAVARIA_STANDARD)["applied_option_ids"] = ["some-option"]
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="applied_option_ids"):
        load_bavaria_cruiser_34_configuration_set(path=tampered)


# ---------------------------------------------------------------------------
# Contessa 32 admission-boundary adversarial coverage — zero authorized
# facts means ANY injected field/value must be rejected outright.
# ---------------------------------------------------------------------------


def test_contessa_legitimate_payload_loads() -> None:
    config_set = load_contessa_32_configuration_set()
    assert config_set.is_fixture is False
    assert len(config_set.configurations) == 1
    projection = config_set.configurations[0].projection
    assert projection.get_numeric("loa_m").value is None


def test_contessa_design_id_tampered_is_rejected(tmp_path: Path) -> None:
    payload = _payload(CONTESSA_PROJECTION_PATH)
    payload["design_id"] = "contessa-32-v2"
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="design_id"):
        load_contessa_32_configuration_set(path=tampered)


def test_contessa_injected_loa_value_is_rejected_even_though_realistic(tmp_path: Path) -> None:
    """The retained JSON attempting to smuggle in a plausible, well-known
    real-world LOA value (9.75 m) must still fail admission: zero numeric
    facts are independently authorized for this design in this wave.
    """
    payload = _payload(CONTESSA_PROJECTION_PATH)
    _configuration(payload, CONTESSA_BASELINE)["numeric_fields"]["loa_m"] = {
        "state": "resolved",
        "value": 9.75,
        "evidence_refs": ["CON-1"],
        "direct_or_derived": "direct",
        "scope_id": "design_wide",
    }
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="loa_m"):
        load_contessa_32_configuration_set(path=tampered)


def test_contessa_injected_beam_and_draft_are_rejected(tmp_path: Path) -> None:
    payload = _payload(CONTESSA_PROJECTION_PATH)
    config = _configuration(payload, CONTESSA_BASELINE)
    config["numeric_fields"]["beam_m"] = {
        "state": "resolved",
        "value": 2.90,
        "evidence_refs": ["CON-1"],
        "direct_or_derived": "direct",
        "scope_id": "design_wide",
    }
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="beam_m"):
        load_contessa_32_configuration_set(path=tampered)


def test_contessa_configuration_evidence_refs_emptied_is_rejected(tmp_path: Path) -> None:
    payload = _payload(CONTESSA_PROJECTION_PATH)
    _configuration(payload, CONTESSA_BASELINE)["configuration_evidence_refs"] = []
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError):
        load_contessa_32_configuration_set(path=tampered)


def test_contessa_unexpected_second_configuration_is_rejected(tmp_path: Path) -> None:
    payload = _payload(CONTESSA_PROJECTION_PATH)
    extra = copy.deepcopy(_configuration(payload, CONTESSA_BASELINE))
    extra["configuration_id"] = "contessa-32-shoal-keel"
    payload["configurations"].append(extra)
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="shoal-keel"):
        load_contessa_32_configuration_set(path=tampered)


def test_contessa_configuration_space_complete_forced_true_is_rejected(tmp_path: Path) -> None:
    payload = _payload(CONTESSA_PROJECTION_PATH)
    payload["configuration_space_complete"] = True
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="configuration_space_complete"):
        load_contessa_32_configuration_set(path=tampered)


# ---------------------------------------------------------------------------
# Lagoon 42 admission-boundary adversarial coverage
# ---------------------------------------------------------------------------


def test_lagoon_legitimate_payload_loads() -> None:
    config_set = load_lagoon_42_configuration_set()
    assert config_set.is_fixture is False
    assert config_set.configuration_space_complete is True


def test_lagoon_design_id_tampered_is_rejected(tmp_path: Path) -> None:
    payload = _payload(LAGOON_PROJECTION_PATH)
    payload["design_id"] = "lagoon-42-v2"
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="design_id"):
        load_lagoon_42_configuration_set(path=tampered)


def test_lagoon_loa_value_tampered_to_still_out_of_range_number_is_rejected(
    tmp_path: Path,
) -> None:
    """13.50 is still outside the Q1/Q2 LOA ranges (same Search result as
    13.22), but the independent oracle must reject any value mismatch
    regardless of whether it would change the outcome.
    """
    payload = _payload(LAGOON_PROJECTION_PATH)
    _configuration(payload, LAGOON_STANDARD)["numeric_fields"]["loa_m"]["value"] = 13.50
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="does not match"):
        load_lagoon_42_configuration_set(path=tampered)


def test_lagoon_configuration_space_complete_forced_false_is_rejected(tmp_path: Path) -> None:
    """The independent oracle fixes this design's completeness determination
    in both directions -- a tampered downgrade to False must fail admission
    exactly like a tampered upgrade would for the other two designs.
    """
    payload = _payload(LAGOON_PROJECTION_PATH)
    payload["configuration_space_complete"] = False
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="configuration_space_complete"):
        load_lagoon_42_configuration_set(path=tampered)


def test_lagoon_draft_evidence_ref_replaced_with_bogus_source_is_rejected(tmp_path: Path) -> None:
    payload = _payload(LAGOON_PROJECTION_PATH)
    _configuration(payload, LAGOON_STANDARD)["numeric_fields"]["draft_max_m"]["evidence_refs"] = [
        "BOGUS"
    ]
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="BOGUS"):
        load_lagoon_42_configuration_set(path=tampered)


def test_lagoon_unexpected_second_configuration_is_rejected(tmp_path: Path) -> None:
    payload = _payload(LAGOON_PROJECTION_PATH)
    extra = copy.deepcopy(_configuration(payload, LAGOON_STANDARD))
    extra["configuration_id"] = "lagoon-42-shoal-daggerboard"
    payload["configurations"].append(extra)
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="shoal-daggerboard"):
        load_lagoon_42_configuration_set(path=tampered)


def test_lagoon_direct_or_derived_reclassified_as_derived_is_rejected(tmp_path: Path) -> None:
    payload = _payload(LAGOON_PROJECTION_PATH)
    _configuration(payload, LAGOON_STANDARD)["numeric_fields"]["draft_max_m"][
        "direct_or_derived"
    ] = "derived"
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SeedCorpusProjectionAdmissionError, match="direct_or_derived"):
        load_lagoon_42_configuration_set(path=tampered)


# ---------------------------------------------------------------------------
# Retained package content — evidence bookkeeping is present and honest
# ---------------------------------------------------------------------------


def _retrieval_log() -> dict[str, Any]:
    log_path = BAVARIA_PROJECTION_PATH.parent / "source_retrieval_log.json"
    return json.loads(log_path.read_text(encoding="utf-8"))


def test_retrieval_cap_not_exceeded_total_and_per_design() -> None:
    log = _retrieval_log()
    counts = log["external_evidence_surface_count"]
    assert counts["total"] <= log["retrieval_ceiling_total"]
    for design in ("bavaria-cruiser-34", "contessa-32", "lagoon-42"):
        assert counts[design] <= log["retrieval_ceiling_per_design"]


def test_no_sailboatdata_scrape_or_reference_aggregator_used_as_evidence() -> None:
    log = _retrieval_log()
    for source in log["sources"]:
        assert "sailboatdata" not in source["url"]
        if source.get("used_as_positive_evidence"):
            assert "wikipedia.org" not in source["url"]


@pytest.mark.parametrize("source_id", ["BAV-1", "LAG-1"])
def test_positive_evidence_sources_record_honest_automated_access_disposition(
    source_id: str,
) -> None:
    source = next(s for s in _retrieval_log()["sources"] if s["id"] == source_id)
    assert source["used_as_positive_evidence"] is True
    assert source["rights"]["access"]["automated_access"] == "conditional"
    assert source["rights"]["clearance"]["bulk_bootstrap"] != "allowed"
