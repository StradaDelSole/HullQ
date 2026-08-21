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

import hashlib
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from hullq.domain.identity import AliasClass, IdentityAlias, generate_search_keys
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
from hullq.sources.wikidata import (
    BOOTSTRAP_ENTITY_API_ENDPOINT,
    BOOTSTRAP_ENTITY_API_VERSION,
    BOOTSTRAP_SPARQL_ENDPOINT,
    BOOTSTRAP_SPARQL_QUERY_VERSION,
    WIKIDATA_SOURCE_ID,
    WikidataEntityData,
)

__all__ = [
    "BOOTSTRAP_MANIFEST_VERSION",
    "BOOTSTRAP_PRODUCER_IDENTIFIER",
    "BOOTSTRAP_PRODUCER_VERSION",
    "BOOTSTRAP_REQUESTED_LIMIT",
    "BOOTSTRAP_SAFETY_CEILING",
    "BootstrapCandidate",
    "BootstrapDecision",
    "BootstrapReasonCode",
    "CollisionCluster",
    "CrosswalkConflictError",
    "build_admission",
    "build_bundle",
    "build_manifest",
    "candidate_from_manifest_dict",
    "candidate_to_manifest_dict",
    "classify_candidates",
    "compute_collision_clusters",
    "load_crosswalk_from_manifest",
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

BOOTSTRAP_MANIFEST_VERSION = "0017-v3"
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


def _stable_alias_id(name: str) -> str:
    """Deterministic, content-derived alias ID.

    Depends only on the alias's own text, never on its position within the
    source alias list or on any other alias's content. Per IDENTITY_MODEL.v0.2
    §4, persistent provenance MUST NOT depend on fragile array position:
    reordering the same alias set MUST NOT change the ID assigned to any
    individual alias. Alias IDs need only be unique within one owning
    entity's alias table (the persistence layer keys on
    ``(boat_model_id, alias_id)``), so a content hash is sufficient scope.
    """
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]
    return f"ALIAS-{digest}"


def _search_keys_for_candidate(label: str, aliases: Sequence[str]) -> frozenset[str]:
    """The complete accepted deterministic search-key projection for one
    candidate's label + aliases, reusing the single accepted HullQ projection
    (``hullq.domain.identity.generate_search_keys``) rather than a weaker
    parallel normalization.
    """
    alias_objs = tuple(
        IdentityAlias(id=_stable_alias_id(name), alias_class=AliasClass.SOURCE_SPELLING, name=name)
        for name in aliases
    )
    return generate_search_keys(label, alias_objs)


@dataclass(frozen=True)
class CollisionCluster:
    """A group of two or more distinct QIDs whose accepted deterministic
    search-key projections overlap on at least one key.

    ``shared_keys`` lists every search key that caused at least one pairwise
    union inside this cluster, for audit purposes. Every member QID MUST
    route to ``REVIEW_REQUIRED``; none may be auto-admitted or force-merged.
    """

    qids: tuple[str, ...]
    shared_keys: tuple[str, ...]


def compute_collision_clusters(entities: list[WikidataEntityData]) -> list[CollisionCluster]:
    """Deterministically compute complete same-search-key collision clusters.

    Two candidates collide when the accepted deterministic search-key
    projection (canonical label + retained same-entity aliases, per
    ``generate_search_keys``) of one overlaps that of the other on at least
    one key. Collision is transitive: if A collides with B on one key and B
    collides with C on a different key, A/B/C form one cluster. Candidates
    with no label are excluded (handled separately as ``MISSING_LABEL``).
    """
    labeled = [e for e in entities if e.label]
    keys_by_qid: dict[str, frozenset[str]] = {
        e.qid: _search_keys_for_candidate(e.label, e.aliases)  # type: ignore[arg-type]
        for e in labeled
    }

    key_to_qids: dict[str, list[str]] = {}
    for qid, keys in keys_by_qid.items():
        for key in keys:
            key_to_qids.setdefault(key, []).append(qid)
    colliding_keys = {key: qids for key, qids in key_to_qids.items() if len(qids) > 1}

    parent: dict[str, str] = {qid: qid for qid in keys_by_qid}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for qids in colliding_keys.values():
        first = qids[0]
        for other in qids[1:]:
            union(first, other)

    members_by_root: dict[str, set[str]] = {}
    for qid in keys_by_qid:
        members_by_root.setdefault(find(qid), set()).add(qid)

    keys_by_root: dict[str, set[str]] = {}
    for key, qids in colliding_keys.items():
        keys_by_root.setdefault(find(qids[0]), set()).add(key)

    clusters = [
        CollisionCluster(qids=tuple(sorted(members)), shared_keys=tuple(sorted(keys_by_root[root])))
        for root, members in members_by_root.items()
        if len(members) > 1
    ]
    clusters.sort(key=lambda c: c.qids)
    return clusters


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
    minted IDs for QIDs it has already admitted in an earlier run. A QID
    present in the crosswalk always reuses its retained ID exactly — it is
    NEVER silently reminted, even if this run newly routes that QID to
    ``REVIEW_REQUIRED`` (the ID is preserved as a reserved historical record
    so a later re-admission after human review still reuses the same stable
    ID; no admission is built for a non-``AUTO_ADMIT`` candidate regardless).
    New QIDs are minted via ``id_factory`` exactly once.

    Same-search-key collisions (the accepted deterministic HullQ search-key
    projection from ``hullq.domain.identity.generate_search_keys``, covering
    the canonical label, case/whitespace normalization, accepted corporate/
    country-suffix stripping, and retained same-entity aliases) within
    *entities* route every colliding QID to ``REVIEW_REQUIRED`` rather than a
    forced merge or an arbitrary pick — see ``compute_collision_clusters``.

    An empty/missing preferred label cannot auto-admit and produces no
    observation, per IDENTITY_MODEL.v0.2 and REQ-ID-012: there is no source
    identity claim to preserve.
    """
    crosswalk = dict(existing_crosswalk or {})
    colliding_qids: set[str] = {
        qid for cluster in compute_collision_clusters(entities) for qid in cluster.qids
    }

    candidates: list[BootstrapCandidate] = []
    for entity in entities:
        qid = entity.qid
        label = entity.label
        retained_id = crosswalk.get(qid)

        if not label:
            candidates.append(
                BootstrapCandidate(
                    qid=qid,
                    retrieved_at=retrieved_at,
                    preferred_label=None,
                    aliases=tuple(entity.aliases),
                    hullq_id=retained_id,
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
                    hullq_id=retained_id,
                    decision=BootstrapDecision.REVIEW_REQUIRED,
                    reason_codes=(BootstrapReasonCode.NAME_COLLISION,),
                    observation_id=observation_id,
                    bundle_id=bundle_id,
                    bundle_version=bundle_version,
                    evidence_link_id=None,
                )
            )
            continue

        hullq_id = retained_id if retained_id is not None else id_factory()
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


def load_crosswalk_from_manifest(manifest: dict[str, Any]) -> dict[str, str]:
    """Extract the retained QID -> HullQ-ID crosswalk from a committed manifest dict.

    Only rows with a non-null ``hullq_id`` contribute. Used to make reruns
    fail-safe: an existing retained mapping is always reused, never silently
    reminted (see ``classify_candidates`` / ``run_live_bootstrap``).

    Fails closed via ``CrosswalkConflictError`` if the manifest itself is
    internally inconsistent in either direction — checked before any row is
    collapsed into the returned dict, so neither conflict form can be masked
    by insertion order:

    - the same QID mapped to two different non-null HullQ IDs;
    - the same HullQ ID addressed by two different QIDs.

    Callers MUST call this (directly or via ``classify_candidates``'s own
    ``validate_crosswalk_consistency`` pass) before any live network request
    on a rerun, so a corrupted retained manifest is never silently trusted.
    """
    qid_to_id: dict[str, str] = {}
    id_to_qid: dict[str, str] = {}
    for row in manifest.get("candidates", []):
        hullq_id = row.get("hullq_id")
        if hullq_id is None:
            continue
        qid = row["qid"]

        prior_id = qid_to_id.get(qid)
        if prior_id is not None and prior_id != hullq_id:
            raise CrosswalkConflictError(
                f"Retained manifest is internally inconsistent: QID {qid!r} maps to "
                f"conflicting HullQ IDs {prior_id!r} and {hullq_id!r}."
            )
        prior_qid = id_to_qid.get(hullq_id)
        if prior_qid is not None and prior_qid != qid:
            raise CrosswalkConflictError(
                f"Retained manifest is internally inconsistent: HullQ ID {hullq_id!r} is "
                f"addressed by conflicting QIDs {prior_qid!r} and {qid!r}."
            )

        qid_to_id[qid] = hullq_id
        id_to_qid[hullq_id] = qid

    return qid_to_id


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
            "id": _stable_alias_id(alias_name),
            "alias_class": "source_spelling",
            "name": alias_name,
        }
        for alias_name in candidate.aliases
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
    collision_clusters: list[CollisionCluster] | None = None,
    acquisition_failure_count: int = 0,
    fetched_entity_count: int | None = None,
    acquired_at: str | None = None,
    classification_recomputed_at: str | None = None,
) -> dict[str, Any]:
    """Build the full versioned, JSON-serializable bootstrap manifest document.

    Validates crosswalk consistency before returning (fails closed on a
    conflicting QID -> HullQ-ID mapping). Retains the exact discovery
    query/version and acquisition path/version in an auditable, non-ambiguous
    form (SLICE-0017 manifest/report audit-completeness requirement).

    ``fetched_entity_count`` is the number of entities actually returned by
    ``fetch_entities_bootstrap`` (distinct from ``candidates_processed``,
    which reflects post-classification candidate count); it defaults to
    ``len(candidates)`` when not supplied, which holds by construction since
    ``classify_candidates`` produces exactly one candidate per acquired
    entity.

    ``generated_at`` is when THIS manifest document was (re)written.
    ``acquired_at`` is the original live Wikidata acquisition timestamp — it
    MUST be preserved verbatim across every later offline reclassification
    and MUST NOT be replaced by a recompute's own timestamp; it defaults to
    ``generated_at`` only for a fresh live run (where they are the same
    instant) or for callers that do not distinguish the two. A non-``None``
    ``classification_recomputed_at`` marks this manifest as the product of an
    offline ``--recompute`` pass rather than (or in addition to) the original
    live run, holding that recompute's own timestamp.
    """
    validate_crosswalk_consistency(candidates)
    counts = _counts(candidates)
    return {
        "manifest_version": BOOTSTRAP_MANIFEST_VERSION,
        "source_id": WIKIDATA_SOURCE_ID,
        "generated_at": generated_at,
        "acquired_at": acquired_at if acquired_at is not None else generated_at,
        "classification_recomputed_at": classification_recomputed_at,
        "requested_limit": requested_limit,
        "safety_ceiling": BOOTSTRAP_SAFETY_CEILING,
        "discovery": {
            "unique_qids_returned": unique_qids_returned,
            "candidates_processed": len(candidates),
            "fetched_entity_count": (
                fetched_entity_count if fetched_entity_count is not None else len(candidates)
            ),
            "target_reached": target_reached,
            "acquisition_failure_count": acquisition_failure_count,
            "sparql_query_version": BOOTSTRAP_SPARQL_QUERY_VERSION,
            "sparql_endpoint": BOOTSTRAP_SPARQL_ENDPOINT,
            "entity_api_endpoint": BOOTSTRAP_ENTITY_API_ENDPOINT,
            "entity_api_version": BOOTSTRAP_ENTITY_API_VERSION,
        },
        "usage_metrics": {
            "retrieval_count": retrieval_count,
            "extracted_record_count": extracted_record_count,
        },
        "candidates": [candidate_to_manifest_dict(c) for c in candidates],
        "collision_clusters": [
            {"qids": list(c.qids), "shared_keys": list(c.shared_keys)}
            for c in (collision_clusters or [])
        ],
        "counts": {
            "candidates_processed": counts.candidates_processed,
            "auto_admit": counts.auto_admit,
            "review_required": counts.review_required,
            "not_admitted": counts.not_admitted,
            "reason_breakdown": counts.reason_breakdown,
            "collision_cluster_count": len(collision_clusters or []),
            "retained_crosswalk_count": sum(1 for c in candidates if c.hullq_id is not None),
            "research_observation_count": sum(
                1 for c in candidates if c.observation_id is not None
            ),
            "canonical_evidence_link_count": sum(
                1 for c in candidates if c.evidence_link_id is not None
            ),
        },
    }
