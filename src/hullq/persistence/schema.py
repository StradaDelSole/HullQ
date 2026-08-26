"""Serialization helpers: Python domain objects → dicts for JSONB columns — SLICE-0013.

These helpers are the canonical bridge between the runtime domain objects and
the relational schema. They are pure Python with no database dependencies.
"""

from __future__ import annotations

from decimal import Decimal
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


def target_to_jsonb(t: ResearchTarget) -> dict[str, Any]:
    return {"manufacturer": t.manufacturer, "model": t.model, "first_built": t.first_built}


def locator_to_jsonb(loc: SourceLocator) -> dict[str, Any]:
    return {
        "page": loc.page,
        "section": loc.section,
        "anchor": loc.anchor,
        "table": loc.table,
        "figure": loc.figure,
        "record_key": loc.record_key,
    }


def raw_to_jsonb(raw: RawObservation) -> dict[str, Any]:
    return {
        "kind": str(raw.kind),
        "value": raw.value,
        "unit": raw.unit,
        "excerpt": raw.excerpt,
    }


# NormalizedCandidate.value is declared as `object` (REQ: canonical physical
# storage uses SI, precision-preserving representation) and MAY be a Decimal
# — every measurement value hullq.sources.wikidata produces via
# hullq.domain.measurements.normalize_measurement is a Decimal. The JSONB/
# JSON encoder has no native Decimal support, so a Decimal must be encoded
# for storage; a bare string (``str(value)``) is NOT sufficient, because
# NormalizedCandidate.value could independently, legitimately be a plain
# string (e.g. "12.80") — that string and Decimal("12.80") are distinct
# values and must not collapse to the same wire representation, or become
# indistinguishable in a content fingerprint. A Decimal is therefore wrapped
# in this explicit, structurally distinct marker object; decoding only ever
# restores a Decimal from that exact marker shape — never from numeric-
# looking text — so every other value (str, int, float, bool, None, dict,
# list) round-trips completely unchanged. Shared verbatim by
# hullq.persistence.readback (decode) and hullq.persistence.fingerprint
# (encode, for a stable/distinguishing content hash) rather than duplicated,
# so the two sides of the encoding can never drift apart.
DECIMAL_JSONB_MARKER_KEY = "__decimal__"


def encode_decimal_for_jsonb(value: object) -> object:
    """Encode *value* for JSON/JSONB storage, preserving Decimal identity.

    See ``DECIMAL_JSONB_MARKER_KEY`` for why a bare stringification is not
    used. Every non-Decimal value passes through completely unchanged.
    """
    if isinstance(value, Decimal):
        return {DECIMAL_JSONB_MARKER_KEY: str(value)}
    return value


def decode_decimal_from_jsonb(value: object) -> object:
    """Inverse of ``encode_decimal_for_jsonb``.

    Restores a Decimal ONLY from the exact structural marker object; no
    heuristic (numeric-looking text, unit, method, field pointer) is ever
    applied, so a legitimately string-typed value — including one that looks
    numeric — always round-trips as the same string.
    """
    if isinstance(value, dict) and set(value) == {DECIMAL_JSONB_MARKER_KEY}:
        marker_value = value[DECIMAL_JSONB_MARKER_KEY]
        if isinstance(marker_value, str):
            return Decimal(marker_value)
    return value


def normalized_to_jsonb(nc: NormalizedCandidate | None) -> dict[str, Any] | None:
    if nc is None:
        return None
    return {
        "value": encode_decimal_for_jsonb(nc.value),
        "unit": nc.unit,
        "method_id": nc.method_id,
        "method_version": nc.method_version,
    }


def applicability_to_jsonb(app: ObservationApplicability) -> dict[str, Any]:
    return {
        "first_year": app.first_year,
        "last_year": app.last_year,
        "hull_number_from": app.hull_number_from,
        "hull_number_to": app.hull_number_to,
        "market_or_region": app.market_or_region,
        "named_variant_hint": app.named_variant_hint,
        "design_option_hints": list(app.design_option_hints)
        if app.design_option_hints is not None
        else None,
        "operating_state_hint": app.operating_state_hint,
        "individual_hull_or_listing_ref": app.individual_hull_or_listing_ref,
        "unknown_or_unbounded": app.unknown_or_unbounded,
    }


def producer_to_jsonb(p: ProducerMetadata) -> dict[str, Any]:
    return {
        "kind": str(p.kind),
        "identifier": p.identifier,
        "version": p.version,
        "model": p.model,
        "prompt_or_rule_version": p.prompt_or_rule_version,
    }


def context_to_jsonb(ctx: ResearchContext) -> dict[str, Any]:
    return {"research_job_id": ctx.research_job_id, "activity_id": ctx.activity_id}


def applicability_from_jsonb(d: dict[str, Any]) -> ObservationApplicability:
    """Reconstruct ObservationApplicability from a JSONB dict."""
    raw_hints: list[str] | None = d.get("design_option_hints")
    return ObservationApplicability(
        first_year=d.get("first_year"),
        last_year=d.get("last_year"),
        hull_number_from=d.get("hull_number_from"),
        hull_number_to=d.get("hull_number_to"),
        market_or_region=d.get("market_or_region"),
        named_variant_hint=d.get("named_variant_hint"),
        design_option_hints=tuple(raw_hints) if raw_hints is not None else None,
        operating_state_hint=d.get("operating_state_hint"),
        individual_hull_or_listing_ref=d.get("individual_hull_or_listing_ref"),
        unknown_or_unbounded=bool(d.get("unknown_or_unbounded", False)),
    )


def observation_row_params(
    obs: ResearchObservation,
    content_hash: str,
) -> tuple[Any, ...]:
    """Return the ordered parameter tuple for INSERT into research_observations."""
    return (
        obs.observation_id,
        content_hash,
        target_to_jsonb(obs.research_target),
        obs.source_id,
        locator_to_jsonb(obs.source_locator),
        raw_to_jsonb(obs.raw),
        normalized_to_jsonb(obs.normalized_candidate),
        str(obs.evidence_type),
        str(obs.claim_semantics),
        applicability_to_jsonb(obs.applicability),
        producer_to_jsonb(obs.producer),
        context_to_jsonb(obs.research_context),
        obs.observed_at,
        str(obs.confidence),
        obs.supersedes_observation_id,
        str(obs.intended_subject_kind_hint) if obs.intended_subject_kind_hint is not None else None,
        str(obs.intended_field_pointer) if obs.intended_field_pointer is not None else None,
        obs.notes,
    )


def evidence_row_params(
    ev: FieldEvidenceV3,
    content_hash: str,
) -> tuple[Any, ...]:
    """Return the ordered parameter tuple for INSERT into research_evidence (global table)."""
    return (
        ev.evidence_id,
        content_hash,
        str(ev.subject.kind),
        ev.subject.id,
        str(ev.field_pointer),
        ev.source_id,
        locator_to_jsonb(ev.source_locator),
        raw_to_jsonb(ev.raw),
        normalized_to_jsonb(ev.normalized_candidate),
        str(ev.evidence_type),
        str(ev.claim_semantics),
        applicability_to_jsonb(ev.applicability),
        producer_to_jsonb(ev.producer),
        context_to_jsonb(ev.research_context),
        ev.observed_at,
        str(ev.confidence),
        ev.supersedes_evidence_id,
        ev.notes,
    )


def finding_row_params(
    finding: UnresolvedFinding,
    bundle: ResearchEvidenceBundle,
) -> tuple[Any, ...]:
    """Return the ordered parameter tuple for INSERT into bundle_unresolved_findings."""
    return (
        finding.finding_id,
        bundle.bundle_id,
        bundle.bundle_version,
        finding.topic,
        finding.description,
        str(finding.severity),
        sorted(finding.related_observation_ids),
    )


def crosscheck_row_params(
    cc: ReferenceCrosscheck,
    bundle: ResearchEvidenceBundle,
) -> tuple[Any, ...]:
    """Return the ordered parameter tuple for INSERT into bundle_reference_crosschecks."""
    return (
        cc.crosscheck_id,
        bundle.bundle_id,
        bundle.bundle_version,
        cc.reference_source_id,
        cc.topic_or_field,
        str(cc.outcome),
        cc.notes,
    )
