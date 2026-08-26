"""Full-boundary Wikidata Tier-1 evidence rollout — SLICE-0028.

Implements the pure, deterministic logic described in
``docs/slices/SLICE-0028-full-boundary-wikidata-tier1-evidence-rollout.md``.

Scales the accepted SLICE-0026/0027 Wikidata Tier-1 evidence path from the
corrected 100-BoatModel pilot to the **entire accepted SLICE-0017+0018
canonical identity boundary** (1,770 canonical BoatModels / 1,772 historical
QID -> HullQ-ID mappings), using only already-accepted historical QID ->
HullQ-ID mappings and the accepted SLICE-0027 qualifier-carrier semantics.

This module performs no network acquisition (that remains in
``hullq.sources.wikidata`` and is invoked by the SLICE-0028 runner script) and
no database access (that remains in ``hullq.persistence``). Given only the
already-accepted SLICE-0017/0018 identity manifests, plus already-acquired
``WikidataEntityData``/``FieldEvidence`` produced by the existing adapter, it:

- reproduces the accepted 1,770/1,772 identity boundary and fails closed on
  any drift (reusing, never reimplementing,
  ``hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot.load_reproduced_identity_boundary``);
- builds a full-boundary QID -> canonical-BoatModel linkage that is
  structurally multi-QID-safe (a BoatModel with more than one accepted QID
  would retain every one of them, never silently collapsed to one) even
  though the accepted SLICE-0017+0018 AUTO_ADMIT crosswalk is, by its own
  enforced bijection invariant, exactly one QID per canonical BoatModel today;
- derives the exact distinct full-boundary request-QID set from that linkage
  only — no discovery, no new identity decision;
- reuses the existing adapter's per-(QID, field) coverage classification
  (``hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot.classify_entity_field_coverage``
  / ``summarize_field_coverage``) for source-QID-level coverage, then
  aggregates to canonical-BoatModel level using strongest-available-evidence
  precedence over every QID mapped to that BoatModel — a coverage
  classification only, never a canonical value choice;
- retains candidate-multiplicity / value-disagreement diagnostics without any
  canonical adjudication;
- computes the explicitly non-canonical ``basic_searchable_evidence_precursor``
  diagnostic count;
- assembles one QID-keyed ``ResearchEvidenceBundle`` per requested QID (never
  per BoatModel — the canonical BoatModel<->QID link is retained separately in
  the linkage document, exactly as SLICE-0026/0027 do) for persistence via the
  existing SLICE-0013 importer;
- assembles the retained linkage/evidence-manifest/coverage/disagreement/
  precursor documents and their offline self-consistency verification.

Explicitly does NOT:
- perform any network acquisition or SPARQL/discovery query;
- infer, mint or persist a canonical BoatDesign generation;
- create or mutate a canonical BoatModel/crosswalk row;
- create a FieldResolution or choose a canonical technical value;
- reimplement Wikidata qualifier/unit extraction or per-(QID, field) coverage
  classification (both reused unchanged from
  ``hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hullq.bootstrap import wikidata_sl0026_tier1_enrichment_pilot as sl0026
from hullq.domain.provenance import FieldEvidence, JsonPointer
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import ResearchEvidenceBundle, migrate_evidence_v02_to_v03
from hullq.sources.wikidata import WIKIDATA_SOURCE_ID, WikidataEntityData, WikidataQualityReport

__all__ = [
    "ALLOWED_FIELD_POINTERS",
    "ARTIFACT_DIGESTS_FILENAME",
    "ARTIFACT_DIGESTS_SCHEMA_VERSION",
    "BASIC_SEARCHABLE_PRECURSOR_SCHEMA_VERSION",
    "COVERAGE_SCHEMA_VERSION",
    "DISAGREEMENT_SCHEMA_VERSION",
    "EVIDENCE_MANIFEST_SCHEMA_VERSION",
    "FIELD_LABEL_BY_POINTER",
    "LINKAGE_SCHEMA_VERSION",
    "SL0028_ACTIVITY_ID",
    "BoatModelFieldCoverage",
    "BoatModelFieldDisagreement",
    "BoatModelLinkage",
    "FieldCoverageBucket",
    "LinkageIntegrityError",
    "build_artifact_digests",
    "build_basic_searchable_precursor_document",
    "build_coverage_document",
    "build_disagreement_document",
    "build_evidence_manifest_document",
    "build_full_boundary_linkage",
    "build_linkage_document",
    "build_sl0028_bundle",
    "classify_boat_model_field_coverage",
    "compute_basic_searchable_evidence_precursor",
    "compute_boat_model_field_disagreements",
    "distinct_request_qids",
    "rebuild_entities_from_manifest",
    "retained_package_filenames",
    "summarize_boat_model_field_coverage",
    "verify_artifact_digests_self_consistency",
    "verify_basic_searchable_precursor_self_consistency",
    "verify_coverage_self_consistency",
    "verify_disagreement_self_consistency",
    "verify_evidence_manifest_self_consistency",
    "verify_full_boundary_linkage",
    "verify_linkage_document_self_consistency",
]

SL0028_ACTIVITY_ID = "SLICE-0028-FULL-BOUNDARY-EVIDENCE"

# Reused directly (not redefined) from the accepted SLICE-0026 pilot module —
# the five allowed field pointers, their labels, and the four mutually
# exclusive per-(QID, field) coverage states are already the single accepted
# source of truth.
ALLOWED_FIELD_POINTERS = sl0026.ALLOWED_FIELD_POINTERS
FIELD_LABEL_BY_POINTER = sl0026.FIELD_LABEL_BY_POINTER
FieldCoverageBucket = sl0026.FieldCoverageBucket

# Strongest-available-evidence precedence for BoatModel-level aggregation
# across every QID mapped to one canonical BoatModel (controlling slice
# "Full-boundary coverage measurement"). A coverage classification only —
# never a canonical technical-value choice.
_BUCKET_PRECEDENCE: tuple[Any, ...] = (
    FieldCoverageBucket.NORMALIZED_CANDIDATE_PRESENT,
    FieldCoverageBucket.SOURCE_STATEMENT_PRESENT,
    FieldCoverageBucket.UNSUPPORTED_OR_MALFORMED,
    FieldCoverageBucket.NO_USABLE_VALUE,
)


# ---------------------------------------------------------------------------
# 1. Full-boundary QID -> canonical-BoatModel linkage (multi-QID-safe)
# ---------------------------------------------------------------------------


class LinkageIntegrityError(RuntimeError):
    """Raised when the full-boundary QID -> BoatModel linkage does not
    exactly reproduce the accepted identity boundary it was derived from.

    SLICE-0028 MUST fail closed (BLOCKED) rather than acquire against a
    linkage that has lost, duplicated, or misattributed a QID or BoatModel.
    """


@dataclass(frozen=True)
class BoatModelLinkage:
    """One canonical BoatModel and every accepted QID mapped to it.

    ``qids`` is a sorted, deduplicated tuple of length >= 1. Deliberately
    generic over cardinality: nothing in this dataclass or in
    ``build_full_boundary_linkage`` assumes exactly one QID per BoatModel, so
    a BoatModel with more than one accepted historical QID would have every
    one of them retained here — never silently collapsed to a single QID —
    even though the accepted SLICE-0017+0018 AUTO_ADMIT crosswalk is, by its
    own enforced bijection invariant
    (``hullq.bootstrap.wikidata_tier0._collapse_qid_id_pairs_fail_closed``),
    exactly one QID per canonical BoatModel in the real accepted boundary
    today.
    """

    hullq_id: str
    qids: tuple[str, ...]
    preferred_label_by_qid: Mapping[str, str | None]

    def __post_init__(self) -> None:
        if not self.hullq_id:
            raise ValueError("BoatModelLinkage.hullq_id must be non-empty")
        deduped = tuple(sorted(dict.fromkeys(self.qids)))
        if not deduped:
            raise ValueError("BoatModelLinkage.qids must contain at least one QID")
        object.__setattr__(self, "qids", deduped)
        object.__setattr__(self, "preferred_label_by_qid", dict(self.preferred_label_by_qid))


def build_full_boundary_linkage(boundary: sl0026.IdentityBoundary) -> tuple[BoatModelLinkage, ...]:
    """Group the reproduced identity boundary's accepted AUTO_ADMIT QID ->
    HullQ-ID pairs by HullQ-ID.

    A plain groupby over already-validated pairs — never a new identity
    decision, never a discovery/fuzzy-match step. Ordered ascending by
    canonical HullQ BoatModel ID (each BoatModel's own QIDs ascending) for
    deterministic, reproducible output independent of the tuple order
    ``IdentityBoundary.auto_admit_qid_to_hullq_id`` happens to carry.
    """
    groups: dict[str, list[str]] = {}
    for qid, hullq_id in boundary.auto_admit_qid_to_hullq_id:
        groups.setdefault(hullq_id, []).append(qid)
    return tuple(
        BoatModelLinkage(
            hullq_id=hullq_id,
            qids=tuple(sorted(qids)),
            preferred_label_by_qid={q: boundary.preferred_label_by_qid.get(q) for q in qids},
        )
        for hullq_id, qids in sorted(groups.items())
    )


def distinct_request_qids(linkage: Sequence[BoatModelLinkage]) -> tuple[str, ...]:
    """The exact, sorted, deduplicated set of QIDs to request — derived only
    from *linkage*, never assumed to equal any hardcoded count."""
    seen: set[str] = set()
    for entry in linkage:
        seen.update(entry.qids)
    return tuple(sorted(seen))


def verify_full_boundary_linkage(
    *, boundary: sl0026.IdentityBoundary, linkage: Sequence[BoatModelLinkage]
) -> list[str]:
    """Independently verify that *linkage* exactly reproduces the accepted
    identity boundary it claims to be derived from.

    Checks (controlling slice "Fixed identity boundary" requirements):
    - the linkage has exactly ``boundary.canonical_boat_model_count`` entries,
      one per distinct HullQ ID (no duplicate BoatModel row);
    - the linkage's HullQ-ID value set is exactly the accepted canonical
      BoatModel ID set (neither more nor fewer);
    - the linkage's QID set is exactly the accepted AUTO_ADMIT QID set (every
      accepted QID -> BoatModel link is preserved, none added by discovery).
    """
    problems: list[str] = []
    if len(linkage) != boundary.canonical_boat_model_count:
        problems.append(
            f"linkage has {len(linkage)} BoatModel entries; expected exactly "
            f"{boundary.canonical_boat_model_count}"
        )
    hullq_ids = [e.hullq_id for e in linkage]
    if len(set(hullq_ids)) != len(hullq_ids):
        problems.append("linkage contains a duplicate BoatModel hullq_id")

    expected_ids = {hullq_id for _qid, hullq_id in boundary.auto_admit_qid_to_hullq_id}
    if set(hullq_ids) != expected_ids:
        problems.append(
            "linkage BoatModel ID value set != accepted canonical BoatModel ID set "
            f"(missing={sorted(expected_ids - set(hullq_ids))!r}, "
            f"unexpected={sorted(set(hullq_ids) - expected_ids)!r})"
        )

    expected_qids = {qid for qid, _hullq_id in boundary.auto_admit_qid_to_hullq_id}
    actual_qids = set(distinct_request_qids(linkage))
    if actual_qids != expected_qids:
        problems.append(
            "linkage QID set != accepted historical AUTO_ADMIT QID set "
            f"(missing={sorted(expected_qids - actual_qids)!r}, "
            f"unexpected={sorted(actual_qids - expected_qids)!r})"
        )
    return problems


LINKAGE_SCHEMA_VERSION = "sl0028-linkage-v1"


def build_linkage_document(
    *, generated_at: str, boundary: sl0026.IdentityBoundary, linkage: Sequence[BoatModelLinkage]
) -> dict[str, Any]:
    """Assemble the retained ``linkage.json`` document: the reproduced
    identity boundary plus the full-boundary QID<->BoatModel linkage derived
    from it, and the exact distinct request-QID count."""
    return {
        "schema_version": LINKAGE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "identity_boundary": {
            "baseline_manifest_path": "research/bootstrap/wikidata/manifest.json",
            "baseline_manifest_sha256": boundary.baseline_manifest_sha256,
            "delta_manifest_path": "research/bootstrap/wikidata/sl0018-2500/manifest.json",
            "delta_manifest_sha256": boundary.delta_manifest_sha256,
            "canonical_boat_model_count": boundary.canonical_boat_model_count,
            "historical_crosswalk_count": boundary.historical_crosswalk_count,
        },
        "linkage_ordering": (
            "ascending canonical HullQ BoatModel ID over the combined SLICE-0017+0018 "
            "AUTO_ADMIT QID->HullQ-ID universe; each BoatModel's own accepted QIDs ascending"
        ),
        "boat_model_count": len(linkage),
        "distinct_request_qid_count": len(distinct_request_qids(linkage)),
        "boat_models": [
            {
                "hullq_id": entry.hullq_id,
                "qids": list(entry.qids),
                "preferred_label_by_qid": dict(entry.preferred_label_by_qid),
            }
            for entry in linkage
        ],
    }


def verify_linkage_document_self_consistency(
    *, boundary: sl0026.IdentityBoundary, document: Mapping[str, Any]
) -> list[str]:
    """Independently rebuild the expected linkage from a freshly reproduced
    identity boundary and compare against a retained ``linkage.json``
    document. Never trusts the retained document's own boundary/linkage
    fields as verification input."""
    linkage = build_full_boundary_linkage(boundary)
    problems = list(verify_full_boundary_linkage(boundary=boundary, linkage=linkage))
    expected = build_linkage_document(
        generated_at=str(document.get("generated_at", "")), boundary=boundary, linkage=linkage
    )
    if dict(document) != expected:
        problems.append(
            "retained linkage.json != independently rebuilt linkage from the live reproduced "
            "identity boundary"
        )
    return problems


# ---------------------------------------------------------------------------
# 2. BoatModel-level coverage aggregation (strongest-evidence precedence)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoatModelFieldCoverage:
    """One canonical BoatModel's aggregated coverage bucket for one allowed
    field, aggregated over every accepted QID mapped to it."""

    hullq_id: str
    field_pointer: JsonPointer
    bucket: Any
    contributing_qids: tuple[str, ...]


def classify_boat_model_field_coverage(
    buckets_by_qid: Mapping[str, Any],
) -> Any:
    """Aggregate one BoatModel's per-QID coverage buckets for one field into
    a single bucket via strongest-available-evidence precedence
    (normalized_candidate_present > source_statement_present >
    unsupported_or_malformed > no_usable_value).

    A coverage classification only — never a canonical value choice; does not
    say which QID's candidate is correct when more than one contributes a
    normalized candidate (see ``compute_boat_model_field_disagreements``).
    """
    present = set(buckets_by_qid.values())
    for bucket in _BUCKET_PRECEDENCE:
        if bucket in present:
            return bucket
    return FieldCoverageBucket.NO_USABLE_VALUE


def summarize_boat_model_field_coverage(
    linkage: Sequence[BoatModelLinkage],
    source_qid_details: Sequence[sl0026.EntityFieldCoverage],
) -> tuple[dict[str, dict[str, int]], tuple[BoatModelFieldCoverage, ...]]:
    """Aggregate already-computed source-QID-level coverage
    (``sl0026.summarize_field_coverage``'s own per-(QID, field) details) up to
    canonical-BoatModel level for every linked BoatModel, using strongest-
    available-evidence precedence over all of that BoatModel's mapped QIDs.

    Never reclassifies or recomputes per-QID coverage itself — only
    aggregates the existing per-QID classification.
    """
    index: dict[tuple[str, JsonPointer], Any] = {
        (d.qid, d.field_pointer): d.bucket for d in source_qid_details
    }
    counts: dict[str, dict[str, int]] = {
        label: {bucket.value: 0 for bucket in FieldCoverageBucket}
        for label in FIELD_LABEL_BY_POINTER.values()
    }
    results: list[BoatModelFieldCoverage] = []
    for entry in linkage:
        for ptr in ALLOWED_FIELD_POINTERS:
            buckets_by_qid = {qid: index[(qid, ptr)] for qid in entry.qids if (qid, ptr) in index}
            bucket = classify_boat_model_field_coverage(buckets_by_qid)
            contributing = tuple(sorted(q for q, b in buckets_by_qid.items() if b == bucket))
            counts[FIELD_LABEL_BY_POINTER[ptr]][bucket.value] += 1
            results.append(
                BoatModelFieldCoverage(
                    hullq_id=entry.hullq_id,
                    field_pointer=ptr,
                    bucket=bucket,
                    contributing_qids=contributing,
                )
            )
    return counts, tuple(results)


COVERAGE_SCHEMA_VERSION = "sl0028-coverage-v1"


def build_coverage_document(
    *,
    generated_at: str,
    boat_model_count: int,
    source_qid_count: int,
    source_qid_coverage_counts: Mapping[str, Mapping[str, int]],
    boat_model_coverage_counts: Mapping[str, Mapping[str, int]],
) -> dict[str, Any]:
    """Assemble the retained ``coverage.json`` document: both the source-QID
    level and canonical-BoatModel level coverage counts for all five allowed
    fields."""
    return {
        "schema_version": COVERAGE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "boat_model_count": boat_model_count,
        "source_qid_count": source_qid_count,
        "note": (
            "Four mutually exclusive, exhaustive coverage states per field: "
            "normalized_candidate_present / source_statement_present / "
            "unsupported_or_malformed / no_usable_value. source_qid_level counts sum to "
            "source_qid_count for every field; boat_model_level counts sum to "
            "boat_model_count for every field, computed via strongest-available-evidence "
            "precedence over every accepted QID mapped to each BoatModel. A coverage "
            "classification only — never a canonical technical-value choice; no "
            "FieldResolution is created."
        ),
        "source_qid_level": {
            label: dict(source_qid_coverage_counts[label])
            for label in FIELD_LABEL_BY_POINTER.values()
        },
        "boat_model_level": {
            label: dict(boat_model_coverage_counts[label])
            for label in FIELD_LABEL_BY_POINTER.values()
        },
    }


def verify_coverage_self_consistency(
    *,
    linkage: Sequence[BoatModelLinkage],
    entities: Sequence[WikidataEntityData],
    full_evidence: Sequence[FieldEvidence],
    document: Mapping[str, Any],
) -> list[str]:
    """Independently recompute both coverage levels purely from *entities*/
    *full_evidence*/*linkage* and compare against a retained ``coverage.json``
    document."""
    source_counts, source_details = sl0026.summarize_field_coverage(entities, full_evidence)
    boat_model_counts, _details = summarize_boat_model_field_coverage(linkage, source_details)
    expected = build_coverage_document(
        generated_at=str(document.get("generated_at", "")),
        boat_model_count=len(linkage),
        source_qid_count=len(entities),
        source_qid_coverage_counts=source_counts,
        boat_model_coverage_counts=boat_model_counts,
    )
    if dict(document) != expected:
        return ["retained coverage.json != independently recomputed source-QID/BoatModel coverage"]
    return []


# ---------------------------------------------------------------------------
# 3. Candidate-multiplicity / value-disagreement diagnostics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoatModelFieldDisagreement:
    """One (BoatModel, field) case flagged by the controlling slice's
    disagreement-diagnostic conditions. Retained explicitly, never silently
    resolved into one canonical value."""

    hullq_id: str
    field_pointer: JsonPointer
    normalized_candidate_count: int
    distinct_normalized_values: tuple[str, ...]
    contributing_qid_count: int
    unsupported_coexists_with_normalized: bool


def _normalized_value_key(ev: FieldEvidence) -> str:
    assert ev.normalized_candidate is not None
    return f"{ev.normalized_candidate.value} {ev.normalized_candidate.unit}"


def compute_boat_model_field_disagreements(
    linkage: Sequence[BoatModelLinkage],
    allowed_evidence: Sequence[FieldEvidence],
    source_qid_details: Sequence[sl0026.EntityFieldCoverage],
) -> tuple[BoatModelFieldDisagreement, ...]:
    """Retain a diagnostic row for every (BoatModel, field) case with any of:

    - more than one normalized candidate;
    - more than one distinct normalized candidate value;
    - evidence arriving through more than one accepted mapped QID;
    - unsupported/malformed evidence coexisting with a normalized candidate.

    Only qualifying cases are retained (not the full BoatModel x field grid)
    — this is a diagnostic surface, not a resolution: no canonical value is
    chosen, and a case appearing more than once is never collapsed to a
    majority/first-seen value.
    """
    ev_index: dict[tuple[str, JsonPointer], list[FieldEvidence]] = {}
    for ev in allowed_evidence:
        ev_index.setdefault((ev.subject.id, ev.field_pointer), []).append(ev)
    bucket_index = {(d.qid, d.field_pointer): d.bucket for d in source_qid_details}

    results: list[BoatModelFieldDisagreement] = []
    for entry in linkage:
        for ptr in ALLOWED_FIELD_POINTERS:
            field_items: list[FieldEvidence] = []
            contributing_qids: set[str] = set()
            unsupported_qids: set[str] = set()
            for qid in entry.qids:
                items = ev_index.get((qid, ptr), [])
                if items:
                    contributing_qids.add(qid)
                field_items.extend(items)
                if bucket_index.get((qid, ptr)) == FieldCoverageBucket.UNSUPPORTED_OR_MALFORMED:
                    unsupported_qids.add(qid)

            normalized_items = [ev for ev in field_items if ev.normalized_candidate is not None]
            distinct_values = tuple(sorted({_normalized_value_key(ev) for ev in normalized_items}))
            unsupported_coexists = bool(unsupported_qids) and bool(normalized_items)

            if (
                len(normalized_items) > 1
                or len(distinct_values) > 1
                or len(contributing_qids) > 1
                or unsupported_coexists
            ):
                results.append(
                    BoatModelFieldDisagreement(
                        hullq_id=entry.hullq_id,
                        field_pointer=ptr,
                        normalized_candidate_count=len(normalized_items),
                        distinct_normalized_values=distinct_values,
                        contributing_qid_count=len(contributing_qids),
                        unsupported_coexists_with_normalized=unsupported_coexists,
                    )
                )
    return tuple(results)


DISAGREEMENT_SCHEMA_VERSION = "sl0028-disagreement-v1"


def build_disagreement_document(
    *, generated_at: str, disagreements: Sequence[BoatModelFieldDisagreement]
) -> dict[str, Any]:
    """Assemble the retained ``disagreement_diagnostics.json`` document."""
    return {
        "schema_version": DISAGREEMENT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "note": (
            "Every (BoatModel, field) case with more than one normalized candidate, more than "
            "one distinct normalized value, evidence arriving through more than one accepted "
            "mapped QID, or unsupported/malformed evidence coexisting with a normalized "
            "candidate. Diagnostic only: no canonical value is chosen and no case is silently "
            "resolved by majority or first-seen value. Absence of a (BoatModel, field) pair here "
            "means none of the four conditions applied to it."
        ),
        "flagged_case_count": len(disagreements),
        "cases": [
            {
                "hullq_id": d.hullq_id,
                "field_pointer": str(d.field_pointer),
                "normalized_candidate_count": d.normalized_candidate_count,
                "distinct_normalized_values": list(d.distinct_normalized_values),
                "contributing_qid_count": d.contributing_qid_count,
                "unsupported_coexists_with_normalized": d.unsupported_coexists_with_normalized,
            }
            for d in disagreements
        ],
    }


def verify_disagreement_self_consistency(
    *,
    linkage: Sequence[BoatModelLinkage],
    allowed_evidence: Sequence[FieldEvidence],
    source_qid_details: Sequence[sl0026.EntityFieldCoverage],
    document: Mapping[str, Any],
) -> list[str]:
    """Independently recompute the disagreement diagnostics purely from
    *linkage*/*allowed_evidence*/*source_qid_details* and compare against a
    retained ``disagreement_diagnostics.json`` document."""
    expected = build_disagreement_document(
        generated_at=str(document.get("generated_at", "")),
        disagreements=compute_boat_model_field_disagreements(
            linkage, allowed_evidence, source_qid_details
        ),
    )
    if dict(document) != expected:
        return [
            "retained disagreement_diagnostics.json != independently recomputed "
            "compute_boat_model_field_disagreements(...)"
        ]
    return []


# ---------------------------------------------------------------------------
# 4. basic_searchable_evidence_precursor — explicitly non-canonical diagnostic
# ---------------------------------------------------------------------------


def compute_basic_searchable_evidence_precursor(
    boat_model_coverage: Sequence[BoatModelFieldCoverage],
) -> tuple[int, tuple[str, ...]]:
    """Count canonical BoatModels with BoatModel-level normalized-candidate
    coverage for LOA AND beam AND (draft OR displacement).

    This is NOT CAL-01 D2 basic-searchable coverage and MUST NOT be reported
    as launch-readiness coverage — canonical BoatDesign/FieldResolution/
    searchable-value decisions have not been made. It is a source-evidence
    diagnostic only.
    """
    by_model: dict[str, dict[JsonPointer, Any]] = {}
    for c in boat_model_coverage:
        by_model.setdefault(c.hullq_id, {})[c.field_pointer] = c.bucket

    ncp = FieldCoverageBucket.NORMALIZED_CANDIDATE_PRESENT
    qualifying: list[str] = []
    for hullq_id, buckets in by_model.items():
        loa_ok = buckets.get(sl0026.PTR_LOA) == ncp
        beam_ok = buckets.get(sl0026.PTR_BEAM) == ncp
        draft_or_disp_ok = (
            buckets.get(sl0026.PTR_DRAFT) == ncp or buckets.get(sl0026.PTR_DISPLACEMENT) == ncp
        )
        if loa_ok and beam_ok and draft_or_disp_ok:
            qualifying.append(hullq_id)
    return len(qualifying), tuple(sorted(qualifying))


BASIC_SEARCHABLE_PRECURSOR_SCHEMA_VERSION = "sl0028-basic-searchable-evidence-precursor-v1"


def build_basic_searchable_precursor_document(
    *,
    generated_at: str,
    boat_model_count: int,
    boat_model_coverage: Sequence[BoatModelFieldCoverage],
) -> dict[str, Any]:
    """Assemble the retained ``basic_searchable_evidence_precursor.json``
    document."""
    count, qualifying_ids = compute_basic_searchable_evidence_precursor(boat_model_coverage)
    return {
        "schema_version": BASIC_SEARCHABLE_PRECURSOR_SCHEMA_VERSION,
        "generated_at": generated_at,
        "metric_name": "basic_searchable_evidence_precursor",
        "definition": (
            "canonical BoatModel count with BoatModel-level normalized_candidate_present "
            "coverage for LOA AND beam AND (draft OR displacement)"
        ),
        "non_canonical_disclaimer": (
            "This is NOT CAL-01 D2 basic-searchable coverage and MUST NOT be reported as "
            "launch-readiness coverage. No canonical BoatDesign, FieldResolution or searchable "
            "technical value has been created or decided. Source-evidence diagnostic only, "
            "intended to inform the still-pending CAL-01 D2b threshold decision."
        ),
        "boat_model_count": boat_model_count,
        "qualifying_boat_model_count": count,
        "qualifying_boat_model_percentage": (
            round(100.0 * count / boat_model_count, 4) if boat_model_count else 0.0
        ),
        "qualifying_hullq_ids": list(qualifying_ids),
    }


def verify_basic_searchable_precursor_self_consistency(
    *,
    boat_model_count: int,
    boat_model_coverage: Sequence[BoatModelFieldCoverage],
    document: Mapping[str, Any],
) -> list[str]:
    """Independently recompute the precursor metric purely from
    *boat_model_coverage* and compare against a retained
    ``basic_searchable_evidence_precursor.json`` document."""
    expected = build_basic_searchable_precursor_document(
        generated_at=str(document.get("generated_at", "")),
        boat_model_count=boat_model_count,
        boat_model_coverage=boat_model_coverage,
    )
    if dict(document) != expected:
        return [
            "retained basic_searchable_evidence_precursor.json != independently recomputed "
            "compute_basic_searchable_evidence_precursor(...)"
        ]
    return []


# ---------------------------------------------------------------------------
# 5. Research evidence bundle assembly — QID-keyed, one bundle per request QID
# ---------------------------------------------------------------------------


def build_sl0028_bundle(
    qid: str, preferred_label: str | None, allowed_evidence_for_qid: Sequence[FieldEvidence]
) -> ResearchEvidenceBundle:
    """Build the retained ``ResearchEvidenceBundle`` for one requested QID.

    Identical construction contract to the accepted SLICE-0026/0027 pilot
    bundle builders (BoatDesign-shaped, QID-keyed subject; existing
    SLICE-0012 ``migrate_evidence_v02_to_v03`` promotion; empty bundle valid),
    but with a distinct ``bundle_id``/``activity_id`` namespace
    (``BUNDLE-SL0028-*`` / ``SL0028_ACTIVITY_ID``) so persisting the
    full-boundary evidence never collides with or overwrites the already-
    imported SLICE-0026/0027 bundles. One bundle per requested QID (never per
    BoatModel) — the canonical BoatModel<->QID link is retained separately in
    the linkage document.
    """
    for ev in allowed_evidence_for_qid:
        if ev.subject.id != qid:
            raise ValueError(
                f"Evidence subject id {ev.subject.id!r} does not match requested QID {qid!r}"
            )
        if ev.field_pointer not in ALLOWED_FIELD_POINTERS:
            raise ValueError(
                f"Evidence field_pointer {ev.field_pointer!r} is not one of the five allowed "
                "Tier-1 field pointers"
            )

    promoted = tuple(migrate_evidence_v02_to_v03(ev) for ev in allowed_evidence_for_qid)
    return ResearchEvidenceBundle(
        bundle_id=f"BUNDLE-SL0028-{qid}",
        bundle_version="1",
        research_target=ResearchTarget(
            manufacturer=None, model=preferred_label or qid, first_built=None
        ),
        research_job_id=None,
        activity_id=SL0028_ACTIVITY_ID,
        observations=(),
        unresolved_findings=(),
        promoted_evidence=promoted,
        reference_crosschecks=(),
    )


# ---------------------------------------------------------------------------
# 6. Evidence-manifest document (raw entities + per-QID evidence) — offline
#    replay source of truth
# ---------------------------------------------------------------------------

EVIDENCE_MANIFEST_SCHEMA_VERSION = "sl0028-evidence-manifest-v1"


def _evidence_row(ev: FieldEvidence) -> dict[str, Any]:
    return {
        "evidence_id": ev.evidence_id,
        "field_pointer": str(ev.field_pointer),
        "subject_kind": str(ev.subject.kind),
        "subject_qid": ev.subject.id,
        "raw": {"kind": str(ev.raw.kind), "value": ev.raw.value, "unit": ev.raw.unit},
        "normalized_candidate": (
            {"value": str(ev.normalized_candidate.value), "unit": str(ev.normalized_candidate.unit)}
            if ev.normalized_candidate is not None
            else None
        ),
    }


def _raw_entity_row(entity: WikidataEntityData) -> dict[str, Any]:
    """Retained raw-entity row: enough of the acquired entity to fully
    reconstruct a ``WikidataEntityData`` and rerun extraction/coverage
    classification offline, trimmed to only the four Wikidata properties any
    of the five allowed fields can ever be extracted from (reuses the
    accepted SLICE-0026 trim, never a second trimming rule)."""
    return {
        "qid": entity.qid,
        "label": entity.label,
        "aliases": list(entity.aliases),
        "raw_claims": sl0026.trim_raw_claims_to_allowed_properties(entity.raw_claims),
    }


def rebuild_entities_from_manifest(
    evidence_manifest: Mapping[str, Any],
) -> list[WikidataEntityData]:
    """Reconstruct the exact ``WikidataEntityData`` list used to produce a
    retained ``evidence_manifest.json``, purely from its own retained
    ``raw_entities`` — zero network access. Identical row shape to the
    accepted SLICE-0026 manifest, so the accepted rebuild logic is reused
    directly rather than duplicated."""
    return sl0026.rebuild_entities_from_manifest(evidence_manifest)


def _requested_qid_evidence_rows(
    linkage: Sequence[BoatModelLinkage],
    allowed_evidence_by_qid: Mapping[str, Sequence[FieldEvidence]],
) -> list[dict[str, Any]]:
    return [
        {
            "hullq_id": entry.hullq_id,
            "qid": qid,
            "bundle_id": f"BUNDLE-SL0028-{qid}",
            "evidence": [_evidence_row(ev) for ev in allowed_evidence_by_qid.get(qid, ())],
        }
        for entry in linkage
        for qid in entry.qids
    ]


def build_evidence_manifest_document(
    *,
    generated_at: str,
    acquired_at: str,
    linkage: Sequence[BoatModelLinkage],
    entities: Sequence[WikidataEntityData],
    allowed_evidence_by_qid: Mapping[str, Sequence[FieldEvidence]],
    quality_report: WikidataQualityReport,
    requested_qid_count: int,
    acquisition_failure_count: int = 0,
) -> dict[str, Any]:
    """Assemble the retained ``evidence_manifest.json`` document: per-
    requested-QID evidence rows (raw representation + normalized candidate,
    when present), request/record/failure counts, and the trimmed raw-entity
    data needed to fully reproduce all derived SLICE-0028 documents with zero
    network access.

    ``acquisition_failure_count`` is retained separately from any coverage
    bucket per the controlling slice's acquisition-failure semantics: a
    retrieval failure/throttle/malformed-response is never reclassified as
    ``no_usable_value``. A caller that could not truthfully classify every
    requested QID MUST NOT call this builder with a complete-looking document
    — it must stop BLOCKED instead (enforced by the runner script, not here).
    """
    return {
        "schema_version": EVIDENCE_MANIFEST_SCHEMA_VERSION,
        "generated_at": generated_at,
        "acquired_at": acquired_at,
        "source_id": WIKIDATA_SOURCE_ID,
        "activity_id": SL0028_ACTIVITY_ID,
        "allowed_field_pointers": [str(p) for p in ALLOWED_FIELD_POINTERS],
        "usage_metrics": {
            "requested_qid_count": requested_qid_count,
            "fetched_entity_count": len(entities),
            "acquisition_failure_count": acquisition_failure_count,
            "retrieval_count_attributed": quality_report.retrieval_count_attributed,
        },
        "quality_report_global": {
            "malformed_statement_count": quality_report.malformed_statement_count,
            "unsupported_qualifier_count": quality_report.unsupported_qualifier_count,
            "note": (
                "Global totals produced directly by the existing adapter's "
                "extract_field_evidence across ALL extracted properties (including "
                "manufacturer/designer/ballast/total_produced, which are not part of the five "
                "SLICE-0028 allowed fields) — not decomposed per field."
            ),
        },
        "requested_qid_evidence": _requested_qid_evidence_rows(linkage, allowed_evidence_by_qid),
        "raw_entities": [_raw_entity_row(e) for e in entities],
    }


def verify_evidence_manifest_self_consistency(
    *,
    linkage: Sequence[BoatModelLinkage],
    entities: Sequence[WikidataEntityData],
    full_evidence: Sequence[FieldEvidence],
    evidence_manifest: Mapping[str, Any],
) -> list[str]:
    """Independently rebuild the expected per-QID evidence rows and raw-
    entity rows purely from *entities*/*full_evidence*/*linkage* and compare
    against a retained ``evidence_manifest.json`` document.

    The caller obtains *entities*/*full_evidence* with zero network access by
    calling ``rebuild_entities_from_manifest(evidence_manifest)`` and
    rerunning the existing adapter's ``extract_field_evidence`` on the
    result — never by trusting the manifest's own already-computed fields.
    """
    problems: list[str] = []

    allowed = sl0026.filter_to_allowed_evidence(full_evidence)
    by_qid: dict[str, list[FieldEvidence]] = {}
    for ev in allowed:
        by_qid.setdefault(ev.subject.id, []).append(ev)

    expected_rows = _requested_qid_evidence_rows(linkage, by_qid)
    if list(evidence_manifest.get("requested_qid_evidence", [])) != expected_rows:
        problems.append(
            "retained evidence_manifest.requested_qid_evidence != independently rebuilt "
            "evidence rows from the already-acquired entities/evidence"
        )

    expected_raw_entities = [_raw_entity_row(e) for e in entities]
    if list(evidence_manifest.get("raw_entities", [])) != expected_raw_entities:
        problems.append(
            "retained evidence_manifest.raw_entities != independently rebuilt raw-entity rows "
            "from the already-acquired entities"
        )

    return problems


# ---------------------------------------------------------------------------
# 7. Retained-package artifact-integrity digests
# ---------------------------------------------------------------------------

ARTIFACT_DIGESTS_SCHEMA_VERSION = "sl0028-artifact-digests-v1"
ARTIFACT_DIGESTS_FILENAME = "ARTIFACT-DIGESTS.json"


def retained_package_filenames(package_dir: Path) -> set[str]:
    """Every regular file directly inside *package_dir* except the digest
    document itself, discovered dynamically (never a hardcoded allowlist)."""
    return {
        p.name for p in package_dir.iterdir() if p.is_file() and p.name != ARTIFACT_DIGESTS_FILENAME
    }


def build_artifact_digests(*, generated_at: str, package_dir: Path) -> dict[str, Any]:
    """Build the retained ``ARTIFACT-DIGESTS.json`` document: a SHA256 digest
    of every retained SLICE-0028 package file except the digest document
    itself."""
    digests = {
        name: "sha256:" + hashlib.sha256((package_dir / name).read_bytes()).hexdigest()
        for name in sorted(retained_package_filenames(package_dir))
    }
    return {
        "schema_version": ARTIFACT_DIGESTS_SCHEMA_VERSION,
        "generated_at": generated_at,
        "digests": digests,
    }


def verify_artifact_digests_self_consistency(
    *, artifact_digests: Mapping[str, Any], package_dir: Path
) -> list[str]:
    """Recompute the SHA256 digest of every file currently in *package_dir*
    (except the digest document itself) and compare against a retained
    ``ARTIFACT-DIGESTS.json`` document."""
    mismatches: list[str] = []
    digests = artifact_digests.get("digests", {})
    retained_names = set(digests)
    expected_names = retained_package_filenames(package_dir)
    if retained_names != expected_names:
        mismatches.append(
            "digests file-name set != every retained package file (excluding "
            f"{ARTIFACT_DIGESTS_FILENAME}): missing={sorted(expected_names - retained_names)!r}, "
            f"unexpected={sorted(retained_names - expected_names)!r}"
        )
    for filename, stored in digests.items():
        file_path = package_dir / filename
        if not file_path.is_file():
            mismatches.append(f"digest entry {filename!r}: file does not exist")
            continue
        actual = "sha256:" + hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual != stored:
            mismatches.append(
                f"digest entry {filename!r}: stored={stored!r} != recomputed {actual!r}"
            )
    return mismatches
