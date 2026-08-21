"""Canonical semantic comparator for SLICE-0014 benchmark round-trip verification.

Single implementation used by both runner.py and tests/persistence/
test_benchmark_persistence.py. Comparing ResearchObservation, UnresolvedFinding
and ReferenceCrosscheck field by field to verify that DB persistence is lossless.
"""

from __future__ import annotations

from typing import Any


def compare_observation_semantics(
    case_id: str,
    original: Any,
    fetched: Any,
) -> list[str]:
    """Return a list of mismatch descriptions (empty = semantically identical).

    Compares ALL persisted ResearchObservation fields:
      research_target (manufacturer, model, first_built)
      source_id
      complete SourceLocator (page, section, anchor, table, figure, record_key)
      RawObservation (kind, value, unit, excerpt)
      normalized_candidate
      EvidenceType
      ClaimSemantics
      all 10 ObservationApplicability fields
      complete ProducerMetadata (kind, identifier, version, model,
                                  prompt_or_rule_version)
      complete ResearchContext (research_job_id, activity_id)
      observed_at
      confidence
      supersedes_observation_id
      intended_subject_kind_hint
      intended_field_pointer
      notes
    """
    mismatches: list[str] = []
    oid = original.observation_id
    prefix = f"{case_id}/{oid}"

    def chk(label: str, got: Any, exp: Any) -> None:
        if got != exp:
            mismatches.append(f"{prefix}: {label}: got={got!r} expected={exp!r}")

    # research_target
    ft, ot = fetched.research_target, original.research_target
    chk("research_target.manufacturer", ft.manufacturer, ot.manufacturer)
    chk("research_target.model", ft.model, ot.model)
    chk("research_target.first_built", ft.first_built, ot.first_built)

    # source identity
    chk("source_id", fetched.source_id, original.source_id)

    # source_locator — all 6 fields
    fl, ol = fetched.source_locator, original.source_locator
    if fl is None and ol is not None:
        mismatches.append(f"{prefix}: source_locator: got=None expected={ol!r}")
    elif fl is not None and ol is None:
        mismatches.append(f"{prefix}: source_locator: got={fl!r} expected=None")
    else:
        if fl is not None and ol is not None:
            chk("source_locator.page", fl.page, ol.page)
            chk("source_locator.section", fl.section, ol.section)
            chk("source_locator.anchor", fl.anchor, ol.anchor)
            chk("source_locator.table", fl.table, ol.table)
            chk("source_locator.figure", fl.figure, ol.figure)
            chk("source_locator.record_key", fl.record_key, ol.record_key)

    # raw observation — all 4 fields
    chk("raw.kind", fetched.raw.kind, original.raw.kind)
    chk("raw.value", fetched.raw.value, original.raw.value)
    chk("raw.unit", fetched.raw.unit, original.raw.unit)
    chk("raw.excerpt", fetched.raw.excerpt, original.raw.excerpt)

    # normalized_candidate
    chk("normalized_candidate", fetched.normalized_candidate, original.normalized_candidate)

    # semantics
    chk("evidence_type", fetched.evidence_type, original.evidence_type)
    chk("claim_semantics", fetched.claim_semantics, original.claim_semantics)

    # applicability — all 10 fields
    fa, oa = fetched.applicability, original.applicability
    for attr in (
        "first_year",
        "last_year",
        "hull_number_from",
        "hull_number_to",
        "market_or_region",
        "named_variant_hint",
        "design_option_hints",
        "operating_state_hint",
        "individual_hull_or_listing_ref",
        "unknown_or_unbounded",
    ):
        chk(f"applicability.{attr}", getattr(fa, attr), getattr(oa, attr))

    # producer — all 5 fields
    fp, op = fetched.producer, original.producer
    chk("producer.kind", fp.kind, op.kind)
    chk("producer.identifier", fp.identifier, op.identifier)
    chk("producer.version", fp.version, op.version)
    chk("producer.model", fp.model, op.model)
    chk("producer.prompt_or_rule_version", fp.prompt_or_rule_version, op.prompt_or_rule_version)

    # research_context — both fields, correct None handling
    fc, oc = fetched.research_context, original.research_context
    if fc is None and oc is not None:
        mismatches.append(f"{prefix}: research_context: got=None expected={oc!r}")
    elif fc is not None and oc is None:
        mismatches.append(f"{prefix}: research_context: got={fc!r} expected=None")
    elif fc is not None and oc is not None:
        chk("research_context.research_job_id", fc.research_job_id, oc.research_job_id)
        chk("research_context.activity_id", fc.activity_id, oc.activity_id)

    # scalar fields
    chk("observed_at", fetched.observed_at, original.observed_at)
    chk("confidence", fetched.confidence, original.confidence)
    chk(
        "supersedes_observation_id",
        fetched.supersedes_observation_id,
        original.supersedes_observation_id,
    )
    chk(
        "intended_subject_kind_hint",
        fetched.intended_subject_kind_hint,
        original.intended_subject_kind_hint,
    )
    chk("intended_field_pointer", fetched.intended_field_pointer, original.intended_field_pointer)
    chk("notes", fetched.notes, original.notes)

    return mismatches


def compare_finding_semantics(
    case_id: str,
    original: Any,
    fetched: Any,
) -> list[str]:
    """Return mismatch descriptions for an UnresolvedFinding pair."""
    mismatches: list[str] = []
    fid = original.finding_id
    prefix = f"{case_id}/{fid}"

    def chk(label: str, got: Any, exp: Any) -> None:
        if got != exp:
            mismatches.append(f"{prefix}: {label}: got={got!r} expected={exp!r}")

    chk("finding_id", fetched.finding_id, original.finding_id)
    chk("topic", fetched.topic, original.topic)
    chk("description", fetched.description, original.description)
    chk(
        "related_observation_ids", fetched.related_observation_ids, original.related_observation_ids
    )
    chk("severity", fetched.severity, original.severity)

    return mismatches


def compare_crosscheck_semantics(
    case_id: str,
    original: Any,
    fetched: Any,
) -> list[str]:
    """Return mismatch descriptions for a ReferenceCrosscheck pair."""
    mismatches: list[str] = []
    ccid = original.crosscheck_id
    prefix = f"{case_id}/{ccid}"

    def chk(label: str, got: Any, exp: Any) -> None:
        if got != exp:
            mismatches.append(f"{prefix}: {label}: got={got!r} expected={exp!r}")

    chk("crosscheck_id", fetched.crosscheck_id, original.crosscheck_id)
    chk("reference_source_id", fetched.reference_source_id, original.reference_source_id)
    chk("topic_or_field", fetched.topic_or_field, original.topic_or_field)
    chk("outcome", fetched.outcome, original.outcome)
    chk("notes", fetched.notes, original.notes)

    return mismatches
