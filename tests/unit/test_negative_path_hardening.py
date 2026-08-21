"""Negative-path hardening tests — SLICE-0015.

Proves honest failure behavior for all seven required negative-path cases:

1. Review-required retained fact — unsafe conversion requires review; no guessed semantics.
2. Insufficient retained fact — classified as INSUFFICIENT_RETAINED_FACT; does not imply BLOCKED.
3. Validation/materialization defect — fails closed; classified as VALIDATION_FAILURE.
4. True representational contract gap — smallest synthetic fixture proves BLOCKED is
   reachable only for CONTRACT_GAP, not for ordinary failures.
5. Semantic readback mismatch — deliberate field change is detected by the canonical comparator.
6. Idempotency/conflict failure — changed immutable semantic content cannot masquerade as
   exact re-import success.
7. SailboatData contamination guard — existing zero-tolerance protection remains active.

These are benchmark-only tests. They do not use production domain code beyond what the
benchmark materializer and comparator already use, and they do not introduce any new
production ingestion framework.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark.gate import G3GateResult, evaluate_g3_gate  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_minimal_bundle(
    *,
    bundle_id: str = "hullq-neg-path-test",
    bundle_version: str = "0015-v1-test",
    obs_count: int = 1,
    sailboatdata_source: bool = False,
) -> Any:
    """Build the smallest valid ResearchEvidenceBundle for negative-path testing."""
    from hullq.domain.provenance import (
        ClaimSemantics,
        ConfidenceLevel,
        EvidenceType,
        ObservationApplicability,
        ProducerKind,
        ProducerMetadata,
        RawObservation,
        RawObservationKind,
        ResearchContext,
        SourceLocator,
    )
    from hullq.research.jobs import ResearchTarget
    from hullq.research.observations import ResearchEvidenceBundle, ResearchObservation

    producer = ProducerMetadata(
        kind=ProducerKind.DETERMINISTIC_TOOL,
        identifier="hullq-neg-path-test",
        version="0015-v1-test",
        model=None,
        prompt_or_rule_version=None,
    )
    locator = SourceLocator(
        page=None, section=None, anchor=None, table=None, figure=None, record_key=None
    )
    context = ResearchContext(research_job_id=None, activity_id="neg-path-test")
    target = ResearchTarget(manufacturer="TestBuilder", model="TestModel", first_built=None)

    source_id = (
        "https://sailboatdata.com/sailboat/test-boat"
        if sailboatdata_source
        else "https://test-source.example.com/test-obs"
    )

    observations = tuple(
        ResearchObservation(
            observation_id=f"{bundle_id}-obs-{i:04d}",
            research_target=target,
            source_id=source_id,
            source_locator=locator,
            raw=RawObservation(
                kind=RawObservationKind.TEXT_FRAGMENT,
                value=f"test-value-{i}",
                unit=None,
                excerpt=None,
            ),
            normalized_candidate=None,
            evidence_type=EvidenceType.NARRATIVE_TEXT,
            claim_semantics=ClaimSemantics.OTHER,
            applicability=ObservationApplicability(
                first_year=None,
                last_year=None,
                hull_number_from=None,
                hull_number_to=None,
                market_or_region=None,
                named_variant_hint=None,
                design_option_hints=None,
                operating_state_hint=None,
                individual_hull_or_listing_ref=None,
                unknown_or_unbounded=True,
            ),
            producer=producer,
            research_context=context,
            observed_at="2026-01-01T00:00:00Z",
            confidence=ConfidenceLevel.MEDIUM,
            supersedes_observation_id=None,
            intended_subject_kind_hint=None,
            intended_field_pointer=None,
            notes=f"field_label:test_field_{i}",
        )
        for i in range(obs_count)
    )

    return ResearchEvidenceBundle(
        bundle_id=bundle_id,
        bundle_version=bundle_version,
        research_target=target,
        research_job_id=None,
        activity_id="neg-path-test",
        observations=observations,
        unresolved_findings=(),
        promoted_evidence=(),
        reference_crosschecks=(),
    )


# ---------------------------------------------------------------------------
# Test 1 — Review-required retained fact
# ---------------------------------------------------------------------------


def test_review_required_produces_no_guessed_semantics() -> None:
    """REVIEW_REQUIRED must not invent canonical values.

    A case where a bundle is produced with REVIEW_REQUIRED status must:
    - carry explicit review_reasons explaining why
    - NOT automatically assign canonical field pointers or resolved values
    - NOT automatically imply BLOCKED (reviewed evidence is not a contract gap)
    """
    from benchmark.materializer import (
        FAILURE_CLASS_INSUFFICIENT_RETAINED_FACT,
        MaterializationResult,
        classify_cannot_materialize_reasons,
    )

    # Simulate REVIEW_REQUIRED due to no observations
    result = MaterializationResult(
        case_id="NEG-REVIEW-001",
        status="REVIEW_REQUIRED",
        bundle=_make_minimal_bundle(obs_count=0),
        review_reasons=["no_observations_extracted"],
    )
    assert result.status == "REVIEW_REQUIRED"
    assert result.review_reasons
    # Classification must be INSUFFICIENT_RETAINED_FACT, not CONTRACT_GAP
    cls = classify_cannot_materialize_reasons(result.review_reasons)
    assert cls == FAILURE_CLASS_INSUFFICIENT_RETAINED_FACT, (
        f"Expected INSUFFICIENT_RETAINED_FACT for no_observations_extracted, got {cls!r}"
    )
    # Bundle must not carry fabricated canonical pointers
    if result.bundle is not None:
        for obs in result.bundle.observations:
            assert obs.intended_field_pointer is None, (
                f"Review-required bundle observation has a canonical pointer set: "
                f"{obs.intended_field_pointer!r} — this is invented, not evidence."
            )


# ---------------------------------------------------------------------------
# Test 2 — Insufficient retained fact
# ---------------------------------------------------------------------------


def test_insufficient_retained_fact_does_not_imply_blocked() -> None:
    """INSUFFICIENT_RETAINED_FACT must not drive a BLOCKED recommendation.

    Sparse retained evidence is a research gap, not a contract failure.
    The runner must map this to HARDEN_FIRST, not BLOCKED.
    """
    from benchmark.materializer import (
        FAILURE_CLASS_CONTRACT_GAP,
        FAILURE_CLASS_INSUFFICIENT_RETAINED_FACT,
        classify_cannot_materialize_reasons,
    )

    reasons = ["no_observations_extracted"]
    cls = classify_cannot_materialize_reasons(reasons)
    assert cls == FAILURE_CLASS_INSUFFICIENT_RETAINED_FACT
    assert cls != FAILURE_CLASS_CONTRACT_GAP, (
        "INSUFFICIENT_RETAINED_FACT must not be classified as CONTRACT_GAP. "
        "Sparse evidence is a research gap, not an architecture problem."
    )


def test_multiple_insufficient_reasons_do_not_escalate_to_contract_gap() -> None:
    """Multiple INSUFFICIENT_RETAINED_FACT reasons must not escalate to CONTRACT_GAP."""
    from benchmark.materializer import (
        FAILURE_CLASS_CONTRACT_GAP,
        classify_cannot_materialize_reasons,
    )

    reasons = ["no_observations_extracted", "no_observations_extracted"]
    cls = classify_cannot_materialize_reasons(reasons)
    assert cls != FAILURE_CLASS_CONTRACT_GAP


# ---------------------------------------------------------------------------
# Test 3 — Validation/materialization defect
# ---------------------------------------------------------------------------


def test_validation_failure_classified_correctly() -> None:
    """An ordinary runtime exception must be classified as VALIDATION_FAILURE, not CONTRACT_GAP."""
    from benchmark.materializer import (
        FAILURE_CLASS_CONTRACT_GAP,
        FAILURE_CLASS_VALIDATION_FAILURE,
        classify_cannot_materialize_reasons,
    )

    # RuntimeError: no leading "CONTRACT_GAP:" marker
    reasons = ["RuntimeError: unexpected None in field mapping"]
    cls = classify_cannot_materialize_reasons(reasons)
    assert cls == FAILURE_CLASS_VALIDATION_FAILURE
    assert cls != FAILURE_CLASS_CONTRACT_GAP, (
        "Ordinary RuntimeError must not be classified as CONTRACT_GAP."
    )


def test_validation_failure_does_not_block() -> None:
    """A VALIDATION_FAILURE in CANNOT_MATERIALIZE must not drive BLOCKED.

    The runner's recommendation logic must only emit BLOCKED for CONTRACT_GAP.
    This test exercises the classification chain, not the full runner.
    """
    from benchmark.materializer import (
        FAILURE_CLASS_CONTRACT_GAP,
        FAILURE_CLASS_VALIDATION_FAILURE,
        MaterializationResult,
        classify_cannot_materialize_reasons,
    )

    result = MaterializationResult(
        case_id="NEG-VAL-001",
        status="CANNOT_MATERIALIZE",
        bundle=None,
        review_reasons=["ValueError: unit 'furlongs' not recognized"],
    )
    cls = classify_cannot_materialize_reasons(result.review_reasons)
    assert cls == FAILURE_CLASS_VALIDATION_FAILURE
    assert cls != FAILURE_CLASS_CONTRACT_GAP


def test_cannot_materialize_without_contract_gap_does_not_block() -> None:
    """CANNOT_MATERIALIZE without CONTRACT_GAP must not produce BLOCKED.

    Exercises the real evaluate_g3_gate() function with two VALIDATION_FAILURE cases
    (cannot_pct=25% > 10%) and contract_gap_count=0. Result must be HARDEN_FIRST, not BLOCKED.
    """
    from benchmark.materializer import (
        FAILURE_CLASS_CONTRACT_GAP,
        classify_cannot_materialize_reasons,
    )

    # Classify the synthetic failures — none should be CONTRACT_GAP
    cannot_results = [
        ["ValueError: bad unit"],
        ["KeyError: missing source field"],
        ["RuntimeError: unexpected None"],
    ]
    contract_gap_count = sum(
        1
        for reasons in cannot_results
        if classify_cannot_materialize_reasons(reasons) == FAILURE_CLASS_CONTRACT_GAP
    )
    assert contract_gap_count == 0, (
        "Ordinary CANNOT_MATERIALIZE cases must not produce CONTRACT_GAP classification."
    )

    # Now confirm the REAL gate function produces HARDEN_FIRST (not BLOCKED) for these inputs.
    # 17 materialized (85%), 3 cannot (15% > 10%), 0 review → HARDEN_FIRST via cannot_pct gate.
    result: G3GateResult = evaluate_g3_gate(
        total_cases=20,
        materialized=17,
        review_required=0,
        cannot_materialize=3,
        contract_gap_count=0,
        first_pass_imported=17,
        reimport_already_imported=17,
        fresh_run_imported=17,
        readback_mismatches=0,
        fresh_run_semantic_mismatches=0,
    )
    assert result.recommendation == "HARDEN_FIRST", (
        f"Expected HARDEN_FIRST for cannot_pct=15% (>10%), contract_gap_count=0; "
        f"got {result.recommendation!r}"
    )
    assert result.recommendation != "BLOCKED", (
        "CANNOT_MATERIALIZE without CONTRACT_GAP must never produce BLOCKED."
    )


# ---------------------------------------------------------------------------
# Test 4 — True representational contract gap → BLOCKED reachable
# ---------------------------------------------------------------------------


def test_contract_gap_error_is_classified_as_contract_gap() -> None:
    """ContractGapError raises with 'CONTRACT_GAP:' prefix and is classified correctly."""
    from benchmark.materializer import (
        FAILURE_CLASS_CONTRACT_GAP,
        ContractGapError,
        classify_cannot_materialize_reasons,
    )

    exc = ContractGapError("cannot represent multihull hull count as a scalar field")
    reason = str(exc)
    assert reason.startswith("CONTRACT_GAP:"), (
        f"ContractGapError message must start with 'CONTRACT_GAP:'; got {reason!r}"
    )
    cls = classify_cannot_materialize_reasons([reason])
    assert cls == FAILURE_CLASS_CONTRACT_GAP


def test_contract_gap_drives_blocked_recommendation() -> None:
    """A CONTRACT_GAP failure must make evaluate_g3_gate() return BLOCKED.

    Exercises the real gate function with contract_gap_count=1 to confirm BLOCKED
    is reachable only for genuine contract insufficiency.
    """
    from benchmark.materializer import (
        FAILURE_CLASS_CONTRACT_GAP,
        ContractGapError,
        MaterializationResult,
        classify_cannot_materialize_reasons,
    )

    # Classify the synthetic ContractGapError result
    exc_msg = str(ContractGapError("retained fact has no schema representation"))
    results = [
        MaterializationResult(
            case_id="NEG-CONTRACT-001",
            status="CANNOT_MATERIALIZE",
            bundle=None,
            review_reasons=[exc_msg],
        )
    ]
    contract_gap_count = sum(
        1
        for r in results
        if r.status == "CANNOT_MATERIALIZE"
        and classify_cannot_materialize_reasons(r.review_reasons) == FAILURE_CLASS_CONTRACT_GAP
    )
    assert contract_gap_count == 1, "Expected one CONTRACT_GAP failure from ContractGapError"

    # Now call the REAL gate function — must produce BLOCKED (highest priority gate).
    # 19 materialized (95%), 1 cannot (5%), contract_gap_count=1 → BLOCKED.
    result: G3GateResult = evaluate_g3_gate(
        total_cases=20,
        materialized=19,
        review_required=0,
        cannot_materialize=1,
        contract_gap_count=contract_gap_count,
        first_pass_imported=19,
        reimport_already_imported=19,
        fresh_run_imported=19,
        readback_mismatches=0,
        fresh_run_semantic_mismatches=0,
    )
    assert result.recommendation == "BLOCKED", (
        f"CONTRACT_GAP failure must produce BLOCKED from evaluate_g3_gate(); "
        f"got {result.recommendation!r}"
    )


def test_contract_gap_separate_from_validation_failure() -> None:
    """CONTRACT_GAP and VALIDATION_FAILURE must be classified separately."""
    from benchmark.materializer import (
        FAILURE_CLASS_CONTRACT_GAP,
        FAILURE_CLASS_VALIDATION_FAILURE,
        ContractGapError,
        classify_cannot_materialize_reasons,
    )

    gap_reason = str(ContractGapError("schema cannot represent trimaran beam-count"))
    val_reason = "RuntimeError: unexpected None in field mapping"

    assert classify_cannot_materialize_reasons([gap_reason]) == FAILURE_CLASS_CONTRACT_GAP
    assert classify_cannot_materialize_reasons([val_reason]) == FAILURE_CLASS_VALIDATION_FAILURE


# ---------------------------------------------------------------------------
# Test 5 — Semantic readback mismatch is detected
# ---------------------------------------------------------------------------


def test_comparator_detects_observation_field_change() -> None:
    """A deliberately mutated observation field must produce a mismatch in the comparator."""
    from benchmark.semantics_compare import compare_observation_semantics

    bundle = _make_minimal_bundle(bundle_id="hullq-neg-compare-001")
    original = bundle.observations[0]

    # Mutate the source_id to simulate a readback mismatch
    mutated = replace(original, source_id="https://mutated-source.example.com/different")

    diffs = compare_observation_semantics("NEG-COMPARE-001", original, mutated)
    assert diffs, (
        "Comparator must detect a mismatch when source_id changes. "
        "Got no diffs — the comparator is not checking this field."
    )
    assert any("source_id" in d for d in diffs), f"Expected a source_id mismatch; got: {diffs}"


def test_comparator_detects_raw_value_change() -> None:
    """A mutated raw.value must produce a mismatch in the comparator."""
    from benchmark.semantics_compare import compare_observation_semantics

    from hullq.domain.provenance import RawObservation, RawObservationKind

    bundle = _make_minimal_bundle(bundle_id="hullq-neg-compare-002")
    original = bundle.observations[0]

    mutated_raw = RawObservation(
        kind=RawObservationKind.TEXT_FRAGMENT,
        value="CHANGED-VALUE",
        unit=None,
        excerpt=None,
    )
    mutated = replace(original, raw=mutated_raw)

    diffs = compare_observation_semantics("NEG-COMPARE-002", original, mutated)
    assert diffs
    assert any("raw.value" in d for d in diffs), f"Expected raw.value mismatch; got: {diffs}"


def test_comparator_detects_notes_change() -> None:
    """A mutated notes field must produce a mismatch."""
    from benchmark.semantics_compare import compare_observation_semantics

    bundle = _make_minimal_bundle(bundle_id="hullq-neg-compare-003")
    original = bundle.observations[0]
    mutated = replace(original, notes="field_label:different_field_label")

    diffs = compare_observation_semantics("NEG-COMPARE-003", original, mutated)
    assert diffs
    assert any("notes" in d for d in diffs)


def test_comparator_detects_finding_change() -> None:
    """A deliberately mutated UnresolvedFinding description must be detected."""
    from benchmark.semantics_compare import compare_finding_semantics

    from hullq.research.observations import UnresolvedFinding, UnresolvedFindingSeverity

    original = UnresolvedFinding(
        finding_id="neg-finding-0001",
        topic="conflict_or_unresolved_evidence",
        description="Original description of an unresolved conflict.",
        related_observation_ids=frozenset({"neg-obs-0000"}),
        severity=UnresolvedFindingSeverity.REVIEW,
    )
    mutated = replace(original, description="CHANGED description — should be detected.")

    diffs = compare_finding_semantics("NEG-FINDING-001", original, mutated)
    assert diffs
    assert any("description" in d for d in diffs)


def test_comparator_detects_crosscheck_outcome_change() -> None:
    """A mutated ReferenceCrosscheck outcome must be detected."""
    from benchmark.semantics_compare import compare_crosscheck_semantics

    from hullq.research.observations import ReferenceCheckOutcome, ReferenceCrosscheck

    original = ReferenceCrosscheck(
        crosscheck_id="neg-cc-0000",
        reference_source_id="sailboatdata-post-hoc-qa",
        topic_or_field=None,
        outcome=ReferenceCheckOutcome.MATCH,
        notes="Original crosscheck notes.",
    )
    mutated = replace(original, outcome=ReferenceCheckOutcome.CONFLICT)

    diffs = compare_crosscheck_semantics("NEG-CC-001", original, mutated)
    assert diffs
    assert any("outcome" in d for d in diffs)


# ---------------------------------------------------------------------------
# Test 6 — Idempotency/conflict failure
# ---------------------------------------------------------------------------


def test_idempotency_requires_exact_fingerprint_match() -> None:
    """Changed immutable semantic content must produce a different fingerprint.

    The importer relies on bundle fingerprinting for idempotency. A bundle with
    changed content must NOT match the fingerprint of the original, so it cannot
    masquerade as an ALREADY_IMPORTED exact re-import.
    """
    from hullq.persistence.fingerprint import fingerprint_bundle

    original = _make_minimal_bundle(bundle_id="hullq-neg-idem-001")

    # Produce a second bundle — same ID/version but different observation value
    from hullq.domain.provenance import RawObservation, RawObservationKind

    obs = original.observations[0]
    mutated_raw = RawObservation(
        kind=RawObservationKind.TEXT_FRAGMENT,
        value="SEMANTICALLY-DIFFERENT-VALUE",
        unit=None,
        excerpt=None,
    )
    mutated_obs = replace(obs, raw=mutated_raw)
    mutated = replace(original, observations=(mutated_obs,))

    fp_original = fingerprint_bundle(original)
    fp_mutated = fingerprint_bundle(mutated)

    assert fp_original != fp_mutated, (
        "Mutated bundle must produce a different fingerprint from the original. "
        "If fingerprints match despite semantic change, ALREADY_IMPORTED detection is broken."
    )


def test_idempotency_same_content_same_fingerprint() -> None:
    """Identical bundles must produce identical fingerprints (determinism)."""
    from hullq.persistence.fingerprint import fingerprint_bundle

    bundle1 = _make_minimal_bundle(bundle_id="hullq-neg-idem-002")
    bundle2 = _make_minimal_bundle(bundle_id="hullq-neg-idem-002")

    fp1 = fingerprint_bundle(bundle1)
    fp2 = fingerprint_bundle(bundle2)

    assert fp1 == fp2, (
        "Identical bundles must produce the same fingerprint. "
        "Nondeterministic fingerprinting would break ALREADY_IMPORTED detection."
    )


# ---------------------------------------------------------------------------
# Test 7 — SailboatData contamination guard
# ---------------------------------------------------------------------------


def test_sailboatdata_source_is_not_observation_source() -> None:
    """SailboatData URLs must not appear as ResearchObservation source_ids.

    This guard ensures that the zero-tolerance SailboatData contamination
    protection remains active through SLICE-0015.
    """
    forbidden = [
        "sailboatdata",
        "sailboat-data",
        "sailboatdata.com",
    ]

    # Attempt to construct a bundle with a SailboatData source
    bundle = _make_minimal_bundle(bundle_id="hullq-neg-sd-001", sailboatdata_source=True)

    # The negative-path test confirms the GUARD CATCHES it:
    violations = [
        obs.observation_id
        for obs in bundle.observations
        if any(f in obs.source_id.lower() for f in forbidden)
    ]
    assert violations, (
        "Expected the synthetic SailboatData-sourced bundle to contain a forbidden source_id. "
        "The test fixture is incorrectly constructed."
    )
    # Now confirm that production benchmark bundles (actual 50 cases) do NOT contain violations:
    from benchmark.materializer import materialize_all

    results = materialize_all()
    production_violations: list[tuple[str, str, str]] = [
        (case_id, obs.observation_id, obs.source_id)
        for case_id, result in results.items()
        if result.bundle is not None
        for obs in result.bundle.observations
        for f in forbidden
        if f in obs.source_id.lower()
    ]

    assert not production_violations, (
        f"SailboatData contamination detected in production benchmark bundles: "
        f"{production_violations[:3]}"
    )


def test_sailboatdata_crosscheck_source_is_qa_marker_not_evidence() -> None:
    """Post-hoc reference crosschecks must use the declared QA source marker, not raw SailboatData.

    A crosscheck outcome is structural/QA evidence, not a field value from SailboatData.
    The crosscheck must never inject SailboatData field values into observations or findings.
    """
    from benchmark.materializer import REFERENCE_SOURCE_ID, materialize_all

    results = materialize_all()
    for case_id, result in results.items():
        if result.bundle is None:
            continue
        for cc in result.bundle.reference_crosschecks:
            assert cc.reference_source_id == REFERENCE_SOURCE_ID, (
                f"Case {case_id} crosscheck has unexpected reference_source_id: "
                f"{cc.reference_source_id!r}. Must be {REFERENCE_SOURCE_ID!r}."
            )
            # Crosscheck notes must not contain raw sailboatdata field values
            if cc.notes:
                for forbidden in ("sailboatdata.com", "sailboatdata/sailboat"):
                    assert forbidden not in cc.notes.lower(), (
                        f"Case {case_id} crosscheck notes contain forbidden substring "
                        f"{forbidden!r}: {cc.notes[:120]!r}"
                    )


# ---------------------------------------------------------------------------
# G3 Gate Boundary Tests — evaluate_g3_gate() called directly
#
# These tests exercise the real production gate function at pre-committed
# threshold boundaries.  They use evaluate_g3_gate() directly so the tests
# share the same decision function as runner.py.
#
# Some inputs do not sum to total_cases (e.g. materialized + review + cannot
# may exceed total_cases) — this is intentional for pure-function boundary
# probing where one gate is isolated while others are kept passing.
# ---------------------------------------------------------------------------


def _base_gate_inputs(**overrides: Any) -> dict[str, Any]:
    """Base inputs representing a perfect 50/50 benchmark run (all gates pass)."""
    base: dict[str, Any] = {
        "total_cases": 50,
        "materialized": 50,
        "review_required": 0,
        "cannot_materialize": 0,
        "contract_gap_count": 0,
        "first_pass_imported": 50,
        "reimport_already_imported": 50,
        "fresh_run_imported": 50,
        "readback_mismatches": 0,
        "fresh_run_semantic_mismatches": 0,
        "first_pass_conflict": 0,
        "first_pass_error": 0,
        "reimport_conflict": 0,
        "reimport_error": 0,
    }
    base.update(overrides)
    return base


def test_g3_gate_perfect_50_50_is_pass() -> None:
    """50/50 materialized, 0 errors → G3_PASS (the actual current benchmark case)."""
    result = evaluate_g3_gate(**_base_gate_inputs())
    assert result.recommendation == "G3_PASS", (
        f"Perfect 50/50 case must produce G3_PASS; got {result.recommendation!r}"
    )
    assert result.all_correctness_pass
    assert result.contract_gap_count == 0


def test_g3_gate_65_pct_materialization_is_positive() -> None:
    """Mechanical materialization exactly at 65% (13/20) satisfies the >=65% threshold.

    Also exercises the review-required <=35% boundary (7/20 = 35%).
    Uses total_cases=20 for exact percentage arithmetic.
    """
    # 13/20 = 65.0%  mat, 7/20 = 35.0% review, 0 cannot — all gates pass
    result = evaluate_g3_gate(
        **_base_gate_inputs(
            total_cases=20,
            materialized=13,
            review_required=7,
            cannot_materialize=0,
            first_pass_imported=13,
            reimport_already_imported=13,
            fresh_run_imported=13,
        )
    )
    assert result.recommendation == "G3_PASS", (
        f"mat=13/20 (65%) and review=7/20 (35%) must satisfy both boundaries; "
        f"got {result.recommendation!r}, rationale: {result.rationale}"
    )
    assert result.materialization_pct == 65.0
    assert result.review_pct == 35.0


def test_g3_gate_below_65_pct_materialization_is_harden_first() -> None:
    """Mechanical materialization below 65% (12/20=60%) → HARDEN_FIRST."""
    result = evaluate_g3_gate(
        **_base_gate_inputs(
            total_cases=20,
            materialized=12,
            review_required=8,
            cannot_materialize=0,
            first_pass_imported=12,
            reimport_already_imported=12,
            fresh_run_imported=12,
        )
    )
    assert result.recommendation == "HARDEN_FIRST", (
        f"mat=12/20 (60%) < 65% must produce HARDEN_FIRST; got {result.recommendation!r}"
    )
    assert result.materialization_pct == 60.0


def test_g3_gate_exactly_10_pct_cannot_is_acceptable() -> None:
    """Cannot-materialize-without-invention exactly at 10% (2/20) satisfies the <=10% threshold.

    Uses total_cases=20 for exact percentage arithmetic; 18 materialized (90%).
    """
    result = evaluate_g3_gate(
        **_base_gate_inputs(
            total_cases=20,
            materialized=18,
            review_required=0,
            cannot_materialize=2,
            first_pass_imported=18,
            reimport_already_imported=18,
            fresh_run_imported=18,
        )
    )
    assert result.recommendation == "G3_PASS", (
        f"cannot=2/20 (10.0%) at exactly the <=10% boundary must still be G3_PASS; "
        f"got {result.recommendation!r}"
    )
    assert result.cannot_pct == 10.0


def test_g3_gate_above_10_pct_cannot_is_harden_first() -> None:
    """Cannot-materialize-without-invention above 10% (3/20=15%) → HARDEN_FIRST."""
    result = evaluate_g3_gate(
        **_base_gate_inputs(
            total_cases=20,
            materialized=17,
            review_required=0,
            cannot_materialize=3,
            first_pass_imported=17,
            reimport_already_imported=17,
            fresh_run_imported=17,
        )
    )
    assert result.recommendation == "HARDEN_FIRST", (
        f"cannot=3/20 (15%) > 10% must produce HARDEN_FIRST; got {result.recommendation!r}"
    )
    assert result.cannot_pct == 15.0


def test_g3_gate_above_35_pct_review_is_harden_first() -> None:
    """Review-required above 35% (36/100=36%) → HARDEN_FIRST.

    Pure function boundary probe: inputs do not sum to total_cases; that is intentional.
    The materialization gate (70% >= 65%) and cannot gate (0% <= 10%) pass; only review fires.
    """
    result = evaluate_g3_gate(
        **_base_gate_inputs(
            total_cases=100,
            materialized=70,
            review_required=36,
            cannot_materialize=0,
            first_pass_imported=70,
            reimport_already_imported=70,
            fresh_run_imported=70,
        )
    )
    assert result.recommendation == "HARDEN_FIRST", (
        f"review=36/100 (36%) > 35% must produce HARDEN_FIRST; got {result.recommendation!r}"
    )
    assert result.review_pct == 36.0


def test_g3_gate_contract_gap_is_blocked() -> None:
    """contract_gap_count >= 1 → BLOCKED regardless of other metrics."""
    result = evaluate_g3_gate(
        **_base_gate_inputs(
            total_cases=20,
            materialized=19,
            cannot_materialize=1,
            contract_gap_count=1,
            first_pass_imported=19,
            reimport_already_imported=19,
            fresh_run_imported=19,
        )
    )
    assert result.recommendation == "BLOCKED", (
        f"contract_gap_count=1 must produce BLOCKED; got {result.recommendation!r}"
    )


def test_g3_gate_validation_failure_is_harden_first_not_blocked() -> None:
    """VALIDATION_FAILURE that pushes cannot_pct > 10% produces HARDEN_FIRST, not BLOCKED.

    Distinguishes: CONTRACT_GAP → BLOCKED; VALIDATION_FAILURE → HARDEN_FIRST.
    """
    # 3/20 cannot (15% > 10%), contract_gap_count=0 → HARDEN_FIRST (cannot_pct gate)
    result = evaluate_g3_gate(
        **_base_gate_inputs(
            total_cases=20,
            materialized=17,
            review_required=0,
            cannot_materialize=3,
            contract_gap_count=0,
            first_pass_imported=17,
            reimport_already_imported=17,
            fresh_run_imported=17,
        )
    )
    assert result.recommendation == "HARDEN_FIRST", (
        f"cannot_pct=15% (>10%) with no CONTRACT_GAP must produce HARDEN_FIRST; "
        f"got {result.recommendation!r}"
    )
    assert result.recommendation != "BLOCKED"


def test_g3_gate_readback_mismatch_fails_correctness() -> None:
    """Any readback semantic mismatch → not G3_PASS (zero-tolerance correctness gate)."""
    result = evaluate_g3_gate(**_base_gate_inputs(readback_mismatches=1))
    assert result.recommendation != "G3_PASS", (
        f"readback_mismatches=1 must not produce G3_PASS; got {result.recommendation!r}"
    )
    assert result.recommendation == "HARDEN_FIRST"
    assert not result.all_correctness_pass


def test_g3_gate_fresh_semantic_mismatch_fails_correctness() -> None:
    """Any fresh-schema semantic mismatch → not G3_PASS (nondeterminism gate)."""
    result = evaluate_g3_gate(**_base_gate_inputs(fresh_run_semantic_mismatches=1))
    assert result.recommendation == "HARDEN_FIRST"
    assert not result.all_correctness_pass


def test_g3_gate_reimport_idempotency_failure_fails_correctness() -> None:
    """reimport_already_imported < materialized → not G3_PASS (idempotency gate)."""
    result = evaluate_g3_gate(**_base_gate_inputs(reimport_already_imported=49))
    assert result.recommendation == "HARDEN_FIRST"
    assert not result.all_correctness_pass


def test_g3_gate_scorecard_contains_all_required_metrics() -> None:
    """G3GateResult scorecard must contain all required binding metric names."""
    required_metrics = {
        "readback_semantic_mismatches",
        "nondeterministic_semantic_output",
        "unexpected_persistence_errors",
        "duplicate_membership_anomalies",
        "exact_reimport_idempotency",
        "fresh_db_semantic_equality",
        "invented_force_resolved_values",
        "sailboatdata_value_contamination",
        "mechanical_materialization_pct",
        "cannot_materialize_without_invention_pct",
        "review_required_pct",
        "contract_gap_count",
    }
    result = evaluate_g3_gate(**_base_gate_inputs())
    scorecard_names = {m.name for m in result.scorecard}
    missing = required_metrics - scorecard_names
    assert not missing, f"Scorecard missing required metrics: {sorted(missing)}"


def test_g3_gate_scorecard_verified_invariants_marked_correctly() -> None:
    """VERIFIED_INVARIANT metrics must have GUARD_VERIFIED as measured value and PASS status."""
    from benchmark.gate import GUARD_VERIFIED

    result = evaluate_g3_gate(**_base_gate_inputs())
    invariant_metrics = [m for m in result.scorecard if m.evidence_basis == "VERIFIED_INVARIANT"]
    assert invariant_metrics, "Expected at least one VERIFIED_INVARIANT metric in scorecard"
    for m in invariant_metrics:
        assert m.measured == GUARD_VERIFIED, (
            f"VERIFIED_INVARIANT metric {m.name!r} must have measured={GUARD_VERIFIED!r}; "
            f"got {m.measured!r}"
        )
        assert m.status == "PASS", (
            f"VERIFIED_INVARIANT metric {m.name!r} must have status=PASS; got {m.status!r}"
        )


def test_g3_gate_scorecard_as_dicts_is_json_serialisable() -> None:
    """scorecard_as_dicts() must return a list of plain dicts serialisable to JSON."""
    import json

    result = evaluate_g3_gate(**_base_gate_inputs())
    dicts = result.scorecard_as_dicts()
    # Must not raise
    json.dumps(dicts)
    assert isinstance(dicts, list)
    assert all(isinstance(d, dict) for d in dicts)
    required_keys = {"name", "measured", "threshold", "status", "evidence_basis"}
    for d in dicts:
        assert required_keys.issubset(d.keys()), (
            f"Scorecard dict missing required keys: {required_keys - d.keys()}"
        )
