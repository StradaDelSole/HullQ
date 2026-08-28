"""Corrected Tier-1 evidence profile + positive-control candidate selection —
SLICE-0031.

Implements the pure, deterministic logic described in
``docs/slices/SLICE-0031-corrected-tier1-evidence-profile-positive-control-selection.md``.

Given only the already-accepted, unmodified SLICE-0028 retained package
(``research/stage3/sl0028-wikidata-tier1-full-boundary/``) and SLICE-0030
retained package (``research/stage3/sl0030-wikidata-mass-unit-correction/``),
used exactly as fixed replay inputs (no reacquisition, no new discovery),
this module:

- builds one per-BoatModel Tier-1 evidence profile (coverage bucket + boolean
  normalized-candidate presence for each of the five fixed fields, the
  predecessor precursor condition, the draft/displacement both-present flag,
  and a disagreement-diagnostic flag), reusing unchanged
  ``hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot`` /
  ``hullq.bootstrap.wikidata_sl0028_full_boundary_evidence`` coverage/
  disagreement classification;
- measures the exact predecessor (pre-SLICE-0030) and corrected (post-
  SLICE-0030) ``basic_searchable_evidence_precursor`` counts and their
  overlap decomposition, strong technical-evidence subset counts, and the
  normalized-field-count distribution;
- deterministically selects a bounded (<=20) positive-control candidate pool
  for a later, separately readied BoatDesign/applicability pilot, excluding
  the two already-researched SLICE-0029 Catalina negative controls.

Explicitly does NOT:
- reacquire the 1,770-QID full-boundary dataset or run a new discovery query;
- infer, mint or persist a canonical BoatDesign generation;
- create or mutate a canonical BoatModel/crosswalk row;
- create a FieldResolution or choose/promote a canonical technical value;
- reimplement Wikidata qualifier/unit extraction, per-(QID, field) coverage
  classification, BoatModel-level coverage aggregation or disagreement
  detection (all reused unchanged from
  ``hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot`` /
  ``hullq.bootstrap.wikidata_sl0028_full_boundary_evidence``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hullq.bootstrap import wikidata_sl0026_tier1_enrichment_pilot as sl0026
from hullq.bootstrap import wikidata_sl0028_full_boundary_evidence as sl0028
from hullq.domain.provenance import JsonPointer

__all__ = [
    "AGGREGATE_PROFILE_SCHEMA_VERSION",
    "ARTIFACT_DIGESTS_FILENAME",
    "ARTIFACT_DIGESTS_SCHEMA_VERSION",
    "BOATMODEL_PROFILE_SCHEMA_VERSION",
    "CANDIDATE_POOL_LIMIT",
    "EXCLUDED_NEGATIVE_CONTROL_QIDS",
    "EXPECTED_PREDECESSOR_PRECURSOR_COUNT",
    "EXPECTED_SL0030_AFTER_NORMALIZED_CANDIDATE_COUNTS",
    "POSITIVE_CONTROL_CANDIDATES_SCHEMA_VERSION",
    "BoatModelEvidenceProfileRow",
    "FieldProfile",
    "PositiveControlCandidate",
    "build_aggregate_profile_document",
    "build_artifact_digests",
    "build_boatmodel_evidence_profile",
    "build_boatmodel_evidence_profile_document",
    "build_positive_control_candidates_document",
    "compute_aggregate_measurements",
    "compute_field_count_distribution",
    "compute_precursor_overlap_decomposition",
    "compute_strong_evidence_subsets",
    "eligible_positive_control_rows",
    "rank_positive_control_candidates",
    "retained_package_filenames",
    "select_positive_control_candidates",
    "verify_aggregate_profile_self_consistency",
    "verify_artifact_digests_self_consistency",
    "verify_boatmodel_evidence_profile_self_consistency",
    "verify_positive_control_candidates_self_consistency",
    "verify_reproduces_sl0030_after_coverage",
]

# Reused directly (not redefined) from the accepted SLICE-0026 pilot module.
ALLOWED_FIELD_POINTERS = sl0026.ALLOWED_FIELD_POINTERS
FIELD_LABEL_BY_POINTER = sl0026.FIELD_LABEL_BY_POINTER
FieldCoverageBucket = sl0026.FieldCoverageBucket

# The accepted SLICE-0028 predecessor (pre-SLICE-0030-correction) precursor
# count, to be independently recomputed from the retained pre-correction
# evidence -- never trusted blindly (controlling slice "Corrected predecessor
# precursor").
EXPECTED_PREDECESSOR_PRECURSOR_COUNT = 607

# The accepted SLICE-0030 corrected/current five-field normalized-candidate
# marginal totals, to be independently reproduced before any new
# interpretation is made (controlling slice "Per-field corrected coverage").
EXPECTED_SL0030_AFTER_NORMALIZED_CANDIDATE_COUNTS: dict[str, int] = {
    "loa": 888,
    "lwl": 848,
    "beam": 891,
    "draft": 691,
    "displacement": 858,
}

# The two already-researched SLICE-0029 Catalina negative-control QIDs, fixed
# by the controlling slice and never expanded/discovered.
EXCLUDED_NEGATIVE_CONTROL_QIDS: frozenset[str] = frozenset({"Q5051252", "Q5051253"})

CANDIDATE_POOL_LIMIT = 20


def verify_reproduces_sl0030_after_coverage(
    per_field_coverage_counts: Mapping[str, Mapping[str, int]],
) -> list[str]:
    """Check that *per_field_coverage_counts* (a
    ``{field_label: {bucket: count}}`` mapping, as produced by
    ``sl0028.summarize_boat_model_field_coverage``) reproduces the accepted
    SLICE-0030 corrected/current ``normalized_candidate_present`` marginal
    totals for all five fixed fields, before any SLICE-0031 profile or
    aggregate measurement is built from it.
    """
    problems: list[str] = []
    for label, expected in EXPECTED_SL0030_AFTER_NORMALIZED_CANDIDATE_COUNTS.items():
        actual = per_field_coverage_counts.get(label, {}).get("normalized_candidate_present")
        if actual != expected:
            problems.append(
                f"{label}: normalized_candidate_present={actual!r} != accepted SLICE-0030 "
                f"corrected/current marginal total {expected}"
            )
    return problems


# ---------------------------------------------------------------------------
# 1. Per-BoatModel Tier-1 evidence profile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldProfile:
    """One BoatModel's aggregated coverage state for one fixed field."""

    bucket: Any
    normalized_candidate_present: bool


@dataclass(frozen=True)
class BoatModelEvidenceProfileRow:
    """One canonical BoatModel's corrected/current Tier-1 evidence profile.

    Purely a source-evidence classification: no canonical technical value or
    FieldResolution is asserted or implied by any field here.
    """

    hullq_id: str
    qids: tuple[str, ...]
    fields: Mapping[str, FieldProfile]
    normalized_field_count: int
    precursor_satisfied: bool
    draft_and_displacement_present: bool
    has_disagreement_diagnostic: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", dict(self.fields))


def build_boatmodel_evidence_profile(
    linkage: Sequence[sl0028.BoatModelLinkage],
    boat_model_coverage: Sequence[sl0028.BoatModelFieldCoverage],
    disagreements: Sequence[sl0028.BoatModelFieldDisagreement],
) -> tuple[BoatModelEvidenceProfileRow, ...]:
    """Build one deterministic evidence-profile row per *linkage* entry from
    already-computed BoatModel-level coverage and disagreement diagnostics.

    Never reclassifies or recomputes coverage/disagreement itself -- purely
    reshapes the existing accepted per-(BoatModel, field) outputs of
    ``sl0028.summarize_boat_model_field_coverage`` /
    ``sl0028.compute_boat_model_field_disagreements`` into the fixed
    SLICE-0031 profile shape.
    """
    coverage_index: dict[tuple[str, JsonPointer], Any] = {
        (c.hullq_id, c.field_pointer): c.bucket for c in boat_model_coverage
    }
    flagged_hullq_ids = {d.hullq_id for d in disagreements}

    ncp = FieldCoverageBucket.NORMALIZED_CANDIDATE_PRESENT
    rows: list[BoatModelEvidenceProfileRow] = []
    for entry in linkage:
        fields: dict[str, FieldProfile] = {}
        for ptr in ALLOWED_FIELD_POINTERS:
            bucket = coverage_index[(entry.hullq_id, ptr)]
            fields[FIELD_LABEL_BY_POINTER[ptr]] = FieldProfile(
                bucket=bucket, normalized_candidate_present=(bucket == ncp)
            )
        normalized_field_count = sum(1 for fp in fields.values() if fp.normalized_candidate_present)
        loa_ok = fields["loa"].normalized_candidate_present
        beam_ok = fields["beam"].normalized_candidate_present
        draft_ok = fields["draft"].normalized_candidate_present
        disp_ok = fields["displacement"].normalized_candidate_present
        rows.append(
            BoatModelEvidenceProfileRow(
                hullq_id=entry.hullq_id,
                qids=entry.qids,
                fields=fields,
                normalized_field_count=normalized_field_count,
                precursor_satisfied=bool(loa_ok and beam_ok and (draft_ok or disp_ok)),
                draft_and_displacement_present=bool(draft_ok and disp_ok),
                has_disagreement_diagnostic=entry.hullq_id in flagged_hullq_ids,
            )
        )
    return tuple(rows)


BOATMODEL_PROFILE_SCHEMA_VERSION = "sl0031-boatmodel-evidence-profile-v1"


def _profile_row_document(row: BoatModelEvidenceProfileRow) -> dict[str, Any]:
    return {
        "hullq_id": row.hullq_id,
        "qids": list(row.qids),
        "fields": {
            label: {
                "coverage_bucket": fp.bucket.value,
                "normalized_candidate_present": fp.normalized_candidate_present,
            }
            for label, fp in row.fields.items()
        },
        "normalized_field_count": row.normalized_field_count,
        "precursor_satisfied": row.precursor_satisfied,
        "draft_and_displacement_present": row.draft_and_displacement_present,
        "has_disagreement_diagnostic": row.has_disagreement_diagnostic,
    }


def build_boatmodel_evidence_profile_document(
    *, generated_at: str, rows: Sequence[BoatModelEvidenceProfileRow]
) -> dict[str, Any]:
    """Assemble the retained ``boatmodel_evidence_profile.json`` document: one
    deterministic evidence-profile row for every canonical BoatModel in
    *rows*, ordered exactly as given (the fixed linkage's own ascending
    canonical-HullQ-ID order)."""
    return {
        "schema_version": BOATMODEL_PROFILE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "boat_model_count": len(rows),
        "note": (
            "One row per canonical BoatModel over the fixed accepted 1,770-BoatModel boundary. "
            "coverage_bucket is one of the four accepted mutually exclusive per-field evidence "
            "states (normalized_candidate_present / source_statement_present / "
            "unsupported_or_malformed / no_usable_value), aggregated over every accepted QID "
            "mapped to that BoatModel via strongest-available-evidence precedence "
            "(sl0028.summarize_boat_model_field_coverage), never a canonical value choice. "
            "precursor_satisfied is the corrected/current LOA + beam + (draft OR displacement) "
            "condition. has_disagreement_diagnostic is true iff this BoatModel has at least one "
            "retained SLICE-0028/0030-style disagreement/unsupported-coexistence diagnostic "
            "(sl0028.compute_boat_model_field_disagreements) on any of the five fixed fields "
            "under the corrected/current evidence path. No canonical technical value or "
            "FieldResolution is asserted anywhere in this document."
        ),
        "boat_models": [_profile_row_document(r) for r in rows],
    }


def verify_boatmodel_evidence_profile_self_consistency(
    *,
    linkage: Sequence[sl0028.BoatModelLinkage],
    boat_model_coverage: Sequence[sl0028.BoatModelFieldCoverage],
    disagreements: Sequence[sl0028.BoatModelFieldDisagreement],
    document: Mapping[str, Any],
) -> list[str]:
    """Independently rebuild the expected evidence-profile document purely
    from *linkage*/*boat_model_coverage*/*disagreements* and compare against a
    retained ``boatmodel_evidence_profile.json`` document."""
    rows = build_boatmodel_evidence_profile(linkage, boat_model_coverage, disagreements)
    expected = build_boatmodel_evidence_profile_document(
        generated_at=str(document.get("generated_at", "")), rows=rows
    )
    if dict(document) != expected:
        return [
            "retained boatmodel_evidence_profile.json != independently rebuilt profile from "
            "the fixed linkage/coverage/disagreement inputs"
        ]
    return []


# ---------------------------------------------------------------------------
# 2. Aggregate measurements
# ---------------------------------------------------------------------------


def compute_field_count_distribution(
    rows: Sequence[BoatModelEvidenceProfileRow],
) -> dict[str, int]:
    """Count BoatModels with exactly 0..5 normalized-candidate fields."""
    distribution = {str(i): 0 for i in range(6)}
    for row in rows:
        distribution[str(row.normalized_field_count)] += 1
    return distribution


def compute_precursor_overlap_decomposition(
    rows: Sequence[BoatModelEvidenceProfileRow],
) -> dict[str, int]:
    """Among corrected-precursor-positive BoatModels, decompose by which of
    draft/displacement contributed the required (draft OR displacement) leg:
    draft only, displacement only, or both."""
    draft_only = displacement_only = both = 0
    for row in rows:
        if not row.precursor_satisfied:
            continue
        draft_ok = row.fields["draft"].normalized_candidate_present
        disp_ok = row.fields["displacement"].normalized_candidate_present
        if draft_ok and disp_ok:
            both += 1
        elif draft_ok:
            draft_only += 1
        else:
            displacement_only += 1
    return {"draft_only": draft_only, "displacement_only": displacement_only, "both": both}


def compute_strong_evidence_subsets(rows: Sequence[BoatModelEvidenceProfileRow]) -> dict[str, int]:
    """Retain counts for the four fixed strong technical-evidence subsets."""
    loa_beam_draft_displacement = 0
    loa_lwl_beam_draft_or_displacement = 0
    all_five_fields = 0
    gte4_no_disagreement = 0
    for row in rows:
        loa = row.fields["loa"].normalized_candidate_present
        lwl = row.fields["lwl"].normalized_candidate_present
        beam = row.fields["beam"].normalized_candidate_present
        draft = row.fields["draft"].normalized_candidate_present
        disp = row.fields["displacement"].normalized_candidate_present
        if loa and beam and draft and disp:
            loa_beam_draft_displacement += 1
        if loa and lwl and beam and (draft or disp):
            loa_lwl_beam_draft_or_displacement += 1
        if row.normalized_field_count == 5:
            all_five_fields += 1
        if row.normalized_field_count >= 4 and not row.has_disagreement_diagnostic:
            gte4_no_disagreement += 1
    return {
        "loa_beam_draft_displacement": loa_beam_draft_displacement,
        "loa_lwl_beam_draft_or_displacement": loa_lwl_beam_draft_or_displacement,
        "all_five_fields": all_five_fields,
        "gte4_normalized_no_disagreement": gte4_no_disagreement,
    }


def compute_aggregate_measurements(
    rows: Sequence[BoatModelEvidenceProfileRow],
    *,
    per_field_corrected_coverage: Mapping[str, Mapping[str, int]],
    predecessor_precursor_count: int,
) -> dict[str, Any]:
    """Compute every SLICE-0031 aggregate measurement purely from *rows* (the
    already-built corrected evidence profile) plus the two already-verified
    inputs that are not otherwise derivable from *rows* alone:
    *per_field_corrected_coverage* (BoatModel-level coverage bucket counts,
    for cross-checking against the accepted SLICE-0030 marginal totals) and
    *predecessor_precursor_count* (measured separately from the
    pre-SLICE-0030-correction evidence, never from *rows*, which are already
    corrected)."""
    boat_model_count = len(rows)
    field_count_distribution = compute_field_count_distribution(rows)
    corrected_precursor_count = sum(1 for row in rows if row.precursor_satisfied)

    def _pct(count: int) -> float:
        return round(100.0 * count / boat_model_count, 4) if boat_model_count else 0.0

    predecessor_pct = _pct(predecessor_precursor_count)
    corrected_pct = _pct(corrected_precursor_count)

    return {
        "boat_model_count": boat_model_count,
        "per_field_corrected_coverage": {
            label: dict(counts) for label, counts in per_field_corrected_coverage.items()
        },
        "normalized_field_count_distribution": field_count_distribution,
        "cumulative": {
            "gte_3": sum(v for k, v in field_count_distribution.items() if int(k) >= 3),
            "gte_4": sum(v for k, v in field_count_distribution.items() if int(k) >= 4),
            "all_5": field_count_distribution["5"],
        },
        "predecessor_precursor": {
            "count": predecessor_precursor_count,
            "boat_model_count": boat_model_count,
            "percentage": predecessor_pct,
        },
        "corrected_precursor": {
            "count": corrected_precursor_count,
            "boat_model_count": boat_model_count,
            "percentage": corrected_pct,
        },
        "precursor_delta": {
            "absolute": corrected_precursor_count - predecessor_precursor_count,
            "percentage_points": round(corrected_pct - predecessor_pct, 4),
        },
        "precursor_overlap_decomposition": compute_precursor_overlap_decomposition(rows),
        "strong_evidence_subsets": compute_strong_evidence_subsets(rows),
    }


AGGREGATE_PROFILE_SCHEMA_VERSION = "sl0031-aggregate-profile-v1"


def build_aggregate_profile_document(
    *,
    generated_at: str,
    rows: Sequence[BoatModelEvidenceProfileRow],
    per_field_corrected_coverage: Mapping[str, Mapping[str, int]],
    predecessor_precursor_count: int,
) -> dict[str, Any]:
    """Assemble the retained ``aggregate_profile.json`` document."""
    measurements = compute_aggregate_measurements(
        rows,
        per_field_corrected_coverage=per_field_corrected_coverage,
        predecessor_precursor_count=predecessor_precursor_count,
    )
    return {
        "schema_version": AGGREGATE_PROFILE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "non_canonical_disclaimer": (
            "Every measurement in this document is a source-evidence diagnostic only. It is NOT "
            "CAL-01 D2 basic-searchable coverage, is NOT a launch-readiness metric, and does not "
            "mean any BoatModel already possesses an accepted canonical searchable value. No "
            "CAL-01 D2/D2b threshold or G4 claim is made or implied."
        ),
        **measurements,
    }


def verify_aggregate_profile_self_consistency(
    *,
    rows: Sequence[BoatModelEvidenceProfileRow],
    per_field_corrected_coverage: Mapping[str, Mapping[str, int]],
    predecessor_precursor_count: int,
    document: Mapping[str, Any],
) -> list[str]:
    """Independently rebuild the expected aggregate document purely from
    *rows*/*per_field_corrected_coverage*/*predecessor_precursor_count* and
    compare against a retained ``aggregate_profile.json`` document."""
    expected = build_aggregate_profile_document(
        generated_at=str(document.get("generated_at", "")),
        rows=rows,
        per_field_corrected_coverage=per_field_corrected_coverage,
        predecessor_precursor_count=predecessor_precursor_count,
    )
    if dict(document) != expected:
        return [
            "retained aggregate_profile.json != independently recomputed aggregate measurements "
            "from the fixed corrected evidence profile"
        ]
    return []


# ---------------------------------------------------------------------------
# 3. Positive-control candidate-pool selection
# ---------------------------------------------------------------------------


def eligible_positive_control_rows(
    rows: Sequence[BoatModelEvidenceProfileRow],
) -> tuple[BoatModelEvidenceProfileRow, ...]:
    """Every BoatModel satisfying all fixed SLICE-0031 eligibility rules,
    unranked and untruncated."""
    return tuple(
        row
        for row in rows
        if row.precursor_satisfied
        and row.normalized_field_count >= 4
        and not row.has_disagreement_diagnostic
        and not (set(row.qids) & EXCLUDED_NEGATIVE_CONTROL_QIDS)
    )


@dataclass(frozen=True)
class PositiveControlCandidate:
    rank: int
    hullq_id: str
    qids: tuple[str, ...]
    normalized_field_count: int
    draft_and_displacement_present: bool
    lwl_present: bool


def rank_positive_control_candidates(
    eligible_rows: Sequence[BoatModelEvidenceProfileRow], *, limit: int = CANDIDATE_POOL_LIMIT
) -> tuple[PositiveControlCandidate, ...]:
    """Deterministically rank *eligible_rows* by the fixed ordered keys
    (normalized_field_count desc; both draft+displacement before only one;
    LWL present before LWL missing; hullq_id asc as the final stable
    tie-break) and retain the first *limit*."""
    ordered = sorted(
        eligible_rows,
        key=lambda row: (
            -row.normalized_field_count,
            0 if row.draft_and_displacement_present else 1,
            0 if row.fields["lwl"].normalized_candidate_present else 1,
            row.hullq_id,
        ),
    )
    selected = ordered[:limit]
    return tuple(
        PositiveControlCandidate(
            rank=i + 1,
            hullq_id=row.hullq_id,
            qids=row.qids,
            normalized_field_count=row.normalized_field_count,
            draft_and_displacement_present=row.draft_and_displacement_present,
            lwl_present=row.fields["lwl"].normalized_candidate_present,
        )
        for i, row in enumerate(selected)
    )


def select_positive_control_candidates(
    rows: Sequence[BoatModelEvidenceProfileRow], *, limit: int = CANDIDATE_POOL_LIMIT
) -> tuple[PositiveControlCandidate, ...]:
    """Full fixed selection: eligibility filter, then deterministic ranking,
    then truncation to *limit* (or fewer, if fewer eligible BoatModels
    exist)."""
    return rank_positive_control_candidates(eligible_positive_control_rows(rows), limit=limit)


POSITIVE_CONTROL_CANDIDATES_SCHEMA_VERSION = "sl0031-positive-control-candidates-v1"


def build_positive_control_candidates_document(
    *, generated_at: str, rows: Sequence[BoatModelEvidenceProfileRow]
) -> dict[str, Any]:
    """Assemble the retained ``positive_control_candidates.json`` document.

    The retained artifact contract is deliberately NOT parameterizable:
    ``candidate_pool_limit`` is always the fixed ``CANDIDATE_POOL_LIMIT``
    (20), never an argument, so a caller cannot construct (and no tampered
    retained document can be mistaken for) a document built against a
    different limit. ``pool_result`` is derived from whether the full
    *eligible* set (``eligible_rows``, before truncation) is non-empty --
    never from ``candidate_pool_limit`` or the truncated ``candidates`` list,
    both of which a tampered document could otherwise set to zero/empty
    (e.g. limit=0) to flip the result independently of the real eligible
    set (controlling slice fail-closed requirement, SLICE-0031 review
    amendment).
    """
    eligible_rows = eligible_positive_control_rows(rows)
    candidates = rank_positive_control_candidates(eligible_rows, limit=CANDIDATE_POOL_LIMIT)
    pool_result = "POSITIVE_CONTROL_POOL_AVAILABLE" if eligible_rows else "NO_POSITIVE_CONTROL_POOL"
    return {
        "schema_version": POSITIVE_CONTROL_CANDIDATES_SCHEMA_VERSION,
        "generated_at": generated_at,
        "eligibility_rule": (
            "within the fixed 1,770 canonical BoatModel boundary; satisfies corrected LOA + "
            "beam + (draft OR displacement); at least 4 of 5 fixed fields normalized; no "
            "retained disagreement/unsupported-coexistence diagnostic on the five fixed fields; "
            "not Q5051252 (Catalina 22) or Q5051253 (Catalina 30)"
        ),
        "ranking_rule": (
            "normalized_field_count descending; both draft and displacement normalized before "
            "only one of them; LWL normalized before LWL missing; canonical hullq_id ascending "
            "as the final stable tie-break"
        ),
        "excluded_negative_control_qids": sorted(EXCLUDED_NEGATIVE_CONTROL_QIDS),
        "eligible_candidate_count": len(eligible_rows),
        "candidate_pool_limit": CANDIDATE_POOL_LIMIT,
        "candidate_pool_size": len(candidates),
        "pool_result": pool_result,
        "non_canonical_disclaimer": (
            "A positive pool means only that technically strong BoatModel-scoped source evidence "
            "exists for later applicability research. It does not mean any selected BoatModel has "
            "a proven BoatDesign generation boundary, a cleared primary source, or a promotable "
            "canonical value. Retention here is not authorization to research all listed "
            "candidates externally."
        ),
        "candidates": [
            {
                "rank": c.rank,
                "hullq_id": c.hullq_id,
                "qids": list(c.qids),
                "normalized_field_count": c.normalized_field_count,
                "draft_and_displacement_present": c.draft_and_displacement_present,
                "lwl_present": c.lwl_present,
            }
            for c in candidates
        ],
    }


def verify_positive_control_candidates_self_consistency(
    *,
    rows: Sequence[BoatModelEvidenceProfileRow],
    document: Mapping[str, Any],
) -> list[str]:
    """Independently rebuild the expected candidate-pool document purely from
    *rows*, using the fixed non-parameterizable ``CANDIDATE_POOL_LIMIT`` --
    NEVER the retained document's own ``candidate_pool_limit``, which is
    untrusted input a tampered document fully controls -- and compare against
    a retained ``positive_control_candidates.json`` document.
    """
    problems: list[str] = []
    retained_limit = document.get("candidate_pool_limit")
    if retained_limit != CANDIDATE_POOL_LIMIT:
        problems.append(
            f"retained positive_control_candidates.candidate_pool_limit={retained_limit!r} != "
            f"the fixed non-parameterizable SLICE-0031 limit {CANDIDATE_POOL_LIMIT}"
        )
    expected = build_positive_control_candidates_document(
        generated_at=str(document.get("generated_at", "")), rows=rows
    )
    if dict(document) != expected:
        problems.append(
            "retained positive_control_candidates.json != independently rebuilt candidate pool "
            "from the fixed corrected evidence profile using the fixed CANDIDATE_POOL_LIMIT"
        )
    return problems


# ---------------------------------------------------------------------------
# 4. Retained-package artifact-integrity digests
# ---------------------------------------------------------------------------

ARTIFACT_DIGESTS_SCHEMA_VERSION = "sl0031-artifact-digests-v1"
ARTIFACT_DIGESTS_FILENAME = "ARTIFACT-DIGESTS.json"


def retained_package_filenames(package_dir: Path) -> set[str]:
    """Every regular file directly inside *package_dir* except the digest
    document itself, discovered dynamically (never a hardcoded allowlist)."""
    return {
        p.name for p in package_dir.iterdir() if p.is_file() and p.name != ARTIFACT_DIGESTS_FILENAME
    }


def build_artifact_digests(*, generated_at: str, package_dir: Path) -> dict[str, Any]:
    """Build the retained ``ARTIFACT-DIGESTS.json`` document: a SHA256 digest
    of every retained SLICE-0031 package file except the digest document
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
