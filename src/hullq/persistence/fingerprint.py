"""Deterministic semantic fingerprinting — SLICE-0013.

All fingerprints are SHA-256 hex digests of canonical JSON (sorted keys,
no whitespace). Canonical serialization is deterministic regardless of Python
dict insertion order or JSON key ordering.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from hullq.domain.provenance import (
    FieldEvidenceV3,
    NormalizedCandidate,
    ObservationApplicability,
    ProducerMetadata,
    RawObservation,
    ResearchContext,
    SourceLocator,
)
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import (
    ReferenceCrosscheck,
    ResearchEvidenceBundle,
    ResearchObservation,
    UnresolvedFinding,
)


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fingerprint_dict(obj: Any) -> str:
    """SHA-256 of canonical JSON of any JSON-serializable object."""
    return _sha256(_canonical_json(obj))


# ---------------------------------------------------------------------------
# Object → canonical dict conversions
# ---------------------------------------------------------------------------


def _target_dict(t: ResearchTarget) -> dict[str, Any]:
    return {"manufacturer": t.manufacturer, "model": t.model, "first_built": t.first_built}


def _locator_dict(loc: SourceLocator) -> dict[str, Any]:
    return {
        "anchor": loc.anchor,
        "figure": loc.figure,
        "page": loc.page,
        "record_key": loc.record_key,
        "section": loc.section,
        "table": loc.table,
    }


def _raw_dict(raw: RawObservation) -> dict[str, Any]:
    return {
        "excerpt": raw.excerpt,
        "kind": str(raw.kind),
        "unit": raw.unit,
        "value": raw.value,
    }


def _normalized_dict(nc: NormalizedCandidate | None) -> dict[str, Any] | None:
    if nc is None:
        return None
    return {
        "method_id": nc.method_id,
        "method_version": nc.method_version,
        "unit": nc.unit,
        "value": nc.value,
    }


def _applicability_dict(app: ObservationApplicability) -> dict[str, Any]:
    return {
        "design_option_hints": list(app.design_option_hints)
        if app.design_option_hints is not None
        else None,
        "first_year": app.first_year,
        "hull_number_from": app.hull_number_from,
        "hull_number_to": app.hull_number_to,
        "individual_hull_or_listing_ref": app.individual_hull_or_listing_ref,
        "last_year": app.last_year,
        "market_or_region": app.market_or_region,
        "named_variant_hint": app.named_variant_hint,
        "operating_state_hint": app.operating_state_hint,
        "unknown_or_unbounded": app.unknown_or_unbounded,
    }


def _producer_dict(p: ProducerMetadata) -> dict[str, Any]:
    return {
        "identifier": p.identifier,
        "kind": str(p.kind),
        "model": p.model,
        "prompt_or_rule_version": p.prompt_or_rule_version,
        "version": p.version,
    }


def _context_dict(ctx: ResearchContext) -> dict[str, Any]:
    return {"activity_id": ctx.activity_id, "research_job_id": ctx.research_job_id}


def _finding_dict(f: UnresolvedFinding) -> dict[str, Any]:
    return {
        "description": f.description,
        "finding_id": f.finding_id,
        "related_observation_ids": sorted(f.related_observation_ids),
        "severity": str(f.severity),
        "topic": f.topic,
    }


def _crosscheck_dict(cc: ReferenceCrosscheck) -> dict[str, Any]:
    return {
        "crosscheck_id": cc.crosscheck_id,
        "notes": cc.notes,
        "outcome": str(cc.outcome),
        "reference_source_id": cc.reference_source_id,
        "topic_or_field": cc.topic_or_field,
    }


# ---------------------------------------------------------------------------
# Per-entity fingerprint functions
# ---------------------------------------------------------------------------


def fingerprint_observation(obs: ResearchObservation) -> str:
    """Stable fingerprint covering all semantic fields of a ResearchObservation."""
    d: dict[str, Any] = {
        "applicability": _applicability_dict(obs.applicability),
        "claim_semantics": str(obs.claim_semantics),
        "confidence": str(obs.confidence),
        "evidence_type": str(obs.evidence_type),
        "intended_field_pointer": str(obs.intended_field_pointer)
        if obs.intended_field_pointer is not None
        else None,
        "intended_subject_kind_hint": str(obs.intended_subject_kind_hint)
        if obs.intended_subject_kind_hint is not None
        else None,
        "normalized_candidate": _normalized_dict(obs.normalized_candidate),
        "notes": obs.notes,
        "observation_id": obs.observation_id,
        "observed_at": obs.observed_at,
        "producer": _producer_dict(obs.producer),
        "raw": _raw_dict(obs.raw),
        "research_context": _context_dict(obs.research_context),
        "research_target": _target_dict(obs.research_target),
        "source_id": obs.source_id,
        "source_locator": _locator_dict(obs.source_locator),
        "supersedes_observation_id": obs.supersedes_observation_id,
    }
    return fingerprint_dict(d)


def fingerprint_evidence(ev: FieldEvidenceV3) -> str:
    """Stable fingerprint covering all semantic fields of a FieldEvidenceV3."""
    d: dict[str, Any] = {
        "applicability": _applicability_dict(ev.applicability),
        "claim_semantics": str(ev.claim_semantics),
        "confidence": str(ev.confidence),
        "evidence_id": ev.evidence_id,
        "evidence_type": str(ev.evidence_type),
        "field_pointer": str(ev.field_pointer),
        "normalized_candidate": _normalized_dict(ev.normalized_candidate),
        "notes": ev.notes,
        "observed_at": ev.observed_at,
        "producer": _producer_dict(ev.producer),
        "raw": _raw_dict(ev.raw),
        "research_context": _context_dict(ev.research_context),
        "source_id": ev.source_id,
        "source_locator": _locator_dict(ev.source_locator),
        "subject_id": ev.subject.id,
        "subject_kind": str(ev.subject.kind),
        "supersedes_evidence_id": ev.supersedes_evidence_id,
    }
    return fingerprint_dict(d)


def fingerprint_bundle(bundle: ResearchEvidenceBundle) -> str:
    """Stable fingerprint covering the full semantic content of a ResearchEvidenceBundle.

    Collections are sorted by their per-element fingerprint so that reordering
    semantically identical members does not produce a different bundle hash.
    Persistence membership tables are unordered; the fingerprint must match.
    """
    d: dict[str, Any] = {
        "activity_id": bundle.activity_id,
        "bundle_id": bundle.bundle_id,
        "bundle_version": bundle.bundle_version,
        "observations": sorted(fingerprint_observation(o) for o in bundle.observations),
        "promoted_evidence": sorted(fingerprint_evidence(e) for e in bundle.promoted_evidence),
        "reference_crosschecks": sorted(
            fingerprint_dict(_crosscheck_dict(cc)) for cc in bundle.reference_crosschecks
        ),
        "research_job_id": bundle.research_job_id,
        "research_target": _target_dict(bundle.research_target),
        "unresolved_findings": sorted(
            fingerprint_dict(_finding_dict(f)) for f in bundle.unresolved_findings
        ),
    }
    return fingerprint_dict(d)
