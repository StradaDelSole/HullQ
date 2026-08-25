"""Wikimedia lead independent identity-verification pilot — SLICE-0024.

Implements the pure, deterministic measurement logic described in
``docs/slices/SLICE-0024-wikimedia-lead-independent-identity-verification-pilot.md``.

This module performs no network acquisition. Given the already-retained
SLICE-0023 quality sample and a manually-compiled bounded external research
log (produced by a human/agent following the fixed research protocol in the
controlling slice document, never by automated web crawling in repository
code), it:

- hard-asserts the accepted immutable SLICE-0023 blob pins and counts (409
  incremental leads, 150-QID quality sample, 102/19/29 prior-tag split, the
  1,770 canonical BoatModel count and 1,772 historical crosswalk count) before
  any candidate selection;
- reproduces the exact deterministic 18/6/6 SHA256-ordered sample selection
  from the three prior-tag strata, with no hand-picking/backfill;
- validates every retained research-action log against the fixed per-candidate
  (<=2 search / <=4 source-page-eval / <=6 combined) and global (<=60 / <=120 /
  <=180) action ceilings;
- validates the fixed qualifying-source-class vocabulary and the
  strong-source / two-independent-specialist evidence-strength rules,
  including genuine source independence;
- validates ``subject_outcome`` / ``evidence_strength`` internal consistency;
- computes every required yield/source/effort/calibration metric mechanically
  from the retained per-candidate results;
- applies the precommitted, mechanical recommendation rule.

Explicitly does NOT:
- perform any web search, page fetch or other network acquisition;
- create, modify or delete any canonical HullQ row;
- mint a HullQ ID for any lead;
- promote Wikipedia/Wikidata/SailboatData/search/discovery material to
  qualifying verification evidence;
- grant production/bulk/automation clearance to any evaluated source.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from hullq.bootstrap.wikimedia_sl0023_category_leads import git_blob_sha1

__all__ = [
    "ACCEPTED_AMBIGUOUS_COUNT",
    "ACCEPTED_CANONICAL_BOAT_MODEL_COUNT",
    "ACCEPTED_HISTORICAL_CROSSWALK_COUNT",
    "ACCEPTED_INCREMENTAL_QID_LEAD_COUNT",
    "ACCEPTED_OUT_OF_SCOPE_COUNT",
    "ACCEPTED_PLAUSIBLE_COUNT",
    "ACCEPTED_QUALITY_SAMPLE_COUNT",
    "DISCOVERY_MANIFEST_GIT_BLOB_SHA1",
    "GLOBAL_COMBINED_ACTION_CEILING",
    "GLOBAL_SEARCH_QUERY_CEILING",
    "GLOBAL_SOURCE_EVALUATION_CEILING",
    "IN_SCOPE_MIN_INDEPENDENT_SUPPORTED",
    "IN_SCOPE_MIN_STRONG_SOURCE",
    "MAX_COMBINED_ACTIONS_PER_CANDIDATE",
    "MAX_MEDIAN_ACTIONS_FOR_FULL_CAMPAIGN",
    "MAX_SEARCH_QUERIES_PER_CANDIDATE",
    "MAX_SOURCE_EVALUATIONS_PER_CANDIDATE",
    "QUALITY_SAMPLE_GIT_BLOB_SHA1",
    "SL0018_MANIFEST_PATH",
    "SL0023_DISCOVERY_MANIFEST_PATH",
    "SL0023_QUALITY_SAMPLE_PATH",
    "SL0023_SOURCE_ASSESSMENT_PATH",
    "SOURCE_ASSESSMENT_GIT_BLOB_SHA1",
    "STRATUM_CAPS",
    "STRATUM_ORDER",
    "STRONG_SOURCE_CLASSES",
    "THRESHOLD_STRATA",
    "EvidenceStrength",
    "ImmutableBoundaries",
    "ImmutableBoundaryIntegrityError",
    "PriorTag",
    "Recommendation",
    "ResearchActionCeilingError",
    "SampleSelection",
    "SourceClass",
    "SubjectOutcome",
    "build_candidate_metadata",
    "build_verification_results_document",
    "build_verification_sample_document",
    "compute_evidence_strength_from_citations",
    "compute_metrics",
    "compute_qid_sha256",
    "determine_recommendation",
    "load_and_verify_immutable_boundaries",
    "select_deterministic_sample",
    "validate_action_ceilings",
    "validate_outcome_evidence_consistency",
    "verify_artifact_digests_self_consistency",
    "verify_metrics_self_consistency",
    "verify_recommendation_self_consistency",
    "verify_result_row_self_consistency",
    "verify_sample_selection_self_consistency",
]

# ---------------------------------------------------------------------------
# Accepted immutable SLICE-0023 comparison boundaries (controlling slice
# "Immutable accepted input boundary")
# ---------------------------------------------------------------------------

ACCEPTED_INCREMENTAL_QID_LEAD_COUNT = 409
ACCEPTED_QUALITY_SAMPLE_COUNT = 150
ACCEPTED_PLAUSIBLE_COUNT = 102
ACCEPTED_OUT_OF_SCOPE_COUNT = 19
ACCEPTED_AMBIGUOUS_COUNT = 29
ACCEPTED_CANONICAL_BOAT_MODEL_COUNT = 1770
ACCEPTED_HISTORICAL_CROSSWALK_COUNT = 1772

QUALITY_SAMPLE_GIT_BLOB_SHA1 = "e26fde36c487f54344e4392ed7f3d7e735f07abf"
DISCOVERY_MANIFEST_GIT_BLOB_SHA1 = "9ddc5483d8b3d34e97aa36d5d72bd28fefe19c0e"
SOURCE_ASSESSMENT_GIT_BLOB_SHA1 = "d025ca31574d38b2bab03fd8211859c10440dd4b"

ROOT = Path(__file__).resolve().parents[3]
SL0023_DIR = ROOT / "research" / "bootstrap" / "wikimedia" / "sl0023-category-leads"
SL0023_QUALITY_SAMPLE_PATH = SL0023_DIR / "quality_sample.json"
SL0023_DISCOVERY_MANIFEST_PATH = SL0023_DIR / "discovery_manifest.json"
SL0023_SOURCE_ASSESSMENT_PATH = SL0023_DIR / "source_assessment.json"
SL0018_MANIFEST_PATH = (
    ROOT / "research" / "bootstrap" / "wikidata" / "sl0018-2500" / "manifest.json"
)


class ImmutableBoundaryIntegrityError(RuntimeError):
    """Raised when a retained SLICE-0023/0018 input artifact no longer
    reproduces its accepted historical blob hash/count.

    SLICE-0024 MUST fail closed (BLOCKED) rather than silently measure
    against a drifted immutable boundary.
    """


class ResearchActionCeilingError(RuntimeError):
    """Raised when a retained (or projected) research-action count would
    exceed a fixed per-candidate or global ceiling."""


@dataclass(frozen=True)
class ImmutableBoundaries:
    """The immutable accepted SLICE-0023/0018 comparison boundaries, loaded
    and fingerprinted once before candidate selection."""

    quality_sample_blob_sha1: str
    discovery_manifest_blob_sha1: str
    source_assessment_blob_sha1: str
    incremental_qid_lead_count: int
    quality_sample_total: int
    quality_tag_counts: dict[str, int]
    canonical_boat_model_count: int
    historical_crosswalk_count: int
    quality_review_rows: tuple[dict[str, Any], ...]
    wikidata_context_by_qid: dict[str, dict[str, Any]]
    discovery_pages_by_qid: dict[str, list[dict[str, Any]]]


def load_and_verify_immutable_boundaries(
    *,
    quality_sample_path: Path = SL0023_QUALITY_SAMPLE_PATH,
    discovery_manifest_path: Path = SL0023_DISCOVERY_MANIFEST_PATH,
    source_assessment_path: Path = SL0023_SOURCE_ASSESSMENT_PATH,
    sl0018_manifest_path: Path = SL0018_MANIFEST_PATH,
) -> ImmutableBoundaries:
    """Load, fingerprint and hard-assert every accepted SLICE-0024 immutable
    input boundary before any candidate selection or research is used.

    Fails closed via ``ImmutableBoundaryIntegrityError`` if any pinned Git
    blob SHA1 or any accepted count has drifted. Never writes to any input
    file.
    """
    quality_sample_bytes = quality_sample_path.read_bytes()
    quality_sample_blob_sha1 = git_blob_sha1(quality_sample_bytes)
    if quality_sample_blob_sha1 != QUALITY_SAMPLE_GIT_BLOB_SHA1:
        raise ImmutableBoundaryIntegrityError(
            f"Retained quality_sample.json at {quality_sample_path} failed Git blob integrity "
            f"check: sha1={quality_sample_blob_sha1!r}, expected {QUALITY_SAMPLE_GIT_BLOB_SHA1!r}"
        )

    discovery_manifest_bytes = discovery_manifest_path.read_bytes()
    discovery_manifest_blob_sha1 = git_blob_sha1(discovery_manifest_bytes)
    if discovery_manifest_blob_sha1 != DISCOVERY_MANIFEST_GIT_BLOB_SHA1:
        raise ImmutableBoundaryIntegrityError(
            f"Retained discovery_manifest.json at {discovery_manifest_path} failed Git blob "
            f"integrity check: sha1={discovery_manifest_blob_sha1!r}, expected "
            f"{DISCOVERY_MANIFEST_GIT_BLOB_SHA1!r}"
        )

    source_assessment_bytes = source_assessment_path.read_bytes()
    source_assessment_blob_sha1 = git_blob_sha1(source_assessment_bytes)
    if source_assessment_blob_sha1 != SOURCE_ASSESSMENT_GIT_BLOB_SHA1:
        raise ImmutableBoundaryIntegrityError(
            f"Retained source_assessment.json at {source_assessment_path} failed Git blob "
            f"integrity check: sha1={source_assessment_blob_sha1!r}, expected "
            f"{SOURCE_ASSESSMENT_GIT_BLOB_SHA1!r}"
        )

    quality_sample = json.loads(quality_sample_bytes.decode("utf-8"))
    incremental_count = quality_sample.get("unique_incremental_qid_lead_count")
    if incremental_count != ACCEPTED_INCREMENTAL_QID_LEAD_COUNT:
        raise ImmutableBoundaryIntegrityError(
            "Retained unique_incremental_qid_lead_count does not equal the accepted "
            f"{ACCEPTED_INCREMENTAL_QID_LEAD_COUNT}: got {incremental_count!r}"
        )
    total_sampled = quality_sample.get("total_sampled")
    if total_sampled != ACCEPTED_QUALITY_SAMPLE_COUNT:
        raise ImmutableBoundaryIntegrityError(
            "Retained total_sampled does not equal the accepted "
            f"{ACCEPTED_QUALITY_SAMPLE_COUNT}: got {total_sampled!r}"
        )
    quality_tag_counts = quality_sample.get("quality_tag_counts", {})
    expected_tag_counts = {
        "plausible_model_or_class_lead": ACCEPTED_PLAUSIBLE_COUNT,
        "obvious_out_of_scope": ACCEPTED_OUT_OF_SCOPE_COUNT,
        "ambiguous": ACCEPTED_AMBIGUOUS_COUNT,
    }
    if quality_tag_counts != expected_tag_counts:
        raise ImmutableBoundaryIntegrityError(
            f"Retained quality_tag_counts={quality_tag_counts!r} != accepted "
            f"{expected_tag_counts!r}"
        )

    sl0018_manifest = json.loads(sl0018_manifest_path.read_bytes().decode("utf-8"))
    canonical_count = sl0018_manifest.get("counts", {}).get(
        "combined_canonical_boat_model_count_expected"
    )
    if canonical_count != ACCEPTED_CANONICAL_BOAT_MODEL_COUNT:
        raise ImmutableBoundaryIntegrityError(
            "Retained combined_canonical_boat_model_count_expected does not equal the accepted "
            f"{ACCEPTED_CANONICAL_BOAT_MODEL_COUNT}: got {canonical_count!r}"
        )
    retained_crosswalk = sl0018_manifest.get("retained_crosswalk")
    if not isinstance(retained_crosswalk, list) or len(retained_crosswalk) != (
        ACCEPTED_HISTORICAL_CROSSWALK_COUNT
    ):
        raise ImmutableBoundaryIntegrityError(
            "Retained crosswalk count does not equal the accepted "
            f"{ACCEPTED_HISTORICAL_CROSSWALK_COUNT}: got "
            f"{len(retained_crosswalk) if isinstance(retained_crosswalk, list) else None!r}"
        )

    quality_review_rows = tuple(quality_sample.get("quality_review", []))
    if len(quality_review_rows) != ACCEPTED_QUALITY_SAMPLE_COUNT:
        raise ImmutableBoundaryIntegrityError(
            f"Retained quality_review row count {len(quality_review_rows)} != "
            f"{ACCEPTED_QUALITY_SAMPLE_COUNT}"
        )
    wikidata_context_by_qid = {
        row["qid"]: row for row in quality_sample.get("wikidata_context", [])
    }

    discovery_manifest = json.loads(discovery_manifest_bytes.decode("utf-8"))
    discovery_pages_by_qid: dict[str, list[dict[str, Any]]] = {}
    for page_info in discovery_manifest.get("unique_pages", {}).values():
        qid = page_info.get("qid")
        if qid is None:
            continue
        discovery_pages_by_qid.setdefault(qid, []).append(
            {
                "title": page_info["title"],
                "canonical_url": page_info["canonical_url"],
                "categories": list(page_info["categories"]),
            }
        )

    return ImmutableBoundaries(
        quality_sample_blob_sha1=quality_sample_blob_sha1,
        discovery_manifest_blob_sha1=discovery_manifest_blob_sha1,
        source_assessment_blob_sha1=source_assessment_blob_sha1,
        incremental_qid_lead_count=incremental_count,
        quality_sample_total=total_sampled,
        quality_tag_counts=dict(quality_tag_counts),
        canonical_boat_model_count=canonical_count,
        historical_crosswalk_count=len(retained_crosswalk),
        quality_review_rows=quality_review_rows,
        wikidata_context_by_qid=wikidata_context_by_qid,
        discovery_pages_by_qid=discovery_pages_by_qid,
    )


# ---------------------------------------------------------------------------
# Deterministic 18/6/6 sample selection (controlling slice "Fixed
# deterministic verification sample")
# ---------------------------------------------------------------------------


class PriorTag(StrEnum):
    """The three prior SLICE-0023 quality-review tags. Sampling/calibration
    metadata only — never new-outcome evidence (controlling slice)."""

    PLAUSIBLE_MODEL_OR_CLASS_LEAD = "plausible_model_or_class_lead"
    OBVIOUS_OUT_OF_SCOPE = "obvious_out_of_scope"
    AMBIGUOUS = "ambiguous"


STRATUM_ORDER: tuple[str, ...] = (
    str(PriorTag.PLAUSIBLE_MODEL_OR_CLASS_LEAD),
    str(PriorTag.AMBIGUOUS),
    str(PriorTag.OBVIOUS_OUT_OF_SCOPE),
)
STRATUM_CAPS: dict[str, int] = {
    str(PriorTag.PLAUSIBLE_MODEL_OR_CLASS_LEAD): 18,
    str(PriorTag.AMBIGUOUS): 6,
    str(PriorTag.OBVIOUS_OUT_OF_SCOPE): 6,
}
SAMPLE_TOTAL = 30

# The 24 "threshold candidates" (prior plausible + ambiguous strata only); the
# 6 prior obvious_out_of_scope candidates are calibration/negative controls
# and never enter the yield/strong-source thresholds (controlling slice
# "Precommitted recommendation rule").
THRESHOLD_STRATA: tuple[str, ...] = (
    str(PriorTag.PLAUSIBLE_MODEL_OR_CLASS_LEAD),
    str(PriorTag.AMBIGUOUS),
)


def compute_qid_sha256(qid: str) -> str:
    """Deterministic SHA256 digest of the UTF-8 QID string, the fixed
    sampling sort key (controlling slice "Fixed deterministic verification
    sample")."""
    return hashlib.sha256(qid.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SampleSelection:
    """The deterministic, per-stratum-capped (18/6/6) verification sample.

    ``selected_by_stratum`` preserves the ascending-SHA256 selection order
    (the selection proof)."""

    selected_by_stratum: dict[str, tuple[str, ...]]
    selected_qids: tuple[str, ...]


def select_deterministic_sample(
    quality_review_rows: Sequence[dict[str, Any]],
) -> SampleSelection:
    """Select exactly 18/6/6 QIDs: within each prior-tag stratum, sort its
    members by ascending SHA256 of the UTF-8 QID string and take the first N
    up to that stratum's fixed cap. Never hand-picks, replaces or backfills
    across strata."""
    by_stratum: dict[str, list[str]] = {tag: [] for tag in STRATUM_ORDER}
    for row in quality_review_rows:
        tag = row["quality_tag"]
        if tag not in by_stratum:
            raise ValueError(f"unknown prior quality_tag {tag!r} for QID {row.get('qid')!r}")
        by_stratum[tag].append(row["qid"])

    selected_by_stratum: dict[str, tuple[str, ...]] = {}
    all_selected: list[str] = []
    for tag in STRATUM_ORDER:
        cap = STRATUM_CAPS[tag]
        ordered = sorted(by_stratum[tag], key=compute_qid_sha256)
        chosen = tuple(ordered[:cap])
        if len(chosen) != cap:
            raise ValueError(
                f"stratum {tag!r} has only {len(chosen)} candidates, fewer than the required "
                f"cap of {cap}"
            )
        selected_by_stratum[tag] = chosen
        all_selected.extend(chosen)

    if len(all_selected) != len(set(all_selected)):
        raise ValueError("deterministic sample selection produced duplicate QIDs across strata")
    if len(all_selected) != SAMPLE_TOTAL:
        raise ValueError(f"deterministic sample selection produced {len(all_selected)} != 30 QIDs")

    return SampleSelection(
        selected_by_stratum=selected_by_stratum, selected_qids=tuple(all_selected)
    )


def build_candidate_metadata(
    sample: SampleSelection, boundaries: ImmutableBoundaries
) -> list[dict[str, Any]]:
    """Build the retained per-candidate audit metadata: prior tag/rationale,
    Wikidata label/description context, and SLICE-0023 page title/category
    memberships (discovery/context only)."""
    rationale_by_qid = {row["qid"]: row["rationale"] for row in boundaries.quality_review_rows}
    tag_by_qid = {row["qid"]: row["quality_tag"] for row in boundaries.quality_review_rows}
    rows: list[dict[str, Any]] = []
    for tag in STRATUM_ORDER:
        for qid in sample.selected_by_stratum[tag]:
            wikidata = boundaries.wikidata_context_by_qid.get(qid, {})
            rows.append(
                {
                    "qid": qid,
                    "sha256": compute_qid_sha256(qid),
                    "prior_tag": tag_by_qid[qid],
                    "prior_rationale": rationale_by_qid[qid],
                    "wikidata_label": wikidata.get("label"),
                    "wikidata_description_en": wikidata.get("description_en"),
                    "sl0023_pages": boundaries.discovery_pages_by_qid.get(qid, []),
                }
            )
    return rows


# ---------------------------------------------------------------------------
# Qualifying source hierarchy + research outcome/evidence-strength vocabulary
# (controlling slice "Qualifying source hierarchy" / "Research outcome model")
# ---------------------------------------------------------------------------


class SourceClass(StrEnum):
    """The fixed qualifying-source-class vocabulary. The first seven are the
    "strong" classes; ``HIGH_QUALITY_SPECIALIST_DOCUMENTATION`` is secondary
    (qualifies only in an independent pair); everything else is
    discovery/noise and MUST NOT qualify an identity outcome."""

    MANUFACTURER_SHIPYARD = "manufacturer_shipyard"
    ORIGINAL_MANUFACTURER_BROCHURE = "original_manufacturer_brochure"
    OWNERS_TECHNICAL_MANUAL = "owners_technical_manual"
    DESIGNER_NAVAL_ARCHITECT = "designer_naval_architect"
    CLASS_ASSOCIATION = "class_association"
    OWNERS_ASSOCIATION = "owners_association"
    MUSEUM_ARCHIVE = "museum_archive"
    HIGH_QUALITY_SPECIALIST_DOCUMENTATION = "high_quality_specialist_documentation"
    NON_QUALIFYING = "non_qualifying"


STRONG_SOURCE_CLASSES: frozenset[str] = frozenset(
    {
        str(SourceClass.MANUFACTURER_SHIPYARD),
        str(SourceClass.ORIGINAL_MANUFACTURER_BROCHURE),
        str(SourceClass.OWNERS_TECHNICAL_MANUAL),
        str(SourceClass.DESIGNER_NAVAL_ARCHITECT),
        str(SourceClass.CLASS_ASSOCIATION),
        str(SourceClass.OWNERS_ASSOCIATION),
        str(SourceClass.MUSEUM_ARCHIVE),
    }
)


class SubjectOutcome(StrEnum):
    IN_SCOPE_IDENTITY = "in_scope_identity"
    OUT_OF_SCOPE = "out_of_scope"
    CONFLICT = "conflict"
    UNRESOLVED = "unresolved"


class EvidenceStrength(StrEnum):
    STRONG_SOURCE = "strong_source"
    TWO_INDEPENDENT_SPECIALIST_SOURCES = "two_independent_specialist_sources"
    INSUFFICIENT = "insufficient"


def compute_evidence_strength_from_citations(
    citations: Sequence[Mapping[str, Any]],
) -> EvidenceStrength:
    """Recompute the evidence-strength tier purely from a candidate's
    retained, *accessible*, *qualifying*, *supporting* evidence citations.

    A citation counts toward evidence strength only when all three hold:
    ``accessible`` is ``True``, ``source_class`` is not ``non_qualifying``,
    and ``supports_identity`` is ``True`` (the source's own content
    affirmatively and directly supports the candidate's final determination
    — being accessible and in a qualifying source class is not, by itself,
    evidence for a particular outcome; e.g. a manufacturer's current model
    lineup that simply omits a discontinued model neither confirms nor
    denies it).

    - >=1 such citation in a strong class -> ``STRONG_SOURCE``;
    - else >=2 such ``high_quality_specialist_documentation`` citations that
      are mutually independent (every pairwise ``independent_of``
      relationship present) -> ``TWO_INDEPENDENT_SPECIALIST_SOURCES``;
    - otherwise -> ``INSUFFICIENT``.
    """
    accessible_qualifying = [
        c
        for c in citations
        if c.get("accessible") is True
        and c.get("supports_identity") is True
        and c.get("source_class") != str(SourceClass.NON_QUALIFYING)
    ]
    if any(c.get("source_class") in STRONG_SOURCE_CLASSES for c in accessible_qualifying):
        return EvidenceStrength.STRONG_SOURCE

    specialists = [
        c
        for c in accessible_qualifying
        if c.get("source_class") == str(SourceClass.HIGH_QUALITY_SPECIALIST_DOCUMENTATION)
    ]
    if len(specialists) >= 2:
        ids = [c["citation_id"] for c in specialists]
        independent_pair_found = False
        for i, c in enumerate(specialists):
            independent_of = set(c.get("independent_of", []))
            for other_id in ids[:i] + ids[i + 1 :]:
                if other_id in independent_of:
                    independent_pair_found = True
                    break
            if independent_pair_found:
                break
        if independent_pair_found:
            return EvidenceStrength.TWO_INDEPENDENT_SPECIALIST_SOURCES

    return EvidenceStrength.INSUFFICIENT


def validate_outcome_evidence_consistency(outcome: str, evidence_strength: str) -> list[str]:
    """Validate the fixed outcome/evidence-strength consistency rules
    (controlling slice "Research outcome model")."""
    problems: list[str] = []
    if outcome == str(SubjectOutcome.IN_SCOPE_IDENTITY):
        if evidence_strength not in {
            str(EvidenceStrength.STRONG_SOURCE),
            str(EvidenceStrength.TWO_INDEPENDENT_SPECIALIST_SOURCES),
        }:
            problems.append(
                f"in_scope_identity requires strong_source or two_independent_specialist_sources, "
                f"got {evidence_strength!r}"
            )
    elif outcome in {str(SubjectOutcome.CONFLICT), str(SubjectOutcome.UNRESOLVED)}:
        if evidence_strength != str(EvidenceStrength.INSUFFICIENT):
            problems.append(
                f"{outcome} requires evidence_strength=insufficient, got {evidence_strength!r}"
            )
    elif outcome != str(SubjectOutcome.OUT_OF_SCOPE):
        problems.append(f"unknown subject_outcome {outcome!r}")
    return problems


# ---------------------------------------------------------------------------
# Research-action ceilings (controlling slice "External research boundary")
# ---------------------------------------------------------------------------

MAX_SEARCH_QUERIES_PER_CANDIDATE = 2
MAX_SOURCE_EVALUATIONS_PER_CANDIDATE = 4
MAX_COMBINED_ACTIONS_PER_CANDIDATE = 6

GLOBAL_SEARCH_QUERY_CEILING = 60
GLOBAL_SOURCE_EVALUATION_CEILING = 120
GLOBAL_COMBINED_ACTION_CEILING = 180


def validate_action_ceilings(
    *, search_query_count: int, source_page_evaluation_count: int, combined_action_count: int
) -> list[str]:
    """Validate one candidate's retained action counts against the fixed
    per-candidate ceilings and internal arithmetic consistency."""
    problems: list[str] = []
    if search_query_count > MAX_SEARCH_QUERIES_PER_CANDIDATE:
        problems.append(
            f"search_query_count={search_query_count} exceeds ceiling "
            f"{MAX_SEARCH_QUERIES_PER_CANDIDATE}"
        )
    if source_page_evaluation_count > MAX_SOURCE_EVALUATIONS_PER_CANDIDATE:
        problems.append(
            f"source_page_evaluation_count={source_page_evaluation_count} exceeds ceiling "
            f"{MAX_SOURCE_EVALUATIONS_PER_CANDIDATE}"
        )
    if combined_action_count > MAX_COMBINED_ACTIONS_PER_CANDIDATE:
        problems.append(
            f"combined_action_count={combined_action_count} exceeds ceiling "
            f"{MAX_COMBINED_ACTIONS_PER_CANDIDATE}"
        )
    if combined_action_count != search_query_count + source_page_evaluation_count:
        problems.append(
            f"combined_action_count={combined_action_count} != search_query_count"
            f"({search_query_count}) + source_page_evaluation_count({source_page_evaluation_count})"
        )
    return problems


# ---------------------------------------------------------------------------
# Metrics + precommitted recommendation rule (controlling slice "Required
# metrics" / "Precommitted recommendation rule")
# ---------------------------------------------------------------------------


class Recommendation(StrEnum):
    RIGHTS_OR_ACCESS_BLOCKED = "RIGHTS_OR_ACCESS_BLOCKED"
    LOW_INDEPENDENT_VERIFICATION_YIELD = "LOW_INDEPENDENT_VERIFICATION_YIELD"
    STRONG_SOURCE_COVERAGE_TOO_WEAK = "STRONG_SOURCE_COVERAGE_TOO_WEAK"
    TOO_EXPENSIVE_FOR_FULL_CAMPAIGN = "TOO_EXPENSIVE_FOR_FULL_CAMPAIGN"
    FULL_409_VERIFICATION_CAMPAIGN_CANDIDATE = "FULL_409_VERIFICATION_CAMPAIGN_CANDIDATE"


IN_SCOPE_MIN_INDEPENDENT_SUPPORTED = 12
IN_SCOPE_MIN_STRONG_SOURCE = 8
MAX_MEDIAN_ACTIONS_FOR_FULL_CAMPAIGN = 4


def _median(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def compute_metrics(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Mechanically recompute every required aggregate metric purely from the
    retained per-candidate results (controlling slice "Required metrics")."""
    tags = STRATUM_ORDER
    outcomes = [str(o) for o in SubjectOutcome]
    strengths = [str(e) for e in EvidenceStrength]

    sample_counts_by_tag = dict.fromkeys(tags, 0)
    outcome_counts: dict[str, int] = dict.fromkeys(outcomes, 0)
    outcome_by_tag: dict[str, dict[str, int]] = {tag: dict.fromkeys(outcomes, 0) for tag in tags}
    strength_counts: dict[str, int] = dict.fromkeys(strengths, 0)
    strength_by_tag: dict[str, dict[str, int]] = {tag: dict.fromkeys(strengths, 0) for tag in tags}
    source_class_counts: dict[str, int] = {str(c): 0 for c in SourceClass}
    access_blocked_count = 0

    search_total = 0
    eval_total = 0
    combined_total = 0
    hit_cap_count = 0
    per_candidate_actions: list[int] = []

    independently_supported_actions_24: list[int] = []
    independently_supported_count_24 = 0
    strong_source_count_24 = 0

    for row in results:
        tag = row["prior_tag"]
        outcome = row["subject_outcome"]
        strength = row["evidence_strength"]
        sample_counts_by_tag[tag] += 1
        outcome_counts[outcome] += 1
        outcome_by_tag[tag][outcome] += 1
        strength_counts[strength] += 1
        strength_by_tag[tag][strength] += 1

        for citation in row.get("evidence_citations", []):
            source_class_counts[citation["source_class"]] += 1
            if not citation.get("accessible", False):
                access_blocked_count += 1

        search_total += row["search_query_count"]
        eval_total += row["source_page_evaluation_count"]
        combined_total += row["combined_action_count"]
        per_candidate_actions.append(row["combined_action_count"])
        if row.get("hit_budget_cap"):
            hit_cap_count += 1

        is_independently_supported_in_scope = outcome == str(
            SubjectOutcome.IN_SCOPE_IDENTITY
        ) and strength in {
            str(EvidenceStrength.STRONG_SOURCE),
            str(EvidenceStrength.TWO_INDEPENDENT_SPECIALIST_SOURCES),
        }
        if tag in THRESHOLD_STRATA and is_independently_supported_in_scope:
            independently_supported_count_24 += 1
            independently_supported_actions_24.append(row["combined_action_count"])
            if strength == str(EvidenceStrength.STRONG_SOURCE):
                strong_source_count_24 += 1

    independently_supported_overall = sum(
        1
        for row in results
        if row["subject_outcome"] == str(SubjectOutcome.IN_SCOPE_IDENTITY)
        and row["evidence_strength"]
        in {
            str(EvidenceStrength.STRONG_SOURCE),
            str(EvidenceStrength.TWO_INDEPENDENT_SPECIALIST_SOURCES),
        }
    )
    strong_source_overall = sum(
        1
        for row in results
        if row["subject_outcome"] == str(SubjectOutcome.IN_SCOPE_IDENTITY)
        and row["evidence_strength"] == str(EvidenceStrength.STRONG_SOURCE)
    )
    conflicts_unresolved_count = (
        outcome_counts[str(SubjectOutcome.CONFLICT)]
        + outcome_counts[str(SubjectOutcome.UNRESOLVED)]
    )

    return {
        "sample_counts_by_prior_tag": sample_counts_by_tag,
        "subject_outcome_counts": outcome_counts,
        "subject_outcome_counts_by_prior_tag": outcome_by_tag,
        "evidence_strength_counts": strength_counts,
        "evidence_strength_counts_by_prior_tag": strength_by_tag,
        "independently_supported_in_scope_count": independently_supported_overall,
        "strong_source_in_scope_count": strong_source_overall,
        "threshold_set_independently_supported_in_scope_count": independently_supported_count_24,
        "threshold_set_strong_source_in_scope_count": strong_source_count_24,
        "source_class_counts": source_class_counts,
        "search_query_count_total": search_total,
        "source_page_evaluation_count_total": eval_total,
        "combined_research_action_count_total": combined_total,
        "per_candidate_research_action_counts": per_candidate_actions,
        "median_combined_actions_independently_supported_threshold_set": _median(
            independently_supported_actions_24
        ),
        "count_hitting_per_candidate_budget_cap": hit_cap_count,
        "access_blocked_source_page_count": access_blocked_count,
        "conflicts_and_unresolved_count": conflicts_unresolved_count,
    }


def determine_recommendation(
    *, rights_access_ok: bool, metrics: Mapping[str, Any]
) -> Recommendation:
    """Apply the precommitted, mechanical recommendation rule in order
    (controlling slice "Precommitted recommendation rule")."""
    if not rights_access_ok:
        return Recommendation.RIGHTS_OR_ACCESS_BLOCKED

    independently_supported_24 = metrics["threshold_set_independently_supported_in_scope_count"]
    if independently_supported_24 < IN_SCOPE_MIN_INDEPENDENT_SUPPORTED:
        return Recommendation.LOW_INDEPENDENT_VERIFICATION_YIELD

    strong_source_24 = metrics["threshold_set_strong_source_in_scope_count"]
    if strong_source_24 < IN_SCOPE_MIN_STRONG_SOURCE:
        return Recommendation.STRONG_SOURCE_COVERAGE_TOO_WEAK

    median_actions = metrics["median_combined_actions_independently_supported_threshold_set"]
    ceiling_exceeded = (
        metrics["search_query_count_total"] > GLOBAL_SEARCH_QUERY_CEILING
        or metrics["source_page_evaluation_count_total"] > GLOBAL_SOURCE_EVALUATION_CEILING
        or metrics["combined_research_action_count_total"] > GLOBAL_COMBINED_ACTION_CEILING
    )
    if median_actions > MAX_MEDIAN_ACTIONS_FOR_FULL_CAMPAIGN or ceiling_exceeded:
        return Recommendation.TOO_EXPENSIVE_FOR_FULL_CAMPAIGN

    return Recommendation.FULL_409_VERIFICATION_CAMPAIGN_CANDIDATE


# ---------------------------------------------------------------------------
# Retained document assembly — JSON-primitive, pure (no network/DB access)
# ---------------------------------------------------------------------------

VERIFICATION_SAMPLE_SCHEMA_VERSION = "sl0024-verification-sample-v1"
VERIFICATION_RESULTS_SCHEMA_VERSION = "sl0024-verification-results-v1"


def build_verification_sample_document(
    *,
    generated_at: str,
    boundaries: ImmutableBoundaries,
    sample: SampleSelection,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble the retained ``verification_sample.json`` document."""
    return {
        "schema_version": VERIFICATION_SAMPLE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "pinned_inputs": {
            "quality_sample_git_blob_sha1": boundaries.quality_sample_blob_sha1,
            "discovery_manifest_git_blob_sha1": boundaries.discovery_manifest_blob_sha1,
            "source_assessment_git_blob_sha1": boundaries.source_assessment_blob_sha1,
            "unique_incremental_qid_lead_count": boundaries.incremental_qid_lead_count,
            "quality_sample_total": boundaries.quality_sample_total,
            "quality_tag_counts": boundaries.quality_tag_counts,
            "canonical_boat_model_count": boundaries.canonical_boat_model_count,
            "historical_crosswalk_count": boundaries.historical_crosswalk_count,
        },
        "stratum_caps": dict(STRATUM_CAPS),
        "sample_total": SAMPLE_TOTAL,
        "selected_by_stratum_sha256_order": {
            tag: list(qids) for tag, qids in sample.selected_by_stratum.items()
        },
        "selected_qids": list(sample.selected_qids),
        "selected_count": len(sample.selected_qids),
        "candidates": candidates,
    }


def build_verification_results_document(
    *,
    generated_at: str,
    sample: SampleSelection,
    results: list[dict[str, Any]],
    rights_access_ok: bool,
    process_deviations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble the retained ``verification_results.json`` document.

    Validates that ``results`` exactly covers the selected sample (no
    missing/extra/duplicate QIDs), that every row's action ceilings and
    outcome/evidence-strength consistency hold, then mechanically computes
    metrics and the precommitted recommendation.
    """
    selected_set = frozenset(sample.selected_qids)
    result_qids = [row["qid"] for row in results]
    result_set = frozenset(result_qids)
    if len(result_qids) != len(result_set):
        dupes = sorted({q for q in result_qids if result_qids.count(q) > 1})
        raise ValueError(f"results contains duplicate QID(s): {dupes}")
    if result_set != selected_set:
        missing = selected_set - result_set
        extra = result_set - selected_set
        raise ValueError(
            f"results does not exactly cover the selected sample: missing={sorted(missing)} "
            f"extra={sorted(extra)}"
        )

    for row in results:
        problems = validate_action_ceilings(
            search_query_count=row["search_query_count"],
            source_page_evaluation_count=row["source_page_evaluation_count"],
            combined_action_count=row["combined_action_count"],
        )
        if problems:
            raise ResearchActionCeilingError(f"candidate {row['qid']}: {'; '.join(problems)}")
        recomputed_strength = compute_evidence_strength_from_citations(
            row.get("evidence_citations", [])
        )
        if str(recomputed_strength) != row["evidence_strength"]:
            raise ValueError(
                f"candidate {row['qid']}: retained evidence_strength={row['evidence_strength']!r} "
                f"!= recomputed {recomputed_strength!r} from evidence_citations"
            )
        consistency_problems = validate_outcome_evidence_consistency(
            row["subject_outcome"], row["evidence_strength"]
        )
        if consistency_problems:
            raise ValueError(f"candidate {row['qid']}: {'; '.join(consistency_problems)}")

    metrics = compute_metrics(results)
    if metrics["search_query_count_total"] > GLOBAL_SEARCH_QUERY_CEILING:
        raise ResearchActionCeilingError(
            f"global search_query_count_total={metrics['search_query_count_total']} exceeds "
            f"ceiling {GLOBAL_SEARCH_QUERY_CEILING}"
        )
    if metrics["source_page_evaluation_count_total"] > GLOBAL_SOURCE_EVALUATION_CEILING:
        raise ResearchActionCeilingError(
            "global source_page_evaluation_count_total="
            f"{metrics['source_page_evaluation_count_total']} exceeds ceiling "
            f"{GLOBAL_SOURCE_EVALUATION_CEILING}"
        )
    if metrics["combined_research_action_count_total"] > GLOBAL_COMBINED_ACTION_CEILING:
        raise ResearchActionCeilingError(
            "global combined_research_action_count_total="
            f"{metrics['combined_research_action_count_total']} exceeds ceiling "
            f"{GLOBAL_COMBINED_ACTION_CEILING}"
        )

    recommendation = determine_recommendation(rights_access_ok=rights_access_ok, metrics=metrics)

    return {
        "schema_version": VERIFICATION_RESULTS_SCHEMA_VERSION,
        "generated_at": generated_at,
        "research_boundary": {
            "max_search_queries_per_candidate": MAX_SEARCH_QUERIES_PER_CANDIDATE,
            "max_source_evaluations_per_candidate": MAX_SOURCE_EVALUATIONS_PER_CANDIDATE,
            "max_combined_actions_per_candidate": MAX_COMBINED_ACTIONS_PER_CANDIDATE,
            "global_search_query_ceiling": GLOBAL_SEARCH_QUERY_CEILING,
            "global_source_evaluation_ceiling": GLOBAL_SOURCE_EVALUATION_CEILING,
            "global_combined_action_ceiling": GLOBAL_COMBINED_ACTION_CEILING,
        },
        "rights_access_ok": rights_access_ok,
        "results": results,
        "metrics": metrics,
        "recommendation": str(recommendation),
        "process_deviations": process_deviations,
    }


# ---------------------------------------------------------------------------
# Offline self-consistency verification of already-retained documents
# ---------------------------------------------------------------------------


def verify_sample_selection_self_consistency(
    verification_sample: dict[str, Any], boundaries: ImmutableBoundaries
) -> list[str]:
    """Recompute the deterministic 18/6/6 sample fresh from the pinned
    SLICE-0023 ``quality_review`` rows and compare against a retained
    ``verification_sample.json`` document."""
    mismatches: list[str] = []
    recomputed = select_deterministic_sample(list(boundaries.quality_review_rows))

    stored_by_stratum = verification_sample.get("selected_by_stratum_sha256_order", {})
    for tag in STRATUM_ORDER:
        expected = list(recomputed.selected_by_stratum[tag])
        actual = stored_by_stratum.get(tag)
        if actual != expected:
            mismatches.append(
                f"selected_by_stratum_sha256_order[{tag!r}]={actual!r} != recomputed {expected!r}"
            )

    stored_qids = verification_sample.get("selected_qids")
    if stored_qids != list(recomputed.selected_qids):
        mismatches.append(
            f"selected_qids={stored_qids!r} != recomputed {list(recomputed.selected_qids)!r}"
        )
    if verification_sample.get("selected_count") != len(recomputed.selected_qids):
        mismatches.append(
            f"selected_count={verification_sample.get('selected_count')!r} != "
            f"{len(recomputed.selected_qids)}"
        )
    if len(set(recomputed.selected_qids)) != SAMPLE_TOTAL:
        mismatches.append("recomputed sample does not contain exactly 30 unique QIDs")

    candidates = verification_sample.get("candidates", [])
    candidate_qids = [c["qid"] for c in candidates]
    if sorted(candidate_qids) != sorted(recomputed.selected_qids):
        mismatches.append("candidates[].qid does not match the recomputed selected QID set")
    for c in candidates:
        expected_sha = compute_qid_sha256(c["qid"])
        if c.get("sha256") != expected_sha:
            mismatches.append(
                f"candidate {c['qid']}: retained sha256={c.get('sha256')!r} != recomputed "
                f"{expected_sha!r}"
            )
    return mismatches


def verify_result_row_self_consistency(row: dict[str, Any]) -> list[str]:
    """Recompute one retained result row's action-ceiling and
    outcome/evidence-strength consistency independently."""
    mismatches = list(
        validate_action_ceilings(
            search_query_count=row["search_query_count"],
            source_page_evaluation_count=row["source_page_evaluation_count"],
            combined_action_count=row["combined_action_count"],
        )
    )
    recomputed_strength = compute_evidence_strength_from_citations(
        row.get("evidence_citations", [])
    )
    if str(recomputed_strength) != row["evidence_strength"]:
        mismatches.append(
            f"evidence_strength={row['evidence_strength']!r} != recomputed "
            f"{recomputed_strength!r} from evidence_citations"
        )
    mismatches.extend(
        validate_outcome_evidence_consistency(row["subject_outcome"], row["evidence_strength"])
    )
    valid_source_classes = {str(c) for c in SourceClass}
    mismatches.extend(
        f"citation {citation.get('citation_id')!r} has invalid source_class "
        f"{citation.get('source_class')!r}"
        for citation in row.get("evidence_citations", [])
        if citation.get("source_class") not in valid_source_classes
    )
    return mismatches


def verify_metrics_self_consistency(verification_results: dict[str, Any]) -> list[str]:
    """Recompute every aggregate metric fresh from ``results`` and compare
    against the retained ``metrics`` block."""
    mismatches: list[str] = []
    results = verification_results.get("results", [])
    recomputed = compute_metrics(results)
    stored = verification_results.get("metrics", {})
    if stored != recomputed:
        mismatches.extend(
            f"metrics.{key}: stored={stored.get(key)!r} != recomputed {recomputed.get(key)!r}"
            for key in sorted(set(stored) | set(recomputed))
            if stored.get(key) != recomputed.get(key)
        )
    return mismatches


def verify_recommendation_self_consistency(verification_results: dict[str, Any]) -> list[str]:
    """Recompute the precommitted recommendation fresh from ``metrics`` and
    ``rights_access_ok`` and compare against the retained value."""
    mismatches: list[str] = []
    metrics = verification_results.get("metrics", {})
    rights_access_ok = bool(verification_results.get("rights_access_ok"))
    recomputed = determine_recommendation(rights_access_ok=rights_access_ok, metrics=metrics)
    stored = verification_results.get("recommendation")
    if stored != str(recomputed):
        mismatches.append(f"recommendation={stored!r} != recomputed {str(recomputed)!r}")
    return mismatches


def verify_artifact_digests_self_consistency(
    *, artifact_digests: dict[str, Any], package_dir: Path
) -> list[str]:
    """Recompute the SHA256 digest of every retained package file and
    compare against a retained ``ARTIFACT-DIGESTS.json`` document (``digests``
    maps filename -> ``"sha256:<hex>"``, excluding the digests file itself)."""
    mismatches: list[str] = []
    for filename, stored in artifact_digests.get("digests", {}).items():
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
