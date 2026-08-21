"""Controlled Wikidata Tier-0 identity bootstrap — SLICE-0017.

Implements the deterministic classification, opaque HullQ-ID minting, and
research/canonical materialization logic for the first controlled broad
identity bootstrap described in
``docs/slices/SLICE-0017-controlled-wikidata-tier0-identity-bootstrap.md``.

This module is pure logic: it does not perform network acquisition (that
remains in ``hullq.sources.wikidata``) and does not open a database
connection (that remains in ``hullq.persistence``). Given already-acquired
``WikidataEntityData`` records, it deterministically classifies each Wikidata
sailboat-class candidate into exactly one bootstrap decision, mints a stable
opaque HullQ ID for safe candidates, and materializes the retained
ResearchObservation / ResearchEvidenceBundle / CanonicalIdentityAdmission
objects needed for persistence.

Explicitly does NOT:
- infer Brand, Organization, BoatDesign generation, NamedVariant or
  DesignOption identity from any Wikidata statement;
- perform fuzzy/heuristic identity resolution or forced merge/split;
- fabricate a canonical value from a missing/absent source label;
- invent a post-hoc admission-rate threshold.
"""

from __future__ import annotations

import unicodedata
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
    JsonPointer,
    ObservationApplicability,
    ProducerKind,
    ProducerMetadata,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    SourceLocator,
    SubjectKind,
)
from hullq.persistence.identity_types import CanonicalEvidenceLink, CanonicalIdentityAdmission
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import (
    ResearchEvidenceBundle,
    ResearchObservation,
    UnresolvedFinding,
    UnresolvedFindingSeverity,
)
from hullq.sources.wikidata import WIKIDATA_SOURCE_ID, WikidataEntityData

__all__ = [
    "BOOTSTRAP_MANIFEST_VERSION",
    "BOOTSTRAP_PRODUCER_IDENTIFIER",
    "BOOTSTRAP_PRODUCER_VERSION",
    "BOOTSTRAP_REQUESTED_LIMIT",
    "BOOTSTRAP_SAFETY_CEILING",
    "BootstrapCandidate",
    "BootstrapDecision",
    "BootstrapReasonCode",
    "CrosswalkConflictError",
    "build_admission",
    "build_bundle",
    "build_manifest",
    "candidate_from_manifest_dict",
    "candidate_to_manifest_dict",
    "classify_candidates",
    "mint_hullq_id",
    "validate_crosswalk_consistency",
]

# ---------------------------------------------------------------------------
# Bounds — mirrors SLICE-0017's binding candidate-set boundary.
# ---------------------------------------------------------------------------

# Requested bootstrap candidate count (runner-level policy choice).
BOOTSTRAP_REQUESTED_LIMIT = 1000

# Hard bootstrap safety ceiling; must never exceed
# hullq.sources.wikidata.WIKIDATA_BOOTSTRAP_SAFETY_CEILING.
BOOTSTRAP_SAFETY_CEILING = 1500

BOOTSTRAP_MANIFEST_VERSION = "0017-v1"
BOOTSTRAP_PRODUCER_IDENTIFIER = "hullq-wikidata-bootstrap"
BOOTSTRAP_PRODUCER_VERSION = "SLICE-0017-v1"

# HullQ BoatModel ID prefix. A static namespace label, not a QID/name
# derivation: per IDENTITY_MODEL.v0.2 §2.3 the minted ID must be independent
# of display name or source ID; the prefix identifies only the minting
# namespace (this bootstrap), never the specific candidate.
_HULLQ_ID_PREFIX = "BM_WDT0_"


class BootstrapDecision(StrEnum):
    """Deterministic Tier-0 admission outcome for one Wikidata candidate."""

    AUTO_ADMIT = "auto_admit"
    REVIEW_REQUIRED = "review_required"
    NOT_ADMITTED = "not_admitted"


class BootstrapReasonCode(StrEnum):
    """Deterministic reason classes for a bootstrap decision.

    Callers and reports MUST use these codes rather than free-form prose to
    decide/report behavior (mirrors the DecisionReason pattern in
    ``hullq.sources.rights``).
    """

    OK = "ok"
    MISSING_LABEL = "missing_label"
    NAME_COLLISION = "name_collision"
    CROSSWALK_CONFLICT = "crosswalk_conflict"


class CrosswalkConflictError(ValueError):
    """Raised when a QID -> HullQ-ID crosswalk contains an inconsistent mapping.

    An existing QID MUST NOT be silently reminted; a conflicting retained
    crosswalk MUST fail closed rather than pick either candidate ID.
    """


def mint_hullq_id() -> str:
    """Mint a new stable opaque HullQ BoatModel ID.

    The returned ID does not encode or derive from any candidate's QID or
    display name — it is a UUIDv4-style opaque identifier under a fixed
    namespace prefix, per IDENTITY_MODEL.v0.2 §2.3 and the SLICE-0017 stable
    HullQ-ID minting contract.
    """
    return f"{_HULLQ_ID_PREFIX}{uuid.uuid4().hex}"


def _normalize_label_for_collision(label: str) -> str:
    """Deterministic case/whitespace-insensitive projection used only to
    detect same-name/search-projection collisions within one candidate set.

    Never mutates or replaces the preserved raw ``preferred_label``.
    """
    folded = unicodedata.normalize("NFC", label).casefold()
    return " ".join(folded.split())


# ---------------------------------------------------------------------------
# BootstrapCandidate — the single retained-manifest-row representation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BootstrapCandidate:
    """One retained bootstrap manifest row.

    Carries exactly the facts needed to (a) audit the bootstrap decision and
    (b) deterministically re-materialize the same ResearchObservation /
    ResearchEvidenceBundle / CanonicalIdentityAdmission objects on replay,
    without any network access.
    """

    qid: str
    retrieved_at: str
    preferred_label: str | None
    aliases: tuple[str, ...]
    hullq_id: str | None
    decision: BootstrapDecision
    reason_codes: tuple[BootstrapReasonCode, ...]
    observation_id: str | None
    bundle_id: str | None
    bundle_version: str | None
    evidence_link_id: str | None

    def __post_init__(self) -> None:
        if not self.qid:
            raise ValueError("BootstrapCandidate.qid must be non-empty")
        if not self.retrieved_at:
            raise ValueError("BootstrapCandidate.retrieved_at must be non-empty")
        object.__setattr__(self, "aliases", tuple(self.aliases))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        if self.decision == BootstrapDecision.AUTO_ADMIT:
            if not self.hullq_id:
                raise ValueError("AUTO_ADMIT candidate must have a non-empty hullq_id")
            if not self.observation_id or not self.bundle_id or not self.evidence_link_id:
                raise ValueError(
                    "AUTO_ADMIT candidate must have observation_id, bundle_id and "
                    "evidence_link_id set"
                )


# ---------------------------------------------------------------------------
# Classification — pure, deterministic, no network/database access
# ---------------------------------------------------------------------------


def classify_candidates(
    entities: list[WikidataEntityData],
    *,
    retrieved_at: str,
    id_factory: Any = mint_hullq_id,
    existing_crosswalk: dict[str, str] | None = None,
) -> list[BootstrapCandidate]:
    """Deterministically classify acquired Wikidata entities into bootstrap decisions.

    ``existing_crosswalk`` (QID -> HullQ ID) lets a caller reuse previously
    minted IDs for QIDs it has already admitted in an earlier run; a QID
    present in the crosswalk always reuses its retained ID rather than
    minting a new one. New QIDs are minted via ``id_factory`` exactly once.

    Deterministic same-name/search-projection collisions (case/whitespace
    normalized) within *entities* route every colliding QID to
    ``REVIEW_REQUIRED`` rather than a forced merge or an arbitrary pick.

    An empty/missing preferred label cannot auto-admit and produces no
    observation, per IDENTITY_MODEL.v0.2 and REQ-ID-012: there is no source
    identity claim to preserve.
    """
    crosswalk = dict(existing_crosswalk or {})

    # First pass: detect same-name collisions across the whole candidate set.
    label_groups: dict[str, list[str]] = {}
    for entity in entities:
        if entity.label:
            key = _normalize_label_for_collision(entity.label)
            label_groups.setdefault(key, []).append(entity.qid)
    colliding_qids: set[str] = {
        qid for group in label_groups.values() if len(group) > 1 for qid in group
    }

    candidates: list[BootstrapCandidate] = []
    for entity in entities:
        qid = entity.qid
        label = entity.label

        if not label:
            candidates.append(
                BootstrapCandidate(
                    qid=qid,
                    retrieved_at=retrieved_at,
                    preferred_label=None,
                    aliases=tuple(entity.aliases),
                    hullq_id=None,
                    decision=BootstrapDecision.NOT_ADMITTED,
                    reason_codes=(BootstrapReasonCode.MISSING_LABEL,),
                    observation_id=None,
                    bundle_id=None,
                    bundle_version=None,
                    evidence_link_id=None,
                )
            )
            continue

        observation_id = f"OBS-WD-TIER0-{qid}"
        bundle_id = f"BUNDLE-WD-TIER0-{qid}"
        bundle_version = "1"

        if qid in colliding_qids:
            candidates.append(
                BootstrapCandidate(
                    qid=qid,
                    retrieved_at=retrieved_at,
                    preferred_label=label,
                    aliases=tuple(entity.aliases),
                    hullq_id=None,
                    decision=BootstrapDecision.REVIEW_REQUIRED,
                    reason_codes=(BootstrapReasonCode.NAME_COLLISION,),
                    observation_id=observation_id,
                    bundle_id=bundle_id,
                    bundle_version=bundle_version,
                    evidence_link_id=None,
                )
            )
            continue

        hullq_id = crosswalk.get(qid)
        if hullq_id is None:
            hullq_id = id_factory()
            crosswalk[qid] = hullq_id

        candidates.append(
            BootstrapCandidate(
                qid=qid,
                retrieved_at=retrieved_at,
                preferred_label=label,
                aliases=tuple(entity.aliases),
                hullq_id=hullq_id,
                decision=BootstrapDecision.AUTO_ADMIT,
                reason_codes=(BootstrapReasonCode.OK,),
                observation_id=observation_id,
                bundle_id=bundle_id,
                bundle_version=bundle_version,
                evidence_link_id=f"LINK-WD-TIER0-{qid}",
            )
        )

    return candidates


def validate_crosswalk_consistency(candidates: list[BootstrapCandidate]) -> None:
    """Fail closed if the retained QID -> HullQ-ID crosswalk is inconsistent.

    Raises ``CrosswalkConflictError`` if the same QID appears more than once
    with different non-null ``hullq_id`` values, or if any two distinct QIDs
    share the same ``hullq_id``. An existing QID MUST NOT be silently
    reminted, and a HullQ ID MUST NOT address more than one QID.
    """
    qid_to_id: dict[str, str] = {}
    id_to_qid: dict[str, str] = {}
    for candidate in candidates:
        if candidate.hullq_id is None:
            continue
        prior_id = qid_to_id.get(candidate.qid)
        if prior_id is not None and prior_id != candidate.hullq_id:
            raise CrosswalkConflictError(
                f"QID {candidate.qid!r} maps to conflicting HullQ IDs "
                f"{prior_id!r} and {candidate.hullq_id!r} in the same manifest."
            )
        qid_to_id[candidate.qid] = candidate.hullq_id

        prior_qid = id_to_qid.get(candidate.hullq_id)
        if prior_qid is not None and prior_qid != candidate.qid:
            raise CrosswalkConflictError(
                f"HullQ ID {candidate.hullq_id!r} is addressed by conflicting QIDs "
                f"{prior_qid!r} and {candidate.qid!r} in the same manifest."
            )
        id_to_qid[candidate.hullq_id] = candidate.qid


# ---------------------------------------------------------------------------
# Materialization — deterministic ResearchObservation / bundle / admission
# ---------------------------------------------------------------------------


def _producer() -> ProducerMetadata:
    return ProducerMetadata(
        kind=ProducerKind.DETERMINISTIC_TOOL,
        identifier=BOOTSTRAP_PRODUCER_IDENTIFIER,
        version=BOOTSTRAP_PRODUCER_VERSION,
        model=None,
        prompt_or_rule_version=None,
    )


def _unbounded_applicability() -> ObservationApplicability:
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


def _build_observation(candidate: BootstrapCandidate) -> ResearchObservation:
    assert candidate.preferred_label is not None
    assert candidate.observation_id is not None
    return ResearchObservation(
        observation_id=candidate.observation_id,
        research_target=ResearchTarget(
            manufacturer=None, model=candidate.preferred_label, first_built=None
        ),
        source_id=WIKIDATA_SOURCE_ID,
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=candidate.qid
        ),
        raw=RawObservation(
            kind=RawObservationKind.STRUCTURED_RECORD,
            value={"qid": candidate.qid, "label": candidate.preferred_label},
            unit=None,
            excerpt=None,
        ),
        normalized_candidate=None,
        evidence_type=EvidenceType.API_RECORD,
        claim_semantics=ClaimSemantics.IDENTITY_OR_CHRONOLOGY_CLAIM,
        applicability=_unbounded_applicability(),
        producer=_producer(),
        research_context=ResearchContext(research_job_id=None, activity_id="SLICE-0017-BOOTSTRAP"),
        observed_at=candidate.retrieved_at,
        confidence=ConfidenceLevel.MEDIUM,
        supersedes_observation_id=None,
        intended_subject_kind_hint=SubjectKind.BOAT_MODEL,
        intended_field_pointer=JsonPointer("/canonical_name"),
        notes=None,
    )


def build_bundle(candidate: BootstrapCandidate) -> ResearchEvidenceBundle | None:
    """Build the retained ResearchEvidenceBundle for one candidate.

    Returns ``None`` for a candidate with no preserved observation (currently
    only ``MISSING_LABEL`` NOT_ADMITTED candidates, which have no source
    identity claim to record).
    """
    if candidate.preferred_label is None or candidate.observation_id is None:
        return None
    assert candidate.bundle_id is not None
    assert candidate.bundle_version is not None

    observation = _build_observation(candidate)
    findings: tuple[UnresolvedFinding, ...] = ()
    if candidate.decision != BootstrapDecision.AUTO_ADMIT:
        reason_text = ", ".join(str(r) for r in candidate.reason_codes)
        findings = (
            UnresolvedFinding(
                finding_id=f"FIND-WD-TIER0-{candidate.qid}",
                topic="bootstrap_identity_admission",
                description=(
                    f"Wikidata candidate {candidate.qid!r} routed to "
                    f"{candidate.decision!s} ({reason_text})."
                ),
                related_observation_ids=frozenset({observation.observation_id}),
                severity=UnresolvedFindingSeverity.REVIEW,
            ),
        )

    return ResearchEvidenceBundle(
        bundle_id=candidate.bundle_id,
        bundle_version=candidate.bundle_version,
        research_target=observation.research_target,
        research_job_id=None,
        activity_id="SLICE-0017-BOOTSTRAP",
        observations=(observation,),
        unresolved_findings=findings,
        promoted_evidence=(),
        reference_crosschecks=(),
    )


def build_admission(candidate: BootstrapCandidate) -> CanonicalIdentityAdmission | None:
    """Build the CanonicalIdentityAdmission for one AUTO_ADMIT candidate.

    Returns ``None`` for any candidate that is not AUTO_ADMIT: a
    REVIEW_REQUIRED or NOT_ADMITTED candidate MUST NOT be persisted as a
    canonical entity.
    """
    if candidate.decision != BootstrapDecision.AUTO_ADMIT:
        return None
    assert candidate.hullq_id is not None
    assert candidate.observation_id is not None
    assert candidate.evidence_link_id is not None

    aliases = [
        {
            "id": f"ALIAS-{candidate.hullq_id}-{i}",
            "alias_class": "source_spelling",
            "name": alias_name,
        }
        for i, alias_name in enumerate(candidate.aliases)
    ]
    boat_model_payload: dict[str, Any] = {
        "schema_version": "0.2",
        "id": candidate.hullq_id,
        "canonical_name": candidate.preferred_label,
        "aliases": aliases,
        "brand_relationships": [],
        "first_built": None,
        "last_built": None,
        "boat_design_ids": [],
    }
    link = CanonicalEvidenceLink(
        link_id=candidate.evidence_link_id,
        entity_kind=SubjectKind.BOAT_MODEL,
        entity_id=candidate.hullq_id,
        observation_id=candidate.observation_id,
        evidence_id=None,
        notes=None,
    )
    return CanonicalIdentityAdmission(boat_models=(boat_model_payload,), evidence_links=(link,))


# ---------------------------------------------------------------------------
# Manifest (de)serialization — JSON-primitive round trip
# ---------------------------------------------------------------------------


def candidate_to_manifest_dict(candidate: BootstrapCandidate) -> dict[str, Any]:
    """Convert a BootstrapCandidate to a JSON-serializable manifest row."""
    return {
        "qid": candidate.qid,
        "retrieved_at": candidate.retrieved_at,
        "preferred_label": candidate.preferred_label,
        "aliases": list(candidate.aliases),
        "hullq_id": candidate.hullq_id,
        "decision": str(candidate.decision),
        "reason_codes": [str(r) for r in candidate.reason_codes],
        "observation_id": candidate.observation_id,
        "bundle_id": candidate.bundle_id,
        "bundle_version": candidate.bundle_version,
        "evidence_link_id": candidate.evidence_link_id,
    }


def candidate_from_manifest_dict(row: dict[str, Any]) -> BootstrapCandidate:
    """Reconstruct a BootstrapCandidate from a retained manifest row.

    Deterministic and offline: performs no network access and does not mint
    a new HullQ ID — the retained ``hullq_id`` (if any) is reused exactly.
    """
    return BootstrapCandidate(
        qid=row["qid"],
        retrieved_at=row["retrieved_at"],
        preferred_label=row["preferred_label"],
        aliases=tuple(row.get("aliases") or ()),
        hullq_id=row["hullq_id"],
        decision=BootstrapDecision(row["decision"]),
        reason_codes=tuple(BootstrapReasonCode(r) for r in row.get("reason_codes") or ()),
        observation_id=row["observation_id"],
        bundle_id=row["bundle_id"],
        bundle_version=row["bundle_version"],
        evidence_link_id=row["evidence_link_id"],
    )


@dataclass(frozen=True)
class _ManifestCounts:
    candidates_processed: int
    auto_admit: int
    review_required: int
    not_admitted: int
    reason_breakdown: dict[str, int] = field(default_factory=dict)


def _counts(candidates: list[BootstrapCandidate]) -> _ManifestCounts:
    reason_breakdown: dict[str, int] = {}
    for candidate in candidates:
        for reason in candidate.reason_codes:
            reason_breakdown[str(reason)] = reason_breakdown.get(str(reason), 0) + 1
    return _ManifestCounts(
        candidates_processed=len(candidates),
        auto_admit=sum(1 for c in candidates if c.decision == BootstrapDecision.AUTO_ADMIT),
        review_required=sum(
            1 for c in candidates if c.decision == BootstrapDecision.REVIEW_REQUIRED
        ),
        not_admitted=sum(1 for c in candidates if c.decision == BootstrapDecision.NOT_ADMITTED),
        reason_breakdown=reason_breakdown,
    )


def build_manifest(
    candidates: list[BootstrapCandidate],
    *,
    generated_at: str,
    requested_limit: int,
    unique_qids_returned: int,
    retrieval_count: int,
    extracted_record_count: int,
    target_reached: bool,
) -> dict[str, Any]:
    """Build the full versioned, JSON-serializable bootstrap manifest document.

    Validates crosswalk consistency before returning (fails closed on a
    conflicting QID -> HullQ-ID mapping).
    """
    validate_crosswalk_consistency(candidates)
    counts = _counts(candidates)
    return {
        "manifest_version": BOOTSTRAP_MANIFEST_VERSION,
        "source_id": WIKIDATA_SOURCE_ID,
        "generated_at": generated_at,
        "requested_limit": requested_limit,
        "safety_ceiling": BOOTSTRAP_SAFETY_CEILING,
        "discovery": {
            "unique_qids_returned": unique_qids_returned,
            "candidates_processed": len(candidates),
            "target_reached": target_reached,
        },
        "usage_metrics": {
            "retrieval_count": retrieval_count,
            "extracted_record_count": extracted_record_count,
        },
        "candidates": [candidate_to_manifest_dict(c) for c in candidates],
        "counts": {
            "candidates_processed": counts.candidates_processed,
            "auto_admit": counts.auto_admit,
            "review_required": counts.review_required,
            "not_admitted": counts.not_admitted,
            "reason_breakdown": counts.reason_breakdown,
        },
    }
