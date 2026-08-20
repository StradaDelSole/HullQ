"""Minimal round-trip readback for persistence fidelity proofs — SLICE-0013.

Provides the smallest read support needed to verify that persisted data
survives the round trip losslessly. Not a general query/search repository API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
    FieldEvidenceV3,
    JsonPointer,
    NormalizedCandidate,
    ProducerKind,
    ProducerMetadata,
    ProvenanceSubject,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    SourceLocator,
    SubjectKind,
)
from hullq.persistence.schema import applicability_from_jsonb
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import (
    ReferenceCheckOutcome,
    ReferenceCrosscheck,
    ResearchObservation,
    UnresolvedFinding,
    UnresolvedFindingSeverity,
)


@dataclass(frozen=True)
class BundleSnapshot:
    """Minimal read-back snapshot of a persisted bundle for round-trip verification."""

    bundle_id: str
    bundle_version: str
    content_hash: str
    research_target: ResearchTarget
    research_job_id: str | None
    activity_id: str | None
    observation_ids: tuple[str, ...]
    finding_ids: tuple[str, ...]
    crosscheck_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal reconstruction helpers
# ---------------------------------------------------------------------------


def _target_from_jsonb(d: dict[str, Any]) -> ResearchTarget:
    return ResearchTarget(
        manufacturer=d.get("manufacturer"),
        model=str(d["model"]),
        first_built=d.get("first_built"),
    )


def _locator_from_jsonb(d: dict[str, Any]) -> SourceLocator:
    return SourceLocator(
        page=d.get("page"),
        section=d.get("section"),
        anchor=d.get("anchor"),
        table=d.get("table"),
        figure=d.get("figure"),
        record_key=d.get("record_key"),
    )


def _raw_from_jsonb(d: dict[str, Any]) -> RawObservation:
    return RawObservation(
        kind=RawObservationKind(d["kind"]),
        value=d["value"],
        unit=d.get("unit"),
        excerpt=d.get("excerpt"),
    )


def _normalized_from_jsonb(d: dict[str, Any] | None) -> NormalizedCandidate | None:
    if d is None:
        return None
    return NormalizedCandidate(
        value=d["value"],
        unit=d.get("unit"),
        method_id=d.get("method_id"),
        method_version=d.get("method_version"),
    )


def _producer_from_jsonb(d: dict[str, Any]) -> ProducerMetadata:
    return ProducerMetadata(
        kind=ProducerKind(d["kind"]),
        identifier=str(d["identifier"]),
        version=d.get("version"),
        model=d.get("model"),
        prompt_or_rule_version=d.get("prompt_or_rule_version"),
    )


def _context_from_jsonb(d: dict[str, Any]) -> ResearchContext:
    return ResearchContext(
        research_job_id=d.get("research_job_id"),
        activity_id=d.get("activity_id"),
    )


# ---------------------------------------------------------------------------
# Public readback functions
# ---------------------------------------------------------------------------


def fetch_bundle_snapshot(conn: Any, bundle_id: str, bundle_version: str) -> BundleSnapshot | None:
    """Return a minimal BundleSnapshot for the given (bundle_id, bundle_version), or None."""
    from psycopg.rows import dict_row

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT bundle_id, bundle_version, content_hash, research_target, "
            "research_job_id, activity_id "
            "FROM research_bundles WHERE bundle_id = %s AND bundle_version = %s",
            [bundle_id, bundle_version],
        )
        row = cur.fetchone()
    if row is None:
        return None

    target = _target_from_jsonb(row["research_target"])

    with conn.cursor() as cur:
        cur.execute(
            "SELECT observation_id FROM bundle_observation_members "
            "WHERE bundle_id = %s AND bundle_version = %s ORDER BY observation_id",
            [bundle_id, bundle_version],
        )
        obs_ids = tuple(r[0] for r in cur.fetchall())

    with conn.cursor() as cur:
        cur.execute(
            "SELECT finding_id FROM bundle_unresolved_findings "
            "WHERE bundle_id = %s AND bundle_version = %s ORDER BY finding_id",
            [bundle_id, bundle_version],
        )
        finding_ids = tuple(r[0] for r in cur.fetchall())

    with conn.cursor() as cur:
        cur.execute(
            "SELECT crosscheck_id FROM bundle_reference_crosschecks "
            "WHERE bundle_id = %s AND bundle_version = %s ORDER BY crosscheck_id",
            [bundle_id, bundle_version],
        )
        crosscheck_ids = tuple(r[0] for r in cur.fetchall())

    with conn.cursor() as cur:
        cur.execute(
            "SELECT evidence_id FROM bundle_evidence_members "
            "WHERE bundle_id = %s AND bundle_version = %s ORDER BY evidence_id",
            [bundle_id, bundle_version],
        )
        evidence_ids = tuple(r[0] for r in cur.fetchall())

    return BundleSnapshot(
        bundle_id=row["bundle_id"],
        bundle_version=row["bundle_version"],
        content_hash=row["content_hash"],
        research_target=target,
        research_job_id=row["research_job_id"],
        activity_id=row["activity_id"],
        observation_ids=obs_ids,
        finding_ids=finding_ids,
        crosscheck_ids=crosscheck_ids,
        evidence_ids=evidence_ids,
    )


def fetch_observation(conn: Any, observation_id: str) -> ResearchObservation | None:
    """Reconstruct a ResearchObservation from the database, or None if not found."""
    from psycopg.rows import dict_row

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM research_observations WHERE observation_id = %s",
            [observation_id],
        )
        row = cur.fetchone()
    if row is None:
        return None

    from hullq.domain.provenance import JsonPointer as JP

    hint_raw: str | None = row["intended_subject_kind_hint"]
    fp_raw: str | None = row["intended_field_pointer"]

    return ResearchObservation(
        observation_id=row["observation_id"],
        research_target=_target_from_jsonb(row["research_target"]),
        source_id=row["source_id"],
        source_locator=_locator_from_jsonb(row["source_locator"]),
        raw=_raw_from_jsonb(row["raw_observation"]),
        normalized_candidate=_normalized_from_jsonb(row["normalized_candidate"]),
        evidence_type=EvidenceType(row["evidence_type"]),
        claim_semantics=ClaimSemantics(row["claim_semantics"]),
        applicability=applicability_from_jsonb(row["applicability"]),
        producer=_producer_from_jsonb(row["producer"]),
        research_context=_context_from_jsonb(row["research_context"]),
        observed_at=row["observed_at"],
        confidence=ConfidenceLevel(row["confidence"]),
        supersedes_observation_id=row["supersedes_observation_id"],
        intended_subject_kind_hint=SubjectKind(hint_raw) if hint_raw is not None else None,
        intended_field_pointer=JP(fp_raw) if fp_raw is not None else None,
        notes=row["notes"],
    )


def fetch_finding(
    conn: Any, finding_id: str, bundle_id: str, bundle_version: str
) -> UnresolvedFinding | None:
    """Reconstruct an UnresolvedFinding from the database."""
    from psycopg.rows import dict_row

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM bundle_unresolved_findings "
            "WHERE finding_id = %s AND bundle_id = %s AND bundle_version = %s",
            [finding_id, bundle_id, bundle_version],
        )
        row = cur.fetchone()
    if row is None:
        return None

    return UnresolvedFinding(
        finding_id=row["finding_id"],
        topic=row["topic"],
        description=row["description"],
        related_observation_ids=frozenset(row["related_observation_ids"]),
        severity=UnresolvedFindingSeverity(row["severity"]),
    )


def fetch_crosscheck(
    conn: Any, crosscheck_id: str, bundle_id: str, bundle_version: str
) -> ReferenceCrosscheck | None:
    """Reconstruct a ReferenceCrosscheck from the database."""
    from psycopg.rows import dict_row

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM bundle_reference_crosschecks "
            "WHERE crosscheck_id = %s AND bundle_id = %s AND bundle_version = %s",
            [crosscheck_id, bundle_id, bundle_version],
        )
        row = cur.fetchone()
    if row is None:
        return None

    return ReferenceCrosscheck(
        crosscheck_id=row["crosscheck_id"],
        reference_source_id=row["reference_source_id"],
        topic_or_field=row["topic_or_field"],
        outcome=ReferenceCheckOutcome(row["outcome"]),
        notes=row["notes"],
    )


def fetch_evidence(conn: Any, evidence_id: str) -> FieldEvidenceV3 | None:
    """Reconstruct a FieldEvidenceV3 from the global research_evidence table, or None."""
    from psycopg.rows import dict_row

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM research_evidence WHERE evidence_id = %s",
            [evidence_id],
        )
        row = cur.fetchone()
    if row is None:
        return None

    return FieldEvidenceV3(
        evidence_id=row["evidence_id"],
        subject=ProvenanceSubject(
            kind=SubjectKind(row["subject_kind"]),
            id=row["subject_id"],
        ),
        field_pointer=JsonPointer(row["field_pointer"]),
        source_id=row["source_id"],
        source_locator=_locator_from_jsonb(row["source_locator"]),
        raw=_raw_from_jsonb(row["raw_observation"]),
        normalized_candidate=_normalized_from_jsonb(row["normalized_candidate"]),
        evidence_type=EvidenceType(row["evidence_type"]),
        producer=_producer_from_jsonb(row["producer"]),
        research_context=_context_from_jsonb(row["research_context"]),
        observed_at=row["observed_at"],
        confidence=ConfidenceLevel(row["confidence"]),
        supersedes_evidence_id=row["supersedes_evidence_id"],
        notes=row["notes"],
        claim_semantics=ClaimSemantics(row["claim_semantics"]),
        applicability=applicability_from_jsonb(row["applicability"]),
    )
