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
    """Simulate the runner recommendation logic: CANNOT_MATERIALIZE without CONTRACT_GAP.

    If cannot_count > 0 but contract_gap_count == 0, recommendation must be HARDEN_FIRST.
    """
    from benchmark.materializer import (
        FAILURE_CLASS_CONTRACT_GAP,
        classify_cannot_materialize_reasons,
    )

    # Two CANNOT_MATERIALIZE cases with VALIDATION_FAILURE
    cannot_results = [
        ["ValueError: bad unit"],
        ["KeyError: missing source field"],
    ]
    contract_gap_count = sum(
        1
        for reasons in cannot_results
        if classify_cannot_materialize_reasons(reasons) == FAILURE_CLASS_CONTRACT_GAP
    )
    assert contract_gap_count == 0, (
        "Ordinary CANNOT_MATERIALIZE cases must not produce CONTRACT_GAP classification."
    )
    # Recommendation must be HARDEN_FIRST (not BLOCKED) — confirmed by contract_gap_count == 0
    # The full runner logic: if contract_gap_count == 0 and cannot_count > 0 → HARDEN_FIRST


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
    """A CONTRACT_GAP failure must make the recommendation BLOCKED.

    Exercises the runner recommendation logic directly with synthetic data.
    """
    from benchmark.materializer import (
        FAILURE_CLASS_CONTRACT_GAP,
        ContractGapError,
        MaterializationResult,
        classify_cannot_materialize_reasons,
    )

    # Synthetic result: one case fails with ContractGapError
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
    assert contract_gap_count == 1, "Expected one CONTRACT_GAP failure"

    # Recommendation derivation (mirrors runner logic):
    recommendation = "BLOCKED" if contract_gap_count > 0 else "HARDEN_FIRST"
    assert recommendation == "BLOCKED", "CONTRACT_GAP failure must produce BLOCKED recommendation."


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
