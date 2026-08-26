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
# storage uses SI, precision-preserving representation) and — per
# FIELD_EVIDENCE_SCHEMA.v0.2 — its accepted value domain is genuinely
# unconstrained: str, int, float, bool, None, dict or list, at any nesting.
# Two concrete needs follow:
#
# 1. Every measurement value hullq.sources.wikidata produces via
#    hullq.domain.measurements.normalize_measurement is a Decimal, which the
#    JSONB/JSON encoder has no native representation for.
# 2. Because the accepted value domain includes arbitrary dicts, ANY marker
#    shape used to tag a Decimal (e.g. a reserved key) can itself collide
#    with a legitimate, unrelated value that happens to already look like
#    that marker — narrowing the accepted domain to rule this out is not
#    permitted (no controlling spec does so), and a partial/heuristic escape
#    scheme only pushes the same collision one level deeper (an escaped
#    value that itself looks like an escape marker).
#
# The only construction that is unambiguous for a genuinely unconstrained
# domain is a TOTAL envelope: every value, without exception, is wrapped in
# a fixed two-key discriminated-union shape before storage/fingerprinting.
# The stored top level is therefore NEVER the naked original value — it is
# always {ENCODED_VALUE_TYPE_KEY: ..., ENCODED_VALUE_PAYLOAD_KEY: ...} — so
# decoding never needs to pattern-match (and risk misreading) a value's own
# internal structure; for the "raw" branch the payload is returned byte-for-
# byte verbatim, completely uninspected. Shared verbatim by
# hullq.persistence.readback (decode) and hullq.persistence.fingerprint
# (encode, for a stable/distinguishing content hash) rather than duplicated,
# so the two sides of the encoding can never drift apart.
ENCODED_VALUE_TYPE_KEY = "$type"
ENCODED_VALUE_PAYLOAD_KEY = "$value"
ENCODED_VALUE_TYPE_DECIMAL = "decimal"
ENCODED_VALUE_TYPE_RAW = "raw"


class EncodedValueError(ValueError):
    """Raised when a value read back from JSONB/JSON storage is not a valid
    ``encode_normalized_value`` envelope.

    Every value ``encode_normalized_value`` ever produces is wrapped, so an
    unwrapped or malformed value here means the data was never round-tripped
    through this encoding (corruption, or a foreign/legacy row) — fails
    closed rather than silently guessing an interpretation.
    """


def encode_normalized_value(value: object) -> dict[str, Any]:
    """Encode *value* for JSON/JSONB storage in a type-preserving envelope.

    See the module-level comment above ``ENCODED_VALUE_TYPE_KEY`` for why
    every value — not only Decimal — is unconditionally wrapped: a genuinely
    unconstrained value domain (FIELD_EVIDENCE_SCHEMA.v0.2) means no
    unwrapped marker shape can ever be proven safe against collision with a
    legitimate value. A Decimal is encoded as its exact decimal text under
    type ``"decimal"``; every other value (str, int, float, bool, None,
    dict, list, at any nesting — including a dict that happens to look like
    an envelope itself) is embedded byte-for-byte unchanged under type
    ``"raw"``.
    """
    if isinstance(value, Decimal):
        return {
            ENCODED_VALUE_TYPE_KEY: ENCODED_VALUE_TYPE_DECIMAL,
            ENCODED_VALUE_PAYLOAD_KEY: str(value),
        }
    return {ENCODED_VALUE_TYPE_KEY: ENCODED_VALUE_TYPE_RAW, ENCODED_VALUE_PAYLOAD_KEY: value}


def decode_normalized_value(encoded: object) -> object:
    """Inverse of ``encode_normalized_value``.

    Fails closed (``EncodedValueError``) unless *encoded* is exactly a
    two-key ``{type, value}`` envelope with a recognized type — the "raw"
    payload is returned completely unexamined (never pattern-matched
    against its own contents), so a legitimate value that happens to look
    like an envelope (or a Decimal marker) is restored exactly as stored,
    never misread as something else.
    """
    if isinstance(encoded, dict) and set(encoded) == {
        ENCODED_VALUE_TYPE_KEY,
        ENCODED_VALUE_PAYLOAD_KEY,
    }:
        type_tag = encoded[ENCODED_VALUE_TYPE_KEY]
        payload = encoded[ENCODED_VALUE_PAYLOAD_KEY]
        if type_tag == ENCODED_VALUE_TYPE_DECIMAL and isinstance(payload, str):
            return Decimal(payload)
        if type_tag == ENCODED_VALUE_TYPE_RAW:
            return payload
    raise EncodedValueError(f"not a valid encode_normalized_value envelope: {encoded!r}")


def normalized_to_jsonb(nc: NormalizedCandidate | None) -> dict[str, Any] | None:
    if nc is None:
        return None
    return {
        "value": encode_normalized_value(nc.value),
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
