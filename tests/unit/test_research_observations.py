"""Unit tests for SLICE-0012: ResearchObservation, applicability, claim semantics,
FieldEvidenceV3 and ResearchEvidenceBundle contracts.

Covers all 22 unit-level required tests from the slice spec.
"""

from __future__ import annotations

import dataclasses

import pytest

from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
    FieldEvidence,
    FieldEvidenceV3,
    JsonPointer,
    NormalizedCandidate,
    ObservationApplicability,
    ProducerKind,
    ProducerMetadata,
    ProvenanceSubject,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    SourceLocator,
    SubjectKind,
    validate_evidence_invariants,
    validate_evidence_v3_invariants,
)
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import (
    PromotionError,
    ReferenceCheckOutcome,
    ReferenceCrosscheck,
    ResearchEvidenceBundle,
    ResearchObservation,
    UnresolvedFinding,
    UnresolvedFindingSeverity,
    migrate_evidence_v02_to_v03,
    promote_to_field_evidence,
)

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _target(model: str = "Test 35", manufacturer: str | None = "TestYachts") -> ResearchTarget:
    return ResearchTarget(manufacturer=manufacturer, model=model, first_built=1980)


def _applicability_unknown() -> ObservationApplicability:
    return ObservationApplicability(
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
    )


def _locator() -> SourceLocator:
    return SourceLocator(
        page=None, section=None, anchor=None, table=None, figure=None, record_key=None
    )


def _producer() -> ProducerMetadata:
    return ProducerMetadata(
        kind=ProducerKind.LLM,
        identifier="test-agent",
        version="0.1",
        model="test-model",
        prompt_or_rule_version=None,
    )


def _raw(value: object = "test") -> RawObservation:
    return RawObservation(kind=RawObservationKind.LITERAL, value=value, unit=None, excerpt=None)


def _observation(
    observation_id: str = "OBS-001",
    model: str = "Test 35",
    claim: ClaimSemantics = ClaimSemantics.UNKNOWN,
    applicability: ObservationApplicability | None = None,
    intended_subject_kind_hint: SubjectKind | None = None,
    intended_field_pointer: JsonPointer | None = None,
) -> ResearchObservation:
    return ResearchObservation(
        observation_id=observation_id,
        research_target=_target(model=model),
        source_id="SRC-TEST",
        source_locator=_locator(),
        raw=_raw(),
        normalized_candidate=None,
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        claim_semantics=claim,
        applicability=applicability or _applicability_unknown(),
        producer=_producer(),
        research_context=ResearchContext(research_job_id="JOB-001", activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_observation_id=None,
        intended_subject_kind_hint=intended_subject_kind_hint,
        intended_field_pointer=intended_field_pointer,
        notes=None,
    )


def _subject(kind: SubjectKind = SubjectKind.BOAT_DESIGN, id: str = "BD-001") -> ProvenanceSubject:
    return ProvenanceSubject(kind=kind, id=id)


def _field_pointer(path: str = "/loa_m") -> JsonPointer:
    return JsonPointer(path)


def _v02_evidence(evidence_id: str = "EVID-V02-001") -> FieldEvidence:
    return FieldEvidence(
        evidence_id=evidence_id,
        subject=_subject(),
        field_pointer=_field_pointer(),
        source_id="SRC-TEST",
        source_locator=_locator(),
        raw=_raw(value=10.5),
        normalized_candidate=None,
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        producer=_producer(),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_evidence_id=None,
        notes=None,
    )


# ---------------------------------------------------------------------------
# Test 1 — ResearchObservation can exist with ResearchTarget and no subject
# ---------------------------------------------------------------------------


def test_research_observation_no_canonical_subject() -> None:
    obs = _observation()
    assert obs.observation_id == "OBS-001"
    # There is no ProvenanceSubject field on ResearchObservation.
    assert not hasattr(obs, "subject")


def test_research_observation_no_subject_field_in_dataclass() -> None:
    field_names = {f.name for f in dataclasses.fields(ResearchObservation)}
    assert "subject" not in field_names
    assert "observation_id" in field_names
    assert "research_target" in field_names


# ---------------------------------------------------------------------------
# Test 2 — ResearchObservation cannot silently manufacture a canonical subject
# ---------------------------------------------------------------------------


def test_research_observation_has_no_subject_property() -> None:
    obs = _observation()
    # No .subject attribute at all — cannot silently manufacture one.
    assert not hasattr(obs, "subject")


def test_research_observation_intended_hint_is_not_canonical() -> None:
    obs = _observation(
        intended_subject_kind_hint=SubjectKind.BOAT_DESIGN,
        intended_field_pointer=JsonPointer("/displacement_kg"),
    )
    # hint does not create or return a ProvenanceSubject
    assert obs.intended_subject_kind_hint is SubjectKind.BOAT_DESIGN
    assert obs.intended_field_pointer == JsonPointer("/displacement_kg")
    assert not hasattr(obs, "subject")


# ---------------------------------------------------------------------------
# Test 3 — Exact claim-semantics vocabulary parity between schema/runtime
# ---------------------------------------------------------------------------


def test_claim_semantics_vocabulary_matches_schema() -> None:
    expected = {
        "nominal_design_value",
        "factory_option_value",
        "operating_state_value",
        "individual_hull_value",
        "class_rule_constraint",
        "measurement_certificate_value",
        "published_calculation",
        "identity_or_chronology_claim",
        "other",
        "unknown",
    }
    actual = {s.value for s in ClaimSemantics}
    assert actual == expected


# ---------------------------------------------------------------------------
# Test 4 — Claim semantics remain independent of existing EvidenceType
# ---------------------------------------------------------------------------


def test_claim_semantics_independent_of_evidence_type() -> None:
    # An authoritative class-or-owner-association source can carry class_rule_constraint
    obs = _observation(claim=ClaimSemantics.CLASS_RULE_CONSTRAINT)
    obs2 = ResearchObservation(
        observation_id="OBS-002",
        research_target=_target(),
        source_id="SRC-CLASS",
        source_locator=_locator(),
        raw=_raw("maximum beam 3.65m per class rules"),
        normalized_candidate=None,
        evidence_type=EvidenceType.CLASS_OR_OWNER_ASSOCIATION,
        claim_semantics=ClaimSemantics.CLASS_RULE_CONSTRAINT,
        applicability=_applicability_unknown(),
        producer=_producer(),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_observation_id=None,
        intended_subject_kind_hint=None,
        intended_field_pointer=None,
        notes=None,
    )
    # The same EvidenceType can appear with different ClaimSemantics
    obs3 = ResearchObservation(
        observation_id="OBS-003",
        research_target=_target(),
        source_id="SRC-CLASS",
        source_locator=_locator(),
        raw=_raw("LOA 10.36m"),
        normalized_candidate=None,
        evidence_type=EvidenceType.CLASS_OR_OWNER_ASSOCIATION,
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
        applicability=_applicability_unknown(),
        producer=_producer(),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_observation_id=None,
        intended_subject_kind_hint=None,
        intended_field_pointer=None,
        notes=None,
    )
    assert obs2.evidence_type == EvidenceType.CLASS_OR_OWNER_ASSOCIATION
    assert obs2.claim_semantics == ClaimSemantics.CLASS_RULE_CONSTRAINT
    assert obs3.evidence_type == EvidenceType.CLASS_OR_OWNER_ASSOCIATION
    assert obs3.claim_semantics == ClaimSemantics.NOMINAL_DESIGN_VALUE
    # Claim semantics and evidence_type are different enum types
    assert type(obs2.claim_semantics) is ClaimSemantics
    assert type(obs2.evidence_type) is EvidenceType
    assert ClaimSemantics is not EvidenceType
    _ = obs  # suppress unused-variable warning


# ---------------------------------------------------------------------------
# Test 5 — Applicability accepts unknown/partial boundaries
# ---------------------------------------------------------------------------


def test_applicability_accepts_all_null() -> None:
    a = ObservationApplicability(
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
    )
    assert a.first_year is None
    assert a.unknown_or_unbounded is True


def test_applicability_accepts_partial_year_range() -> None:
    a = ObservationApplicability(
        first_year=1979,
        last_year=None,
        hull_number_from=None,
        hull_number_to=None,
        market_or_region=None,
        named_variant_hint=None,
        design_option_hints=None,
        operating_state_hint=None,
        individual_hull_or_listing_ref=None,
        unknown_or_unbounded=False,
    )
    assert a.first_year == 1979
    assert a.last_year is None


def test_applicability_accepts_full_year_range() -> None:
    a = ObservationApplicability(
        first_year=1975,
        last_year=1982,
        hull_number_from=None,
        hull_number_to=None,
        market_or_region=None,
        named_variant_hint=None,
        design_option_hints=None,
        operating_state_hint=None,
        individual_hull_or_listing_ref=None,
        unknown_or_unbounded=False,
    )
    assert a.first_year == 1975
    assert a.last_year == 1982


# ---------------------------------------------------------------------------
# Test 6 — Invalid reversed year ranges fail
# ---------------------------------------------------------------------------


def test_applicability_rejects_reversed_year_range() -> None:
    with pytest.raises(ValueError, match=r"first_year.*last_year"):
        ObservationApplicability(
            first_year=1985,
            last_year=1979,
            hull_number_from=None,
            hull_number_to=None,
            market_or_region=None,
            named_variant_hint=None,
            design_option_hints=None,
            operating_state_hint=None,
            individual_hull_or_listing_ref=None,
            unknown_or_unbounded=False,
        )


def test_applicability_rejects_same_value_is_ok() -> None:
    a = ObservationApplicability(
        first_year=1979,
        last_year=1979,
        hull_number_from=None,
        hull_number_to=None,
        market_or_region=None,
        named_variant_hint=None,
        design_option_hints=None,
        operating_state_hint=None,
        individual_hull_or_listing_ref=None,
        unknown_or_unbounded=False,
    )
    assert a.first_year == 1979
    assert a.last_year == 1979


# ---------------------------------------------------------------------------
# Test 7 — Scoped refs required when that scope is asserted
# ---------------------------------------------------------------------------


def test_applicability_rejects_empty_individual_hull_ref() -> None:
    with pytest.raises(ValueError, match="individual_hull_or_listing_ref"):
        ObservationApplicability(
            first_year=None,
            last_year=None,
            hull_number_from=None,
            hull_number_to=None,
            market_or_region=None,
            named_variant_hint=None,
            design_option_hints=None,
            operating_state_hint=None,
            individual_hull_or_listing_ref="",
            unknown_or_unbounded=False,
        )


def test_applicability_rejects_empty_string_in_design_option_hints() -> None:
    with pytest.raises(ValueError, match="design_option_hints"):
        ObservationApplicability(
            first_year=None,
            last_year=None,
            hull_number_from=None,
            hull_number_to=None,
            market_or_region=None,
            named_variant_hint=None,
            design_option_hints=["shoal keel", ""],
            operating_state_hint=None,
            individual_hull_or_listing_ref=None,
            unknown_or_unbounded=False,
        )


def test_applicability_accepts_valid_design_option_hints() -> None:
    a = ObservationApplicability(
        first_year=None,
        last_year=None,
        hull_number_from=None,
        hull_number_to=None,
        market_or_region=None,
        named_variant_hint=None,
        design_option_hints=["shoal keel", "roller furling"],
        operating_state_hint=None,
        individual_hull_or_listing_ref=None,
        unknown_or_unbounded=False,
    )
    assert a.design_option_hints == ("shoal keel", "roller furling")


# ---------------------------------------------------------------------------
# Test 8 — Caller mutation cannot alter stored observation/applicability snapshots
# ---------------------------------------------------------------------------


def test_applicability_freezes_design_option_hints_list() -> None:
    hints: list[str] = ["shoal keel"]
    a = ObservationApplicability(
        first_year=None,
        last_year=None,
        hull_number_from=None,
        hull_number_to=None,
        market_or_region=None,
        named_variant_hint=None,
        design_option_hints=hints,
        operating_state_hint=None,
        individual_hull_or_listing_ref=None,
        unknown_or_unbounded=False,
    )
    hints.append("tall rig")
    assert a.design_option_hints == ("shoal keel",)


def test_research_observation_is_frozen() -> None:
    obs = _observation()
    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
        obs.observation_id = "MUTATED"  # type: ignore[misc]


def test_research_observation_raw_snapshot_is_independent() -> None:
    mutable_value: dict[str, object] = {"key": "original"}
    raw = RawObservation(
        kind=RawObservationKind.STRUCTURED_RECORD,
        value=mutable_value,
        unit=None,
        excerpt=None,
    )
    mutable_value["key"] = "mutated"
    assert raw.value == {"key": "original"}


def test_bundle_snapshots_caller_list() -> None:
    obs = _observation()
    obs_list = [obs]
    bundle = ResearchEvidenceBundle(
        bundle_id="BUNDLE-001",
        bundle_version="1.0",
        research_target=_target(),
        research_job_id=None,
        activity_id=None,
        observations=tuple(obs_list),  # type: ignore[arg-type]
        unresolved_findings=(),
        promoted_evidence=(),
        reference_crosschecks=(),
    )
    obs_list.clear()
    assert len(bundle.observations) == 1


# ---------------------------------------------------------------------------
# Test 9 — Successor FieldEvidenceV3 retains all v0.2 semantics + claim/applicability
# ---------------------------------------------------------------------------


def test_field_evidence_v3_has_all_v02_fields_plus_new() -> None:
    v3 = FieldEvidenceV3(
        evidence_id="EVID-V3-001",
        subject=_subject(),
        field_pointer=_field_pointer(),
        source_id="SRC-TEST",
        source_locator=_locator(),
        raw=_raw(value=10.5),
        normalized_candidate=NormalizedCandidate(
            value=10.5, unit="m", method_id="hullq-norm-1.0", method_version="1.0"
        ),
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        producer=_producer(),
        research_context=ResearchContext(research_job_id="JOB-001", activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_evidence_id=None,
        notes="Pearson 35 LOA from specification sheet",
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
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
            unknown_or_unbounded=False,
        ),
    )
    # v0.2 fields preserved
    assert v3.evidence_id == "EVID-V3-001"
    assert v3.subject == _subject()
    assert v3.evidence_type == EvidenceType.MANUFACTURER_SPECIFICATION
    assert v3.confidence == ConfidenceLevel.HIGH
    # New v0.3 fields
    assert v3.claim_semantics == ClaimSemantics.NOMINAL_DESIGN_VALUE
    assert isinstance(v3.applicability, ObservationApplicability)


def test_field_evidence_v3_inherits_v02_invariants() -> None:
    # validate_evidence_invariants works with v0.3 (via inheritance)
    v3 = FieldEvidenceV3(
        evidence_id="EVID-V3-VALID",
        subject=_subject(),
        field_pointer=_field_pointer(),
        source_id="SRC",
        source_locator=_locator(),
        raw=_raw(),
        normalized_candidate=None,
        evidence_type=EvidenceType.BROCHURE,
        producer=_producer(),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.MEDIUM,
        supersedes_evidence_id=None,
        notes=None,
        claim_semantics=ClaimSemantics.UNKNOWN,
        applicability=_applicability_unknown(),
    )
    errors = validate_evidence_invariants(v3)
    assert errors == []


def test_field_evidence_v3_validate_v3_invariants() -> None:
    v3 = FieldEvidenceV3(
        evidence_id="EVID-V3-VALID2",
        subject=_subject(),
        field_pointer=_field_pointer(),
        source_id="SRC",
        source_locator=_locator(),
        raw=_raw(),
        normalized_candidate=None,
        evidence_type=EvidenceType.BROCHURE,
        producer=_producer(),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.MEDIUM,
        supersedes_evidence_id=None,
        notes=None,
        claim_semantics=ClaimSemantics.UNKNOWN,
        applicability=_applicability_unknown(),
    )
    errors = validate_evidence_v3_invariants(v3)
    assert errors == []


# ---------------------------------------------------------------------------
# Test 10 — v0.2 adapter maps absent semantics to explicit unknown/unbounded
# ---------------------------------------------------------------------------


def test_migrate_v02_to_v03_defaults_to_unknown_claim() -> None:
    v02 = _v02_evidence()
    v3 = migrate_evidence_v02_to_v03(v02)
    assert v3.claim_semantics == ClaimSemantics.UNKNOWN
    assert v3.claim_semantics != ClaimSemantics.NOMINAL_DESIGN_VALUE


def test_migrate_v02_to_v03_defaults_to_unknown_applicability() -> None:
    v02 = _v02_evidence()
    v3 = migrate_evidence_v02_to_v03(v02)
    assert v3.applicability.unknown_or_unbounded is True


def test_migrate_v02_to_v03_preserves_all_provenance_fields() -> None:
    v02 = _v02_evidence("EVID-ORIG")
    v3 = migrate_evidence_v02_to_v03(v02)
    assert v3.evidence_id == "EVID-ORIG"
    assert v3.subject == v02.subject
    assert v3.field_pointer == v02.field_pointer
    assert v3.source_id == v02.source_id
    assert v3.evidence_type == v02.evidence_type
    assert v3.observed_at == v02.observed_at
    assert v3.confidence == v02.confidence


def test_migrate_v02_to_v03_accepts_explicit_semantics() -> None:
    v02 = _v02_evidence()
    a = ObservationApplicability(
        first_year=1979,
        last_year=1982,
        hull_number_from=None,
        hull_number_to=None,
        market_or_region=None,
        named_variant_hint=None,
        design_option_hints=None,
        operating_state_hint=None,
        individual_hull_or_listing_ref=None,
        unknown_or_unbounded=False,
    )
    v3 = migrate_evidence_v02_to_v03(
        v02,
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
        applicability=a,
    )
    assert v3.claim_semantics == ClaimSemantics.NOMINAL_DESIGN_VALUE
    assert v3.applicability.first_year == 1979


# ---------------------------------------------------------------------------
# Test 11 — observed_at and applicability time remain independent
# ---------------------------------------------------------------------------


def test_observed_at_and_applicability_year_are_independent() -> None:
    obs = ResearchObservation(
        observation_id="OBS-INDEP",
        research_target=_target(),
        source_id="SRC",
        source_locator=_locator(),
        raw=_raw("10.67m"),
        normalized_candidate=None,
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
        applicability=ObservationApplicability(
            first_year=1979,
            last_year=1979,
            hull_number_from=None,
            hull_number_to=None,
            market_or_region=None,
            named_variant_hint=None,
            design_option_hints=None,
            operating_state_hint=None,
            individual_hull_or_listing_ref=None,
            unknown_or_unbounded=False,
        ),
        producer=_producer(),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-20T12:30:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_observation_id=None,
        intended_subject_kind_hint=None,
        intended_field_pointer=None,
        notes="Pearson 35 - 1979 model year specification",
    )
    # observed_at is retrieval time
    assert obs.observed_at == "2026-08-20T12:30:00Z"
    # applicability year is production year
    assert obs.applicability.first_year == 1979
    assert obs.applicability.last_year == 1979
    # They are independent — different values, different semantics
    assert obs.observed_at != str(obs.applicability.first_year)


# ---------------------------------------------------------------------------
# Test 12 — individual_hull_value remains identifiable
# ---------------------------------------------------------------------------


def test_individual_hull_value_is_identifiable() -> None:
    obs = ResearchObservation(
        observation_id="OBS-BROKER",
        research_target=_target("Bavaria 38"),
        source_id="SRC-BROKER",
        source_locator=_locator(),
        raw=_raw("displacement 8200kg per seller listing"),
        normalized_candidate=None,
        evidence_type=EvidenceType.NARRATIVE_TEXT,
        claim_semantics=ClaimSemantics.INDIVIDUAL_HULL_VALUE,
        applicability=ObservationApplicability(
            first_year=None,
            last_year=None,
            hull_number_from=None,
            hull_number_to=None,
            market_or_region=None,
            named_variant_hint=None,
            design_option_hints=None,
            operating_state_hint=None,
            individual_hull_or_listing_ref="LISTING-2024-DE-001",
            unknown_or_unbounded=False,
        ),
        producer=_producer(),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.LOW,
        supersedes_observation_id=None,
        intended_subject_kind_hint=None,
        intended_field_pointer=None,
        notes="Broker listing displacement — individual hull only, not design baseline",
    )
    assert obs.claim_semantics == ClaimSemantics.INDIVIDUAL_HULL_VALUE
    assert obs.applicability.individual_hull_or_listing_ref == "LISTING-2024-DE-001"
    # It must not be confused with a nominal design value
    assert obs.claim_semantics != ClaimSemantics.NOMINAL_DESIGN_VALUE


# ---------------------------------------------------------------------------
# Test 13 — Class-rule constraint fixture cannot be mistaken for nominal design
# ---------------------------------------------------------------------------


def test_class_rule_constraint_not_nominal_design_value() -> None:
    obs = ResearchObservation(
        observation_id="OBS-J105-CLASS",
        research_target=_target("J/105"),
        source_id="SRC-J105-CLASS-ASSOC",
        source_locator=_locator(),
        raw=_raw("maximum displacement 2268kg per class rules"),
        normalized_candidate=None,
        evidence_type=EvidenceType.CLASS_OR_OWNER_ASSOCIATION,
        claim_semantics=ClaimSemantics.CLASS_RULE_CONSTRAINT,
        applicability=_applicability_unknown(),
        producer=_producer(),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_observation_id=None,
        intended_subject_kind_hint=SubjectKind.BOAT_DESIGN,
        intended_field_pointer=None,
        notes="J/105 class rule maximum displacement limit",
    )
    assert obs.claim_semantics == ClaimSemantics.CLASS_RULE_CONSTRAINT
    assert obs.claim_semantics != ClaimSemantics.NOMINAL_DESIGN_VALUE
    # Class rules and nominal design values are distinguishable by the contract
    assert ClaimSemantics.CLASS_RULE_CONSTRAINT.value == "class_rule_constraint"
    assert ClaimSemantics.NOMINAL_DESIGN_VALUE.value == "nominal_design_value"


# ---------------------------------------------------------------------------
# Test 14 — Operating-state fixture representable without DesignOption ID
# ---------------------------------------------------------------------------


def test_operating_state_without_design_option_id() -> None:
    obs = ResearchObservation(
        observation_id="OBS-GEMINI-MAST-DOWN",
        research_target=_target("Gemini 105Mc", manufacturer="Performance Cruising"),
        source_id="SRC-GEMINI-SPECS",
        source_locator=_locator(),
        raw=_raw("air draft mast down: 1.1m"),
        normalized_candidate=None,
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        claim_semantics=ClaimSemantics.OPERATING_STATE_VALUE,
        applicability=ObservationApplicability(
            first_year=None,
            last_year=None,
            hull_number_from=None,
            hull_number_to=None,
            market_or_region=None,
            named_variant_hint=None,
            design_option_hints=None,
            operating_state_hint="mast_down",
            individual_hull_or_listing_ref=None,
            unknown_or_unbounded=False,
        ),
        producer=_producer(),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_observation_id=None,
        intended_subject_kind_hint=None,
        intended_field_pointer=None,
        notes="Gemini 105Mc mast-down air draft from spec sheet",
    )
    # Operating state is captured via claim_semantics + applicability.operating_state_hint
    assert obs.claim_semantics == ClaimSemantics.OPERATING_STATE_VALUE
    assert obs.applicability.operating_state_hint == "mast_down"
    # No DesignOption ID was invented — individual_hull_or_listing_ref is None
    assert obs.applicability.individual_hull_or_listing_ref is None
    assert obs.applicability.design_option_hints is None


# ---------------------------------------------------------------------------
# Test 15 — ResearchEvidenceBundle allows partial/unresolved identity research
# ---------------------------------------------------------------------------


def test_bundle_allows_no_canonical_ids() -> None:
    bundle = ResearchEvidenceBundle(
        bundle_id="BUNDLE-PARTIAL",
        bundle_version="1.0",
        research_target=ResearchTarget(
            manufacturer=None, model="Unknown Catamaran", first_built=None
        ),
        research_job_id=None,
        activity_id=None,
        observations=(_observation(),),
        unresolved_findings=(
            UnresolvedFinding(
                finding_id="FIND-001",
                topic="manufacturer_identity",
                description="Manufacturer name could not be resolved to a canonical Brand",
                related_observation_ids=frozenset({"OBS-001"}),
                severity=UnresolvedFindingSeverity.REVIEW,
            ),
        ),
        promoted_evidence=(),
        reference_crosschecks=(),
    )
    assert bundle.bundle_id == "BUNDLE-PARTIAL"
    assert bundle.research_target.manufacturer is None
    assert len(bundle.unresolved_findings) == 1
    assert len(bundle.promoted_evidence) == 0


# ---------------------------------------------------------------------------
# Test 16 — Bundle observations do not require canonical subject IDs
# ---------------------------------------------------------------------------


def test_bundle_observations_have_no_subject_requirement() -> None:
    obs1 = _observation("OBS-A")
    obs2 = _observation("OBS-B")
    bundle = ResearchEvidenceBundle(
        bundle_id="BUNDLE-NO-SUBJECT",
        bundle_version="1.0",
        research_target=_target(),
        research_job_id="JOB-001",
        activity_id=None,
        observations=(obs1, obs2),
        unresolved_findings=(),
        promoted_evidence=(),
        reference_crosschecks=(),
    )
    for obs in bundle.observations:
        assert not hasattr(obs, "subject")
    assert len(bundle.observations) == 2


# ---------------------------------------------------------------------------
# Test 17 — Explicit promotion requires caller-supplied stable ProvenanceSubject
# ---------------------------------------------------------------------------


def test_promotion_requires_explicit_subject() -> None:
    obs = _observation()
    subject = _subject()
    ptr = _field_pointer()
    v3 = promote_to_field_evidence(obs, subject, "EVID-PROMOTED-001", ptr)
    assert v3.subject == subject
    assert v3.evidence_id == "EVID-PROMOTED-001"


def test_promotion_rejects_empty_evidence_id() -> None:
    obs = _observation()
    with pytest.raises(PromotionError, match="evidence_id"):
        promote_to_field_evidence(obs, _subject(), "", _field_pointer())


# ---------------------------------------------------------------------------
# Test 18 — Promotion preserves snapshot losslessly
# ---------------------------------------------------------------------------


def test_promotion_preserves_all_observation_fields() -> None:
    app = ObservationApplicability(
        first_year=1979,
        last_year=1979,
        hull_number_from=None,
        hull_number_to=None,
        market_or_region=None,
        named_variant_hint=None,
        design_option_hints=None,
        operating_state_hint=None,
        individual_hull_or_listing_ref=None,
        unknown_or_unbounded=False,
    )
    obs = ResearchObservation(
        observation_id="OBS-PEARSON",
        research_target=_target("Pearson 35"),
        source_id="SRC-PEARSON-SPEC",
        source_locator=_locator(),
        raw=_raw("LOA 10.67m"),
        normalized_candidate=NormalizedCandidate(
            value=10.67, unit="m", method_id="hullq-norm-1.0", method_version="1.0"
        ),
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
        applicability=app,
        producer=_producer(),
        research_context=ResearchContext(research_job_id="JOB-PEARSON", activity_id="ACT-001"),
        observed_at="2026-08-20T09:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_observation_id=None,
        intended_subject_kind_hint=SubjectKind.BOAT_DESIGN,
        intended_field_pointer=JsonPointer("/loa_m"),
        notes="Pearson 35 spec sheet 1979",
    )
    v3 = promote_to_field_evidence(
        obs,
        ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id="BD-PEARSON35"),
        "EVID-PEARSON-001",
        JsonPointer("/loa_m"),
    )
    # Raw/normalized preserved
    assert v3.raw.value == "LOA 10.67m"
    assert v3.normalized_candidate is not None
    assert v3.normalized_candidate.value == 10.67
    # Source info preserved
    assert v3.source_id == "SRC-PEARSON-SPEC"
    assert v3.evidence_type == EvidenceType.MANUFACTURER_SPECIFICATION
    # Claim and applicability preserved
    assert v3.claim_semantics == ClaimSemantics.NOMINAL_DESIGN_VALUE
    assert v3.applicability.first_year == 1979
    assert v3.applicability.last_year == 1979
    # observed_at preserved from observation
    assert v3.observed_at == "2026-08-20T09:00:00Z"
    # Producer/context preserved
    assert v3.producer.identifier == "test-agent"
    assert v3.research_context.research_job_id == "JOB-PEARSON"


# ---------------------------------------------------------------------------
# Test 19 — Promotion cannot produce FieldResolution or canonical mutation
# ---------------------------------------------------------------------------


def test_promotion_returns_only_field_evidence_v3() -> None:
    obs = _observation()
    result = promote_to_field_evidence(obs, _subject(), "EVID-001", _field_pointer())
    assert isinstance(result, FieldEvidenceV3)
    # Not a tuple, not a resolution, just the evidence record
    assert not isinstance(result, tuple)


def test_promotion_does_not_modify_observation() -> None:
    obs = _observation()
    original_id = obs.observation_id
    promote_to_field_evidence(obs, _subject(), "EVID-001", _field_pointer())
    assert obs.observation_id == original_id


# ---------------------------------------------------------------------------
# Test 20 — Contradictory subject-kind/field mapping fails closed
# ---------------------------------------------------------------------------


def test_promotion_fails_on_subject_kind_contradiction() -> None:
    obs = _observation(
        intended_subject_kind_hint=SubjectKind.BOAT_DESIGN,
    )
    wrong_subject = ProvenanceSubject(kind=SubjectKind.BRAND, id="BRAND-001")
    with pytest.raises(PromotionError, match="intended_subject_kind_hint"):
        promote_to_field_evidence(obs, wrong_subject, "EVID-001", _field_pointer())


def test_promotion_fails_on_field_pointer_contradiction() -> None:
    obs = _observation(
        intended_field_pointer=JsonPointer("/loa_m"),
    )
    wrong_pointer = JsonPointer("/displacement_kg")
    with pytest.raises(PromotionError, match="intended_field_pointer"):
        promote_to_field_evidence(obs, _subject(), "EVID-001", wrong_pointer)


def test_promotion_succeeds_when_hints_match() -> None:
    obs = _observation(
        intended_subject_kind_hint=SubjectKind.BOAT_DESIGN,
        intended_field_pointer=JsonPointer("/loa_m"),
    )
    v3 = promote_to_field_evidence(
        obs,
        ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id="BD-001"),
        "EVID-OK",
        JsonPointer("/loa_m"),
    )
    assert v3.evidence_id == "EVID-OK"


def test_promotion_succeeds_when_no_hints_set() -> None:
    obs = _observation(
        intended_subject_kind_hint=None,
        intended_field_pointer=None,
    )
    v3 = promote_to_field_evidence(obs, _subject(), "EVID-NOHINT", _field_pointer())
    assert v3.evidence_id == "EVID-NOHINT"


# ---------------------------------------------------------------------------
# Test 21 — Reference crosscheck cannot satisfy a FieldResolution evidence reference
# ---------------------------------------------------------------------------


def test_reference_crosscheck_has_no_evidence_id() -> None:
    cc = ReferenceCrosscheck(
        crosscheck_id="CC-001",
        reference_source_id="sailboatdata-reference",
        topic_or_field="/displacement_kg",
        outcome=ReferenceCheckOutcome.CONFLICT,
        notes="Conflict detected on /displacement_kg — likely measurement-basis difference",
    )
    # No evidence_id field — cannot be used as a FieldResolution supporting evidence
    assert not hasattr(cc, "evidence_id")
    assert cc.crosscheck_id == "CC-001"
    assert cc.outcome == ReferenceCheckOutcome.CONFLICT


def test_reference_crosscheck_outcome_only_no_numeric_values() -> None:
    # Regression: ReferenceCrosscheck notes must be qualitative only —
    # no reference field values (no numeric measurements from the reference source).
    cc = ReferenceCrosscheck(
        crosscheck_id="CC-REG-001",
        reference_source_id="sailboatdata-reference",
        topic_or_field="/displacement_kg",
        outcome=ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE,
        notes="Outcome: definition/basis difference on /displacement_kg — reference and researched sources likely use different load-state basis",
    )
    assert cc.outcome == ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE
    assert cc.reference_source_id == "sailboatdata-reference"
    assert cc.topic_or_field == "/displacement_kg"
    # Notes must not contain standalone numeric values that would represent
    # a reference field value (qualitative outcome description only).
    import re

    assert re.search(r"\b\d{4,}\s*(kg|lbs|lb|m|ft)\b", cc.notes or "") is None


def test_reference_crosscheck_in_bundle_is_separate() -> None:
    cc = ReferenceCrosscheck(
        crosscheck_id="CC-002",
        reference_source_id="sailboatdata-reference",
        topic_or_field="/loa_m",
        outcome=ReferenceCheckOutcome.MATCH,
        notes=None,
    )
    bundle = ResearchEvidenceBundle(
        bundle_id="BUNDLE-CC",
        bundle_version="1.0",
        research_target=_target(),
        research_job_id=None,
        activity_id=None,
        observations=(_observation(),),
        unresolved_findings=(),
        promoted_evidence=(),
        reference_crosschecks=(cc,),
    )
    assert len(bundle.reference_crosschecks) == 1
    assert len(bundle.observations) == 1
    # The crosscheck is in reference_crosschecks, NOT in observations
    cc_ids = {c.crosscheck_id for c in bundle.reference_crosschecks}
    obs_ids = {o.observation_id for o in bundle.observations}
    assert cc_ids.isdisjoint(obs_ids)


# ---------------------------------------------------------------------------
# Test 22 — Reference crosscheck works without storing reference field values
# ---------------------------------------------------------------------------


def test_reference_crosscheck_has_no_reference_field_value() -> None:
    cc = ReferenceCrosscheck(
        crosscheck_id="CC-003",
        reference_source_id="sailboatdata-reference",
        topic_or_field="/loa_m",
        outcome=ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE,
        notes="Reference measures DWL, spec sheet measures LOA — definition difference",
    )
    # The crosscheck does not store the actual reference value
    field_names = {f.name for f in dataclasses.fields(ReferenceCrosscheck)}
    assert "reference_value" not in field_names
    assert "reference_field_value" not in field_names
    # Only the outcome and notes
    assert cc.topic_or_field == "/loa_m"
    assert cc.outcome == ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE
    assert "definition" in (cc.notes or "")


# ---------------------------------------------------------------------------
# Additional vocabulary parity test
# ---------------------------------------------------------------------------


def test_reference_check_outcome_vocabulary_matches_schema() -> None:
    expected = {
        "match",
        "partial_match",
        "conflict",
        "definition_or_basis_difference",
        "identity_disambiguation_required",
        "reference_incomplete",
        "no_reference_record_found",
        "not_checked",
    }
    actual = {v.value for v in ReferenceCheckOutcome}
    assert actual == expected


# ---------------------------------------------------------------------------
# Validation error paths — coverage for error-raising branches
# ---------------------------------------------------------------------------


def test_reference_crosscheck_rejects_empty_crosscheck_id() -> None:
    with pytest.raises(ValueError, match="crosscheck_id"):
        ReferenceCrosscheck(
            crosscheck_id="",
            reference_source_id="sailboatdata-reference",
            topic_or_field=None,
            outcome=ReferenceCheckOutcome.MATCH,
            notes=None,
        )


def test_reference_crosscheck_rejects_empty_reference_source_id() -> None:
    with pytest.raises(ValueError, match="reference_source_id"):
        ReferenceCrosscheck(
            crosscheck_id="CC-001",
            reference_source_id="",
            topic_or_field=None,
            outcome=ReferenceCheckOutcome.MATCH,
            notes=None,
        )


def test_unresolved_finding_rejects_empty_finding_id() -> None:
    with pytest.raises(ValueError, match="finding_id"):
        UnresolvedFinding(
            finding_id="",
            topic="test",
            description="test",
            related_observation_ids=frozenset(),
            severity=UnresolvedFindingSeverity.INFORMATIONAL,
        )


def test_unresolved_finding_rejects_empty_topic() -> None:
    with pytest.raises(ValueError, match="topic"):
        UnresolvedFinding(
            finding_id="FIND-001",
            topic="",
            description="test",
            related_observation_ids=frozenset(),
            severity=UnresolvedFindingSeverity.INFORMATIONAL,
        )


def test_unresolved_finding_rejects_empty_description() -> None:
    with pytest.raises(ValueError, match="description"):
        UnresolvedFinding(
            finding_id="FIND-001",
            topic="test",
            description="",
            related_observation_ids=frozenset(),
            severity=UnresolvedFindingSeverity.INFORMATIONAL,
        )


def test_research_observation_rejects_empty_observation_id() -> None:
    with pytest.raises(ValueError, match="observation_id"):
        ResearchObservation(
            observation_id="",
            research_target=_target(),
            source_id="SRC",
            source_locator=_locator(),
            raw=_raw(),
            normalized_candidate=None,
            evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
            claim_semantics=ClaimSemantics.UNKNOWN,
            applicability=_applicability_unknown(),
            producer=_producer(),
            research_context=ResearchContext(research_job_id=None, activity_id=None),
            observed_at="2026-08-20T00:00:00Z",
            confidence=ConfidenceLevel.HIGH,
            supersedes_observation_id=None,
            intended_subject_kind_hint=None,
            intended_field_pointer=None,
            notes=None,
        )


def test_research_observation_rejects_empty_source_id() -> None:
    with pytest.raises(ValueError, match="source_id"):
        ResearchObservation(
            observation_id="OBS-001",
            research_target=_target(),
            source_id="",
            source_locator=_locator(),
            raw=_raw(),
            normalized_candidate=None,
            evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
            claim_semantics=ClaimSemantics.UNKNOWN,
            applicability=_applicability_unknown(),
            producer=_producer(),
            research_context=ResearchContext(research_job_id=None, activity_id=None),
            observed_at="2026-08-20T00:00:00Z",
            confidence=ConfidenceLevel.HIGH,
            supersedes_observation_id=None,
            intended_subject_kind_hint=None,
            intended_field_pointer=None,
            notes=None,
        )


def test_research_observation_rejects_empty_observed_at() -> None:
    with pytest.raises(ValueError, match="observed_at"):
        ResearchObservation(
            observation_id="OBS-001",
            research_target=_target(),
            source_id="SRC",
            source_locator=_locator(),
            raw=_raw(),
            normalized_candidate=None,
            evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
            claim_semantics=ClaimSemantics.UNKNOWN,
            applicability=_applicability_unknown(),
            producer=_producer(),
            research_context=ResearchContext(research_job_id=None, activity_id=None),
            observed_at="",
            confidence=ConfidenceLevel.HIGH,
            supersedes_observation_id=None,
            intended_subject_kind_hint=None,
            intended_field_pointer=None,
            notes=None,
        )


def test_bundle_rejects_empty_bundle_id() -> None:
    with pytest.raises(ValueError, match="bundle_id"):
        ResearchEvidenceBundle(
            bundle_id="",
            bundle_version="1.0",
            research_target=_target(),
            research_job_id=None,
            activity_id=None,
            observations=(),
            unresolved_findings=(),
            promoted_evidence=(),
            reference_crosschecks=(),
        )


def test_bundle_rejects_empty_bundle_version() -> None:
    with pytest.raises(ValueError, match="bundle_version"):
        ResearchEvidenceBundle(
            bundle_id="BUNDLE-001",
            bundle_version="",
            research_target=_target(),
            research_job_id=None,
            activity_id=None,
            observations=(),
            unresolved_findings=(),
            promoted_evidence=(),
            reference_crosschecks=(),
        )


# ---------------------------------------------------------------------------
# Issue 1 — fail-closed validation for all string scope dimensions
# ---------------------------------------------------------------------------


def test_applicability_rejects_empty_hull_number_from() -> None:
    with pytest.raises(ValueError, match="hull_number_from"):
        ObservationApplicability(
            first_year=None,
            last_year=None,
            hull_number_from="",
            hull_number_to=None,
            market_or_region=None,
            named_variant_hint=None,
            design_option_hints=None,
            operating_state_hint=None,
            individual_hull_or_listing_ref=None,
            unknown_or_unbounded=True,
        )


def test_applicability_rejects_empty_hull_number_to() -> None:
    with pytest.raises(ValueError, match="hull_number_to"):
        ObservationApplicability(
            first_year=None,
            last_year=None,
            hull_number_from=None,
            hull_number_to="",
            market_or_region=None,
            named_variant_hint=None,
            design_option_hints=None,
            operating_state_hint=None,
            individual_hull_or_listing_ref=None,
            unknown_or_unbounded=True,
        )


def test_applicability_rejects_empty_market_or_region() -> None:
    with pytest.raises(ValueError, match="market_or_region"):
        ObservationApplicability(
            first_year=None,
            last_year=None,
            hull_number_from=None,
            hull_number_to=None,
            market_or_region="",
            named_variant_hint=None,
            design_option_hints=None,
            operating_state_hint=None,
            individual_hull_or_listing_ref=None,
            unknown_or_unbounded=True,
        )


def test_applicability_rejects_empty_named_variant_hint() -> None:
    with pytest.raises(ValueError, match="named_variant_hint"):
        ObservationApplicability(
            first_year=None,
            last_year=None,
            hull_number_from=None,
            hull_number_to=None,
            market_or_region=None,
            named_variant_hint="",
            design_option_hints=None,
            operating_state_hint=None,
            individual_hull_or_listing_ref=None,
            unknown_or_unbounded=True,
        )


def test_applicability_rejects_empty_operating_state_hint() -> None:
    with pytest.raises(ValueError, match="operating_state_hint"):
        ObservationApplicability(
            first_year=None,
            last_year=None,
            hull_number_from=None,
            hull_number_to=None,
            market_or_region=None,
            named_variant_hint=None,
            design_option_hints=None,
            operating_state_hint="",
            individual_hull_or_listing_ref=None,
            unknown_or_unbounded=True,
        )


def test_applicability_accepts_non_empty_string_scope_dimensions() -> None:
    # All string scope dimensions accept non-empty values without error.
    app = ObservationApplicability(
        first_year=None,
        last_year=None,
        hull_number_from="H001",
        hull_number_to="H999",
        market_or_region="US",
        named_variant_hint="shoal draft",
        design_option_hints=("lead_keel",),
        operating_state_hint="mast_up",
        individual_hull_or_listing_ref="LISTING-001",
        unknown_or_unbounded=False,
    )
    assert app.hull_number_from == "H001"
    assert app.hull_number_to == "H999"
    assert app.market_or_region == "US"
    assert app.named_variant_hint == "shoal draft"
    assert app.operating_state_hint == "mast_up"
    assert app.individual_hull_or_listing_ref == "LISTING-001"
