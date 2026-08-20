"""Pre-canonical ResearchObservation, ResearchEvidenceBundle and promotion — SLICE-0012.

Implements the accepted SLICE-0012 contracts:

- ResearchObservation: immutable source-linked observation that does NOT require
  a canonical ProvenanceSubject (pre-canonical, pre-identity-resolution stage);
- ReferenceCheckOutcome / ReferenceCrosscheck: structurally separate reference
  comparison entries that cannot be promoted to ResearchObservation or FieldEvidence;
- UnresolvedFinding: explicit unresolved/review finding not yet at FieldResolution;
- ResearchEvidenceBundle: versioned machine-ingestible research handoff bundle;
- promote_to_field_evidence: explicit deterministic promotion from ResearchObservation
  to FieldEvidenceV3 after the caller supplies a stable canonical ProvenanceSubject;
- migrate_evidence_v02_to_v03: lossless v0.2 → v0.3 adapter that maps missing new
  semantics to explicit unknown/unbounded, never to nominal or global defaults.

Does not implement: identity resolution, fuzzy matching, automatic FieldResolution,
conflict resolution, authority ranking, network acquisition, PostgreSQL, ORM.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import StrEnum

from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
    FieldEvidence,
    FieldEvidenceV3,
    JsonPointer,
    NormalizedCandidate,
    ObservationApplicability,
    ProducerMetadata,
    ProvenanceSubject,
    RawObservation,
    ResearchContext,
    SourceLocator,
    SubjectKind,
)
from hullq.research.jobs import ResearchTarget

__all__ = [
    "PromotionError",
    "ReferenceCheckOutcome",
    "ReferenceCrosscheck",
    "ResearchEvidenceBundle",
    "ResearchObservation",
    "UnresolvedFinding",
    "UnresolvedFindingSeverity",
    "migrate_evidence_v02_to_v03",
    "promote_to_field_evidence",
]


# ---------------------------------------------------------------------------
# Reference crosscheck vocabulary
# Matches RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1.json $defs.reference_crosscheck.
# Tests enforce parity.
# ---------------------------------------------------------------------------


class ReferenceCheckOutcome(StrEnum):
    """Outcome of a reference comparison crosscheck.

    These values describe QA comparison results; they are structurally separate
    from ResearchObservation and cannot be promoted to FieldEvidence.
    """

    MATCH = "match"
    PARTIAL_MATCH = "partial_match"
    CONFLICT = "conflict"
    DEFINITION_OR_BASIS_DIFFERENCE = "definition_or_basis_difference"
    IDENTITY_DISAMBIGUATION_REQUIRED = "identity_disambiguation_required"
    REFERENCE_INCOMPLETE = "reference_incomplete"
    NO_REFERENCE_RECORD_FOUND = "no_reference_record_found"
    NOT_CHECKED = "not_checked"


class UnresolvedFindingSeverity(StrEnum):
    """Severity of an unresolved bundle finding."""

    BLOCKING = "blocking"
    REVIEW = "review"
    INFORMATIONAL = "informational"


# ---------------------------------------------------------------------------
# ReferenceCrosscheck
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferenceCrosscheck:
    """Structurally separate reference comparison entry.

    Exists specifically so QA comparison cannot leak into source provenance.
    Has no evidence_id and cannot satisfy a FieldResolution evidence reference.
    Must not store reference field values — only the comparison outcome and notes.
    """

    crosscheck_id: str
    reference_source_id: str
    topic_or_field: str | None
    outcome: ReferenceCheckOutcome
    notes: str | None

    def __post_init__(self) -> None:
        if not self.crosscheck_id:
            raise ValueError("ReferenceCrosscheck.crosscheck_id must be non-empty")
        if not self.reference_source_id:
            raise ValueError("ReferenceCrosscheck.reference_source_id must be non-empty")


# ---------------------------------------------------------------------------
# UnresolvedFinding
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UnresolvedFinding:
    """Explicit unresolved or review finding not yet at FieldResolution stage.

    ``related_observation_ids`` is snapshot-safe as a frozenset.
    """

    finding_id: str
    topic: str
    description: str
    related_observation_ids: frozenset[str]
    severity: UnresolvedFindingSeverity

    def __post_init__(self) -> None:
        if not self.finding_id:
            raise ValueError("UnresolvedFinding.finding_id must be non-empty")
        if not self.topic:
            raise ValueError("UnresolvedFinding.topic must be non-empty")
        if not self.description:
            raise ValueError("UnresolvedFinding.description must be non-empty")
        # Snapshot safety: freeze any mutable set passed by caller.
        object.__setattr__(self, "related_observation_ids", frozenset(self.related_observation_ids))


# ---------------------------------------------------------------------------
# ResearchObservation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchObservation:
    """Immutable pre-canonical source-linked observation.

    Does NOT require a canonical ``ProvenanceSubject``. The absence of a canonical
    subject is normal — not an error — and must not trigger hidden identity inference.

    ``intended_subject_kind_hint`` and ``intended_field_pointer`` are research mapping
    candidates only. They do not assert canonical identity and do not themselves write
    any canonical object. They are validated during explicit promotion.

    ``raw`` and ``normalized_candidate`` are independent snapshot-safe value objects
    (deep-copied by their own ``__post_init__``).
    """

    observation_id: str
    research_target: ResearchTarget
    source_id: str
    source_locator: SourceLocator
    raw: RawObservation
    normalized_candidate: NormalizedCandidate | None
    evidence_type: EvidenceType
    claim_semantics: ClaimSemantics
    applicability: ObservationApplicability
    producer: ProducerMetadata
    research_context: ResearchContext
    observed_at: str
    confidence: ConfidenceLevel
    supersedes_observation_id: str | None
    intended_subject_kind_hint: SubjectKind | None
    intended_field_pointer: JsonPointer | None
    notes: str | None

    def __post_init__(self) -> None:
        if not self.observation_id:
            raise ValueError("ResearchObservation.observation_id must be non-empty")
        if not self.source_id:
            raise ValueError("ResearchObservation.source_id must be non-empty")
        if not self.observed_at:
            raise ValueError("ResearchObservation.observed_at must be non-empty")
        # Snapshot safety: deep-copy the research_target snapshot so caller
        # mutation cannot alter the captured identity.
        object.__setattr__(self, "research_target", copy.copy(self.research_target))


# ---------------------------------------------------------------------------
# ResearchEvidenceBundle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchEvidenceBundle:
    """Versioned machine-ingestible research handoff bundle.

    Does NOT require canonical BoatModel or BoatDesign IDs. Supports partial
    research and identity ambiguity. The reference_crosschecks section is
    structurally separate from observations and promoted evidence.

    All collection fields are snapshot-safe tuples.
    """

    bundle_id: str
    bundle_version: str
    research_target: ResearchTarget
    research_job_id: str | None
    activity_id: str | None
    observations: tuple[ResearchObservation, ...]
    unresolved_findings: tuple[UnresolvedFinding, ...]
    promoted_evidence: tuple[FieldEvidenceV3, ...]
    reference_crosschecks: tuple[ReferenceCrosscheck, ...]

    def __post_init__(self) -> None:
        if not self.bundle_id:
            raise ValueError("ResearchEvidenceBundle.bundle_id must be non-empty")
        if not self.bundle_version:
            raise ValueError("ResearchEvidenceBundle.bundle_version must be non-empty")
        # Snapshot safety: freeze all collections.
        object.__setattr__(self, "observations", tuple(self.observations))
        object.__setattr__(self, "unresolved_findings", tuple(self.unresolved_findings))
        object.__setattr__(self, "promoted_evidence", tuple(self.promoted_evidence))
        object.__setattr__(self, "reference_crosschecks", tuple(self.reference_crosschecks))


# ---------------------------------------------------------------------------
# Promotion — ResearchObservation → FieldEvidenceV3
# ---------------------------------------------------------------------------


class PromotionError(ValueError):
    """Raised when a ResearchObservation cannot be promoted to FieldEvidenceV3.

    Promotion fails closed: any contradiction between the observation's research
    hints and the caller-supplied canonical subject or field pointer is a hard
    error rather than a silent resolution.
    """


def promote_to_field_evidence(
    observation: ResearchObservation,
    subject: ProvenanceSubject,
    evidence_id: str,
    field_pointer: JsonPointer,
    supersedes_evidence_id: str | None = None,
) -> FieldEvidenceV3:
    """Promote a ResearchObservation to a FieldEvidenceV3.

    The caller MUST supply a stable canonical ``ProvenanceSubject`` obtained after
    explicit identity resolution. This function does NOT perform identity resolution,
    fuzzy matching, or FieldResolution. It does NOT create or mutate canonical objects.

    All provenance fields (raw snapshot, normalized candidate, source locator, producer,
    research context, confidence, claim semantics, applicability) are preserved losslessly.

    Raises ``PromotionError`` if:
    - ``evidence_id`` is empty;
    - ``observation.intended_subject_kind_hint`` contradicts ``subject.kind``;
    - ``observation.intended_field_pointer`` contradicts ``field_pointer``.

    ``observed_at`` is preserved from the observation and must not be reused as
    applicability time.
    """
    if not evidence_id:
        raise PromotionError("evidence_id must be non-empty for promotion")

    # Fail closed on subject-kind contradiction.
    if (
        observation.intended_subject_kind_hint is not None
        and observation.intended_subject_kind_hint != subject.kind
    ):
        raise PromotionError(
            f"Observation {observation.observation_id!r}: "
            f"intended_subject_kind_hint {observation.intended_subject_kind_hint!r} "
            f"contradicts supplied subject kind {subject.kind!r}; promotion blocked"
        )

    # Fail closed on field pointer contradiction.
    if (
        observation.intended_field_pointer is not None
        and observation.intended_field_pointer != field_pointer
    ):
        raise PromotionError(
            f"Observation {observation.observation_id!r}: "
            f"intended_field_pointer {observation.intended_field_pointer!r} "
            f"contradicts supplied field_pointer {field_pointer!r}; promotion blocked"
        )

    return FieldEvidenceV3(
        evidence_id=evidence_id,
        subject=subject,
        field_pointer=field_pointer,
        source_id=observation.source_id,
        source_locator=observation.source_locator,
        raw=observation.raw,
        normalized_candidate=observation.normalized_candidate,
        evidence_type=observation.evidence_type,
        producer=observation.producer,
        research_context=observation.research_context,
        observed_at=observation.observed_at,
        confidence=observation.confidence,
        supersedes_evidence_id=supersedes_evidence_id,
        notes=observation.notes,
        claim_semantics=observation.claim_semantics,
        applicability=observation.applicability,
    )


# ---------------------------------------------------------------------------
# v0.2 → v0.3 migration adapter
# ---------------------------------------------------------------------------


def migrate_evidence_v02_to_v03(
    evidence: FieldEvidence,
    claim_semantics: ClaimSemantics | None = None,
    applicability: ObservationApplicability | None = None,
) -> FieldEvidenceV3:
    """Lossless v0.2 FieldEvidence → v0.3 FieldEvidenceV3 adapter.

    Maps absent ``claim_semantics`` to ``ClaimSemantics.UNKNOWN`` — never to
    ``NOMINAL_DESIGN_VALUE`` or any other specific claim.

    Maps absent ``applicability`` to an explicitly unknown/unbounded scope
    (``unknown_or_unbounded=True``) — never to a global or all-production assertion.

    All raw/normalized/provenance fields are preserved losslessly.
    """
    resolved_claim = claim_semantics if claim_semantics is not None else ClaimSemantics.UNKNOWN
    resolved_applicability = (
        applicability
        if applicability is not None
        else ObservationApplicability(
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
    )
    return FieldEvidenceV3(
        evidence_id=evidence.evidence_id,
        subject=evidence.subject,
        field_pointer=evidence.field_pointer,
        source_id=evidence.source_id,
        source_locator=evidence.source_locator,
        raw=evidence.raw,
        normalized_candidate=evidence.normalized_candidate,
        evidence_type=evidence.evidence_type,
        producer=evidence.producer,
        research_context=evidence.research_context,
        observed_at=evidence.observed_at,
        confidence=evidence.confidence,
        supersedes_evidence_id=evidence.supersedes_evidence_id,
        notes=evidence.notes,
        claim_semantics=resolved_claim,
        applicability=resolved_applicability,
    )
