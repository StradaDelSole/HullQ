"""Shared FieldResolution/evidence test helpers — SLICE-0051 amendment.

Not a test module itself (no `test_` prefix, not collected by pytest).
Shared by every SLICE-0051 persistence test that needs to durably admit a
qualified `FieldResolution` for a BoatDesign/NamedVariant `draft_max_m`
field through the real accepted write path
(`hullq.persistence.field_resolution.write_field_resolution`), rather than
each duplicating the same `FieldEvidenceV3`/`ResearchEvidenceBundle`
construction boilerplate.
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
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
    ResolutionMethod,
    ResolutionState,
    ResolverKind,
    ResolverMetadata,
    SourceLocator,
    SubjectKind,
)
from hullq.domain.provenance import FieldResolution as _FieldResolution
from hullq.persistence.field_resolution import (
    FieldResolutionWriteStatus,
    encode_canonical_decimal_snapshot,
    write_field_resolution,
)
from hullq.persistence.importer import import_research_evidence_bundle
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import ResearchEvidenceBundle

_REPO_ROOT = Path(__file__).resolve().parents[2]
WIKIDATA_SOURCE: dict[str, Any] = json.loads(
    (_REPO_ROOT / "fixtures" / "sources" / "wikidata_source.json").read_text(encoding="utf-8")
)
WIKIDATA_SOURCE_ID: str = WIKIDATA_SOURCE["source_id"]


def make_evidence(
    evidence_id: str,
    *,
    subject_kind: SubjectKind,
    subject_id: str,
    field_pointer: str,
    value: str,
    source_id: str = WIKIDATA_SOURCE_ID,
) -> FieldEvidenceV3:
    return FieldEvidenceV3(
        evidence_id=evidence_id,
        subject=ProvenanceSubject(kind=subject_kind, id=subject_id),
        field_pointer=JsonPointer(field_pointer),
        source_id=source_id,
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(
            kind=RawObservationKind.STRUCTURED_RECORD, value=value, unit="m", excerpt=None
        ),
        normalized_candidate=NormalizedCandidate(
            value=value, unit="m", method_id="test-normalize", method_version="1"
        ),
        evidence_type=EvidenceType.STRUCTURED_DATASET,
        producer=ProducerMetadata(
            kind=ProducerKind.DETERMINISTIC_TOOL,
            identifier="test-harness",
            version="1",
            model=None,
            prompt_or_rule_version=None,
        ),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-09-12T00:00:00+00:00",
        confidence=ConfidenceLevel.HIGH,
        supersedes_evidence_id=None,
        notes=None,
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
            unknown_or_unbounded=True,
        ),
    )


def import_evidence(conn: Any, *evidence: FieldEvidenceV3) -> None:
    bundle = ResearchEvidenceBundle(
        bundle_id=f"BUNDLE-{uuid.uuid4().hex[:8]}",
        bundle_version="1",
        research_target=ResearchTarget(manufacturer=None, model="test", first_built=None),
        research_job_id=None,
        activity_id=None,
        observations=(),
        unresolved_findings=(),
        promoted_evidence=tuple(evidence),
        reference_crosschecks=(),
    )
    result = import_research_evidence_bundle(conn, bundle)
    assert result.status.value in ("imported", "already_imported"), result
    conn.commit()


def admit_resolved_draft_max(
    conn: Any,
    *,
    subject_kind: SubjectKind,
    subject_id: str,
    field_pointer: str,
    value: Decimal,
    resolution_id: str,
    evidence_id: str | None = None,
) -> None:
    """Durably admit one `resolved` `draft_max_m` FieldResolution end to end:
    import one supporting FieldEvidenceV3 (Wikidata source, already-accepted
    `production_value: allowed` clearance) then write the resolution through
    the real accepted `write_field_resolution` path. Asserts success --
    intended for test/proof setup, not for exercising failure paths."""
    evidence_id = evidence_id or f"EV-{resolution_id}"
    evidence = make_evidence(
        evidence_id,
        subject_kind=subject_kind,
        subject_id=subject_id,
        field_pointer=field_pointer,
        value=str(value),
    )
    import_evidence(conn, evidence)

    resolution = _FieldResolution(
        resolution_id=resolution_id,
        subject=ProvenanceSubject(kind=subject_kind, id=subject_id),
        field_pointer=JsonPointer(field_pointer),
        state=ResolutionState.RESOLVED,
        canonical_value_snapshot=encode_canonical_decimal_snapshot(value),
        supporting_evidence_ids=frozenset({evidence_id}),
        contradicting_evidence_ids=frozenset(),
        considered_evidence_ids=frozenset({evidence_id}),
        resolution_method=ResolutionMethod.UNANIMOUS_EVIDENCE,
        policy_version="test-policy-1",
        resolver=ResolverMetadata(
            kind=ResolverKind.DETERMINISTIC_TOOL, identifier="test", version="1"
        ),
        resolved_at="2026-09-12T00:00:00+00:00",
        supersedes_resolution_id=None,
        notes=None,
    )
    result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={WIKIDATA_SOURCE_ID: WIKIDATA_SOURCE},
    )
    assert result.status is FieldResolutionWriteStatus.CREATED, result
    conn.commit()
