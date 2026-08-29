"""Sequential positive-control BoatDesign applicability pilot — SLICE-0032.

Implements the pure, deterministic logic described in
``docs/slices/SLICE-0032-sequential-positive-control-boatdesign-applicability-pilot.md``.

Scope is exactly the three fixed, rank-ordered SLICE-0031 positive-control
candidates (Q104861437 "Buzzards Bay 14", Q104829866 "Suspens", Q60521258
"Hunter 340") and exactly the five existing Tier-1 dimension field pointers.
Research is sequential and stop-on-first-positive: candidate *N+1* is
attempted only if candidate *N* did not reach
``READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT``.

This module performs no network acquisition. The bounded primary-source
research itself (<=12 retrievals per candidate, <=36 total) was performed
interactively and is retained as data in
``research/stage3/sl0032-positive-control-boatdesign-applicability/
source_retrieval_log.json``; the qualitative BoatDesign-generation/option
findings derived from it are retained in ``boatdesign_applicability.json``.
What this module *does* make deterministic and offline-reproducible is:

- reproducing the exact fixed rank-1..3 candidate sequence from an
  independently rebuilt SLICE-0031 candidate ranking (never trusting the
  retained SLICE-0031 ``positive_control_candidates.json`` file alone, and
  never trusting anything inside the SLICE-0032 retained package as a
  normative input for its own verification);
- reproducing the corrected/current five-field normalized technical
  candidate for each fixed QID purely from the retained SLICE-0028
  ``raw_entities`` replayed through the accepted SLICE-0030 corrected unit
  map -- zero Wikidata reacquisition;
- validating internal consistency and the fixed retrieval ceilings
  (<=12 per candidate, <=36 total) of the retained retrieval log, including
  a fixed per-candidate-rank permitted-host allowlist;
- evaluating the retained rank-1 Source record through the existing
  SLICE-0007 deterministic source-use gate
  (``hullq.sources.rights.check_source_use``) for all seven use keys, and
  mechanically deriving the ``identity_seed``/``production_value``
  clearance from the retained SR-6.6 condition evaluation itself
  (``derive_sr_6_6_use_clearance``), exactly as SLICE-0029 established;
- treating a candidate with no locatable authoritative primary source under
  the fixed source classes as rights-clearance-blocked (there is nothing to
  clear), never as a silent pass;
- validating every field-applicability classification's structured
  ``applicability_scope`` and refusing ``SAFE_FOR_LATER_DESIGN_PROMOTION``
  unless that scope is genuinely, fully bounded -- reusing the SLICE-0029
  no-absence-as-proof / no-equality-alone invariant;
- mechanically computing each candidate's result and the slice's single
  top-level result from the fixed deterministic rules, including the
  stop-on-first-positive sequencing invariant;
- building/verifying the retained-package SHA-256 artifact-integrity digest
  document.

Explicitly does NOT:
- perform any network acquisition or browse a live source;
- infer, mint or persist a canonical BoatDesign generation, DesignOption or
  NamedVariant;
- create or mutate a canonical BoatModel/crosswalk row;
- create a FieldResolution or choose a canonical technical value;
- weaken or bypass ``hullq.sources.rights.check_source_use``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from hullq.sources.rights import DecisionOutcome, SourceUse, check_source_use

__all__ = [
    "ALLOWED_FIELD_POINTERS",
    "ALLOWED_RETRIEVAL_HOSTS_BY_RANK",
    "ALLOWED_SOURCE_SURFACE_CLASSES",
    "ARTIFACT_DIGESTS_FILENAME",
    "ARTIFACT_DIGESTS_SCHEMA_VERSION",
    "BOUNDED_ONLY_PERMISSION_KEYS",
    "FIXED_CANDIDATE_SEQUENCE",
    "MAX_CANDIDATES",
    "MAX_RETRIEVALS_PER_CANDIDATE",
    "MAX_TOTAL_RETRIEVALS",
    "SL0032_ACTIVITY_ID",
    "SOURCE_CLEARANCE_RESULT_VALUES",
    "SOURCE_CLEARANCE_RIGHTS_BLOCKED",
    "SOURCE_CLEARANCE_USE_CLEARED",
    "SR_6_6_DEFAULT_CLEARANCE",
    "SR_6_6_GATED_USES",
    "SR_6_6_SATISFIED_CLEARANCE",
    "AttemptStatus",
    "CandidateOutcome",
    "CandidateSequenceEntry",
    "FieldApplicabilityOutcome",
    "FixedCandidate",
    "RetrievalLogIntegrityError",
    "SequenceIntegrityError",
    "TopLevelResult",
    "build_artifact_digests",
    "build_pilot_candidates_document",
    "compute_candidate_result",
    "compute_top_level_result",
    "derive_sr_6_6_use_clearance",
    "evaluate_source_use_gate",
    "retained_package_filenames",
    "retrieval_host",
    "sr_6_6_conditions_satisfied",
    "validate_applicability_scope_invariant",
    "validate_boatdesign_applicability",
    "validate_bounded_scope",
    "validate_field_applicability",
    "validate_permissions_bounded",
    "validate_sequential_stop_invariant",
    "validate_source_retrieval_log",
    "validate_stop_on_first_positive_retrievals",
    "verify_artifact_digests_self_consistency",
    "verify_fixed_candidate_sequence",
    "verify_result_self_consistency",
    "verify_source_clearance_assessment_self_consistency",
]

SL0032_ACTIVITY_ID = "SLICE-0032-SEQUENTIAL-POSITIVE-CONTROL-BOATDESIGN-APPLICABILITY-PILOT"


@dataclass(frozen=True)
class FixedCandidate:
    """One entry of the normative, non-tamperable pilot candidate sequence."""

    rank: int
    qid: str
    hullq_id: str
    label: str


# The exact, fixed SLICE-0031 rank-1..3 pilot sequence (controlling slice
# "Fixed candidate identity boundary"). This is a normative code constant --
# never read from a mutable/tamperable retained artifact at runtime.
FIXED_CANDIDATE_SEQUENCE: tuple[FixedCandidate, ...] = (
    FixedCandidate(
        rank=1,
        qid="Q104861437",
        hullq_id="BM_WDT0_003ba28d4cd143d68c28e57899a3ed73",
        label="Buzzards Bay 14",
    ),
    FixedCandidate(
        rank=2,
        qid="Q104829866",
        hullq_id="BM_WDT0_0040159e704c49d0a0b7bc7c6224ecfb",
        label="Suspens",
    ),
    FixedCandidate(
        rank=3,
        qid="Q60521258",
        hullq_id="BM_WDT0_00f6a6f678474a14ab5ec1b078cf6d60",
        label="Hunter 340",
    ),
)

MAX_CANDIDATES = 3
MAX_RETRIEVALS_PER_CANDIDATE = 12
MAX_TOTAL_RETRIEVALS = 36

ALLOWED_FIELD_POINTERS: frozenset[str] = frozenset(
    {
        "/baseline/dimensions/loa_m",
        "/baseline/dimensions/lwl_m",
        "/baseline/dimensions/beam_m",
        "/baseline/dimensions/draft_min_m",
        "/baseline/dimensions/displacement_kg",
    }
)

# Fixed per-candidate-rank permitted retrieval-host allowlist, matching
# exactly the bounded manual research actually performed for this pilot. A
# tampered retrieval log cannot introduce a host outside this fixed set for
# a given candidate rank.
ALLOWED_RETRIEVAL_HOSTS_BY_RANK: Mapping[int, frozenset[str]] = {
    1: frozenset({"www.buzzardsbayboatshop.com", "www.capecodshipbuilding.com"}),
    2: frozenset({"www.joubertnivelt-design.com", "www.bgrace.fr"}),
    3: frozenset({"www.marlow-hunter.com"}),
}

# Fixed permitted source-surface-class vocabulary (controlling slice "Fixed
# external-source boundary" permitted surface types), enforced here
# independently of JSON Schema so a retained document that skips/bypasses
# schema validation still cannot introduce a search-result-snippet or other
# out-of-contract surface class as positive evidence.
ALLOWED_SOURCE_SURFACE_CLASSES: frozenset[str] = frozenset(
    {
        "official_model_specification_page",
        "official_brochure_archive_index",
        "official_model_brochure_or_specification_document",
        "official_history_or_current_model_page",
        "official_current_model_and_navigation_page",
        "official_class_rules_or_specifications",
        "official_terms_privacy_copyright_page",
        "access_or_automation_policy",
    }
)

# SR-6.6 (specs/SOURCE_RIGHTS_POLICY.v0.1.md#6.6) baseline is 'conditional'
# production clearance for an unlicensed primary factual source. This
# mapping is the single source of truth for the scoped promotion to
# 'allowed'; nothing else in this module or the retained package may assert
# 'allowed' for these two uses independently of it (reused unchanged from
# the accepted SLICE-0029 pattern).
SR_6_6_SATISFIED_CLEARANCE = "allowed"
SR_6_6_DEFAULT_CLEARANCE = "conditional"
SR_6_6_GATED_USES: tuple[str, str] = (
    SourceUse.IDENTITY_SEED.value,
    SourceUse.PRODUCTION_VALUE.value,
)

BOUNDED_ONLY_PERMISSION_KEYS: tuple[str, str, str] = (
    "commercial_use",
    "store_canonical_values",
    "publish_derived_database",
)


class FieldApplicabilityOutcome(StrEnum):
    """Fail-closed field-level applicability vocabulary (controlling slice)."""

    SAFE_FOR_LATER_DESIGN_PROMOTION = "SAFE_FOR_LATER_DESIGN_PROMOTION"
    MODEL_SCOPE_ONLY_NOT_PROMOTABLE = "MODEL_SCOPE_ONLY_NOT_PROMOTABLE"
    GENERATION_AMBIGUOUS = "GENERATION_AMBIGUOUS"
    OPTION_SENSITIVE = "OPTION_SENSITIVE"
    SOURCE_VALUE_CONFLICT = "SOURCE_VALUE_CONFLICT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NO_NORMALIZED_WIKIDATA_CANDIDATE = "NO_NORMALIZED_WIKIDATA_CANDIDATE"
    RIGHTS_BLOCKED = "RIGHTS_BLOCKED"


class CandidateOutcome(StrEnum):
    """The exact three normative per-candidate result values the controlling
    slice defines for an ATTEMPTED candidate. Deliberately contains NOTHING
    else: attempt/non-attempt status is a wholly separate concept
    (:class:`AttemptStatus`), never a fourth member of this enum -- a
    candidate that was never researched has no result at all, not a
    result meaning "not attempted"."""

    READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT = "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT"
    RIGHTS_CLEARANCE_BLOCKED = "RIGHTS_CLEARANCE_BLOCKED"
    APPLICABILITY_EVIDENCE_INSUFFICIENT = "APPLICABILITY_EVIDENCE_INSUFFICIENT"


class AttemptStatus(StrEnum):
    """Whether a fixed-rank candidate was actually researched.

    Kept entirely separate from :class:`CandidateOutcome`: a
    ``NOT_ATTEMPTED_AFTER_SUCCESS`` candidate carries no
    :class:`CandidateOutcome` value at all (``None``), zero retrievals, and
    no rights/applicability/technical evidence in any retained document --
    it is not a fourth "result".
    """

    ATTEMPTED = "ATTEMPTED"
    NOT_ATTEMPTED_AFTER_SUCCESS = "NOT_ATTEMPTED_AFTER_SUCCESS"


# One fixed rank's position in the sequential stop-on-first-positive
# ordering: (rank, attempt_status, result). ``result`` MUST be a
# ``CandidateOutcome`` when ``attempt_status`` is ``ATTEMPTED`` and MUST be
# ``None`` when ``attempt_status`` is ``NOT_ATTEMPTED_AFTER_SUCCESS`` --
# enforced by ``validate_sequential_stop_invariant``, never assumed.
CandidateSequenceEntry = tuple[int, AttemptStatus, "CandidateOutcome | None"]


class TopLevelResult(StrEnum):
    """The slice's single deterministic top-level result vocabulary."""

    READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT = "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT"
    RIGHTS_CLEARANCE_BLOCKED = "RIGHTS_CLEARANCE_BLOCKED"
    APPLICABILITY_EVIDENCE_INSUFFICIENT = "APPLICABILITY_EVIDENCE_INSUFFICIENT"


# Vocabulary for source_clearance_assessment.json's per-candidate
# candidate_source_clearance_result field. This is intentionally a SEPARATE
# vocabulary from CandidateOutcome (never reuses/aliases it): a source-
# clearance outcome is not itself one of the three normative candidate
# results. A rank that was never researched carries NO row at all in
# field_applicability.json / boatdesign_applicability.json /
# source_clearance_assessment.json (see verify_result_self_consistency) --
# so this vocabulary has exactly two values, both meaning research was
# genuinely attempted for that candidate.
SOURCE_CLEARANCE_USE_CLEARED = "SOURCE_USE_CLEARED_FOR_APPLICABILITY_RESEARCH"
SOURCE_CLEARANCE_RIGHTS_BLOCKED = "RIGHTS_CLEARANCE_BLOCKED"
SOURCE_CLEARANCE_RESULT_VALUES: frozenset[str] = frozenset(
    {SOURCE_CLEARANCE_USE_CLEARED, SOURCE_CLEARANCE_RIGHTS_BLOCKED}
)


class SequenceIntegrityError(Exception):
    """Raised when the reproduced candidate sequence drifts from the accepted
    SLICE-0031 ranking or the fixed SLICE-0032 candidate constant."""


class RetrievalLogIntegrityError(Exception):
    """Raised when the retained retrieval log violates the bounded-research contract."""


# ---------------------------------------------------------------------------
# 1. Fixed candidate sequence reproduction
# ---------------------------------------------------------------------------


def verify_fixed_candidate_sequence(
    ranked_eligible_candidates: Sequence[Any],
) -> list[str]:
    """Independently verify that the fixed SLICE-0032 candidate sequence is
    exactly ranks 1..3 of *ranked_eligible_candidates* -- the freshly,
    independently recomputed SLICE-0031 eligible+ranked candidate pool
    (``hullq.bootstrap.wikidata_sl0031_corrected_tier1_evidence_profile
    .select_positive_control_candidates`` applied to a freshly rebuilt
    evidence profile), never the retained SLICE-0031
    ``positive_control_candidates.json`` file taken on trust and never
    anything inside the SLICE-0032 retained package.

    *ranked_eligible_candidates* entries must expose ``.hullq_id`` and
    ``.qids`` attributes (as
    ``wikidata_sl0031_corrected_tier1_evidence_profile.PositiveControlCandidate``
    does).
    """
    problems: list[str] = []
    top_three = list(ranked_eligible_candidates[: len(FIXED_CANDIDATE_SEQUENCE)])
    if len(top_three) < len(FIXED_CANDIDATE_SEQUENCE):
        return [
            f"independently recomputed SLICE-0031 candidate pool has only {len(top_three)} "
            f"entries, fewer than the {len(FIXED_CANDIDATE_SEQUENCE)} fixed pilot ranks"
        ]
    for fixed, actual in zip(FIXED_CANDIDATE_SEQUENCE, top_three, strict=True):
        if actual.hullq_id != fixed.hullq_id:
            problems.append(
                f"rank {fixed.rank}: independently recomputed hullq_id {actual.hullq_id!r} != "
                f"fixed {fixed.hullq_id!r}"
            )
        if fixed.qid not in tuple(actual.qids):
            problems.append(
                f"rank {fixed.rank}: independently recomputed qids {tuple(actual.qids)!r} does "
                f"not contain fixed qid {fixed.qid!r}"
            )
    return problems


PILOT_CANDIDATES_SCHEMA_VERSION = "sl0032-pilot-candidates-v1"


def build_pilot_candidates_document(*, generated_at: str) -> dict[str, Any]:
    """Assemble the retained ``pilot_candidates.json`` document: the fixed,
    normative rank-1..3 candidate constants and the eligibility/ranking rule
    they were selected under (unchanged from the accepted SLICE-0031
    contract). Contains no reproduction-result booleans of its own -- those
    live in the runner's verification log, never inside this retained
    artifact (a tampered artifact must never be able to assert its own
    correctness)."""
    return {
        "schema_version": PILOT_CANDIDATES_SCHEMA_VERSION,
        "generated_at": generated_at,
        "source_pool": "research/stage3/sl0031-corrected-tier1-evidence-profile/positive_control_candidates.json",
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
        "sequential_rule": (
            "assess rank 1; only if rank 1 does not satisfy the fixed positive-control success "
            "rule, assess rank 2; only if ranks 1 and 2 do not satisfy it, assess rank 3; stop "
            "immediately once one candidate satisfies the positive-control success rule"
        ),
        "max_candidates": MAX_CANDIDATES,
        "max_retrievals_per_candidate": MAX_RETRIEVALS_PER_CANDIDATE,
        "max_total_retrievals": MAX_TOTAL_RETRIEVALS,
        "allowed_field_pointers": sorted(ALLOWED_FIELD_POINTERS),
        "candidates": [
            {
                "rank": c.rank,
                "qid": c.qid,
                "hullq_id": c.hullq_id,
                "label": c.label,
            }
            for c in FIXED_CANDIDATE_SEQUENCE
        ],
    }


# ---------------------------------------------------------------------------
# 2. Bounded retrieval log
# ---------------------------------------------------------------------------


def retrieval_host(url: str) -> str | None:
    """Extract the host component of an ``https://`` URL, or ``None`` if the
    URL is not a well-formed ``https://host/...`` string."""
    if not url.startswith("https://") or url.count("/") < 2:
        return None
    return url.split("/")[2]


def validate_source_retrieval_log(document: Mapping[str, Any]) -> list[str]:
    """Validate internal consistency and the fixed ceilings (<=12 per
    candidate, <=36 total) of the retained retrieval log, independently of
    any ceiling value the document itself might claim."""
    problems: list[str] = []
    retrievals = document.get("retrievals", [])
    declared_count = document.get("retrieval_count")
    if declared_count != len(retrievals):
        problems.append(f"retrieval_count={declared_count!r} != len(retrievals)={len(retrievals)}")
    if len(retrievals) > MAX_TOTAL_RETRIEVALS:
        problems.append(
            f"len(retrievals)={len(retrievals)} exceeds fixed MAX_TOTAL_RETRIEVALS="
            f"{MAX_TOTAL_RETRIEVALS}"
        )

    seen_indices: set[int] = set()
    per_rank_counts: dict[int, int] = {}
    for entry in retrievals:
        index = entry.get("retrieval_index")
        if not isinstance(index, int) or index in seen_indices:
            problems.append(f"duplicate or non-integer retrieval_index: {index!r}")
        if isinstance(index, int):
            seen_indices.add(index)

        rank = entry.get("candidate_rank")
        if rank not in (1, 2, 3):
            problems.append(f"retrieval {index!r}: candidate_rank {rank!r} is not 1, 2 or 3")
        else:
            per_rank_counts[rank] = per_rank_counts.get(rank, 0) + 1

        url = entry.get("url", "")
        host = retrieval_host(url)
        allowed_hosts = ALLOWED_RETRIEVAL_HOSTS_BY_RANK.get(rank, frozenset())
        if host not in allowed_hosts:
            problems.append(
                f"retrieval {index!r} (rank {rank!r}) host {host!r} not in the fixed permitted "
                f"host set for that rank {sorted(allowed_hosts)!r}"
            )

        surface_class = entry.get("source_surface_class")
        if surface_class not in ALLOWED_SOURCE_SURFACE_CLASSES:
            problems.append(
                f"retrieval {index!r}: source_surface_class {surface_class!r} not in the fixed "
                f"permitted surface-class vocabulary {sorted(ALLOWED_SOURCE_SURFACE_CLASSES)!r} "
                "(search-result snippets and other ad-hoc surfaces are never positive evidence)"
            )

        outcome = entry.get("retrieval_outcome")
        if outcome not in ("fetched", "dns_resolution_failed"):
            problems.append(f"retrieval {index!r}: unrecognized retrieval_outcome {outcome!r}")
        if outcome == "fetched":
            sha256 = entry.get("sha256", "")
            if not (
                isinstance(sha256, str)
                and len(sha256) == 64
                and all(c in "0123456789abcdef" for c in sha256)
            ):
                problems.append(
                    f"retrieval {index!r}: sha256 {sha256!r} is not a valid lowercase hex digest"
                )
            if not isinstance(entry.get("http_status"), int):
                problems.append(
                    f"retrieval {index!r}: fetched outcome requires an integer http_status"
                )
        elif entry.get("sha256") is not None or entry.get("http_status") is not None:
            problems.append(
                f"retrieval {index!r}: {outcome!r} outcome must not carry an sha256/http_status"
            )

    for rank, count in per_rank_counts.items():
        if count > MAX_RETRIEVALS_PER_CANDIDATE:
            problems.append(
                f"candidate rank {rank}: {count} retrievals exceeds fixed "
                f"MAX_RETRIEVALS_PER_CANDIDATE={MAX_RETRIEVALS_PER_CANDIDATE}"
            )

    if seen_indices and seen_indices != set(range(1, len(retrievals) + 1)):
        problems.append(
            f"retrieval_index set {sorted(seen_indices)!r} is not exactly 1..{len(retrievals)}"
        )

    return problems


def validate_stop_on_first_positive_retrievals(
    document: Mapping[str, Any],
    *,
    not_attempted_ranks: frozenset[int],
) -> list[str]:
    """Validate that zero retrievals exist in the retrieval log for any rank
    in *not_attempted_ranks* (mechanically auditable stop-on-first-positive:
    a candidate correctly skipped after an earlier rank reached READY must
    show literally zero retrieval activity, not merely a suppressed
    result)."""
    if not not_attempted_ranks:
        return []
    problems: list[str] = []
    for entry in document.get("retrievals", []):
        rank = entry.get("candidate_rank")
        if rank in not_attempted_ranks:
            problems.append(
                f"retrieval {entry.get('retrieval_index')!r} targets rank {rank}, which is in "
                f"the independently-derived not-attempted-rank set {sorted(not_attempted_ranks)!r} "
                "-- stop-on-first-positive was violated"
            )
    return problems


# ---------------------------------------------------------------------------
# 3. Source-rights gate evaluation (rank 1 only has a located source here;
#    reuses hullq.sources.rights unchanged)
# ---------------------------------------------------------------------------


def evaluate_source_use_gate(source_record: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """Evaluate a retained Source record through the unmodified SLICE-0007
    gate for all seven use keys."""
    results: dict[str, dict[str, str]] = {}
    for use in SourceUse:
        decision = check_source_use(dict(source_record), use)
        results[use.value] = {"outcome": decision.outcome.value}
    return results


def sr_6_6_conditions_satisfied(conditions: Any) -> bool:
    """True only if every retained SR-6.6 condition is positively satisfied
    (``True`` or the one explicitly-allowed partial state)."""
    return all(c["satisfied"] in (True, "partial_left_unresolved") for c in conditions)


def derive_sr_6_6_use_clearance(conditions: Any) -> str:
    """Mechanically derive the ``identity_seed``/``production_value`` clearance
    value from the retained SR-6.6 condition evaluation -- the same
    computation, never two independently-asserted facts that could drift
    apart (reused unchanged from the accepted SLICE-0029 pattern)."""
    return (
        SR_6_6_SATISFIED_CLEARANCE
        if sr_6_6_conditions_satisfied(conditions)
        else SR_6_6_DEFAULT_CLEARANCE
    )


def validate_permissions_bounded(source_record: Mapping[str, Any]) -> list[str]:
    """The broader SOURCE_SCHEMA permissions that would authorize *unscoped*
    reuse MUST NOT read 'allowed'."""
    permissions = source_record["rights"]["permissions"]
    return [
        f"permissions.{key} == 'allowed' would remove the SLICE-0032 bounded-scope "
        "constraint on the scoped identity_seed/production_value clearance"
        for key in BOUNDED_ONLY_PERMISSION_KEYS
        if permissions.get(key) == "allowed"
    ]


def validate_bounded_scope(
    entry: Mapping[str, Any], *, fixed_candidate: FixedCandidate
) -> list[str]:
    """Validate that one candidate's clearance ``bounded_scope`` covers
    exactly that fixed candidate's hullq_id/qid and the five fixed field
    pointers, for the identity_seed/production_value use kinds only."""
    problems: list[str] = []
    scope = entry.get("bounded_scope", {})
    if scope.get("hullq_ids") != [fixed_candidate.hullq_id]:
        problems.append(
            f"bounded_scope.hullq_ids {scope.get('hullq_ids')!r} != [{fixed_candidate.hullq_id!r}]"
        )
    if scope.get("qids") != [fixed_candidate.qid]:
        problems.append(f"bounded_scope.qids {scope.get('qids')!r} != [{fixed_candidate.qid!r}]")
    if set(scope.get("field_pointers", [])) != ALLOWED_FIELD_POINTERS:
        problems.append(
            f"bounded_scope.field_pointers {sorted(scope.get('field_pointers', []))!r} != "
            f"the five fixed Tier-1 pointers {sorted(ALLOWED_FIELD_POINTERS)!r}"
        )
    if set(scope.get("use_kinds", [])) != set(SR_6_6_GATED_USES):
        problems.append(
            f"bounded_scope.use_kinds {sorted(scope.get('use_kinds', []))!r} != "
            f"{sorted(SR_6_6_GATED_USES)!r}"
        )
    return problems


def verify_source_clearance_assessment_self_consistency(
    document: Mapping[str, Any],
    *,
    attempted_ranks: frozenset[int],
) -> list[str]:
    """Recompute every candidate's clearance decision from its retained
    evidence and compare against the retained document.

    *attempted_ranks* is the independently-derived set of ranks that were
    genuinely researched (never inferred from this document itself): the
    retained document's rank coverage must equal it exactly. A rank that was
    never attempted (a later candidate correctly skipped after an earlier
    rank reached READY) MUST NOT appear here at all -- there is no
    "not attempted" clearance result, only genuine research outcomes.

    For a candidate with a located source record, the source-use gate
    decisions and the SR-6.6-derived identity_seed/production_value
    clearance are recomputed exactly as SLICE-0029 established. For an
    attempted candidate with no located authoritative primary source
    (``source_located: false``), the only valid ``candidate_source_clearance_result``
    is ``RIGHTS_CLEARANCE_BLOCKED`` -- there is nothing to clear.
    """
    mismatches: list[str] = []
    fixed_by_rank = {c.rank: c for c in FIXED_CANDIDATE_SEQUENCE}
    found_ranks: set[int] = set()

    for entry in document.get("candidates", []):
        rank = entry.get("candidate_rank")
        found_ranks.add(rank)
        fixed_candidate = fixed_by_rank.get(rank)
        if fixed_candidate is None:
            mismatches.append(f"source_clearance_assessment: unrecognized candidate_rank {rank!r}")
            continue

        if entry.get("source_located") is False:
            if entry.get("candidate_source_clearance_result") != SOURCE_CLEARANCE_RIGHTS_BLOCKED:
                mismatches.append(
                    f"rank {rank}: source_located=false but "
                    f"candidate_source_clearance_result={entry.get('candidate_source_clearance_result')!r} "
                    f"!= {SOURCE_CLEARANCE_RIGHTS_BLOCKED!r}"
                )
            continue

        source_record = entry["source_record"]
        clearance = source_record["rights"]["clearance"]
        conditions = entry["sr_6_6_condition_evaluation"]["conditions"]
        all_satisfied = sr_6_6_conditions_satisfied(conditions)
        retained_flag = entry["sr_6_6_condition_evaluation"][
            "conditions_satisfied_for_bounded_manual_use"
        ]
        if retained_flag != all_satisfied:
            mismatches.append(
                f"rank {rank}: conditions_satisfied_for_bounded_manual_use retained="
                f"{retained_flag!r} recomputed={all_satisfied!r}"
            )

        expected_use_clearance = derive_sr_6_6_use_clearance(conditions)
        for use in SR_6_6_GATED_USES:
            actual = clearance.get(use)
            if actual != expected_use_clearance:
                mismatches.append(
                    f"rank {rank}: source_record.rights.clearance.{use}={actual!r} is not "
                    f"mechanically derived from sr_6_6_condition_evaluation (expected "
                    f"{expected_use_clearance!r})"
                )

        mismatches.extend(f"rank {rank}: {p}" for p in validate_permissions_bounded(source_record))
        mismatches.extend(
            f"rank {rank}: {p}"
            for p in validate_bounded_scope(entry, fixed_candidate=fixed_candidate)
        )

        recomputed_gate = evaluate_source_use_gate(source_record)
        retained_gate = entry["source_use_gate_decisions"]["decisions"]
        if recomputed_gate != retained_gate:
            mismatches.append(f"rank {rank}: source_use_gate_decisions mismatch")

        source_cleared = source_use_allowed(
            retained_gate, SourceUse.IDENTITY_SEED.value
        ) and source_use_allowed(retained_gate, SourceUse.PRODUCTION_VALUE.value)
        expected_clearance_result = (
            SOURCE_CLEARANCE_USE_CLEARED if source_cleared else SOURCE_CLEARANCE_RIGHTS_BLOCKED
        )
        if entry.get("candidate_source_clearance_result") != expected_clearance_result:
            mismatches.append(
                f"rank {rank}: candidate_source_clearance_result="
                f"{entry.get('candidate_source_clearance_result')!r} != mechanically derived "
                f"{expected_clearance_result!r}"
            )

    if found_ranks != attempted_ranks:
        mismatches.append(
            f"source_clearance_assessment rank set {sorted(found_ranks)!r} != independently "
            f"derived attempted-rank set {sorted(attempted_ranks)!r} -- an unattempted rank must "
            "carry no clearance row at all, and every attempted rank must carry exactly one"
        )

    return mismatches


def source_use_allowed(gate_decisions: Mapping[str, Any], use: str) -> bool:
    """True only if the given use key's gate outcome is exactly 'allowed'."""
    entry = gate_decisions.get(use, {})
    return bool(entry.get("outcome") == DecisionOutcome.ALLOWED.value)


def candidate_source_cleared(clearance_entry: Mapping[str, Any]) -> bool:
    """True iff a per-candidate source_clearance_assessment entry cleared
    identity_seed/production_value for applicability research."""
    return clearance_entry.get("candidate_source_clearance_result") == SOURCE_CLEARANCE_USE_CLEARED


# ---------------------------------------------------------------------------
# 4. Applicability-scope / no-absence-as-proof invariant (SLICE-0029 reuse)
# ---------------------------------------------------------------------------

_APPLICABILITY_SCOPE_DIMENSION_KEYS: tuple[str, ...] = (
    "first_year",
    "last_year",
    "hull_number_from",
    "hull_number_to",
    "market_or_region",
    "named_variant_hint",
    "design_option_hints",
    "operating_state_hint",
    "individual_hull_or_listing_ref",
)
_NON_YEAR_APPLICABILITY_SCOPE_DIMENSION_KEYS: tuple[str, ...] = tuple(
    key for key in _APPLICABILITY_SCOPE_DIMENSION_KEYS if key not in ("first_year", "last_year")
)


def validate_applicability_scope_invariant(scope: Mapping[str, Any]) -> list[str]:
    """Validate the OBSERVATION_APPLICABILITY_SCHEMA.v0.1 no-absence-as-proof
    invariant: a half-open year range (only one of first_year/last_year
    known) can never be claimed bounded, and an all-null scope can never be
    claimed bounded either (reused unchanged from the accepted SLICE-0029
    pattern -- see that module's docstring for full rationale)."""
    if scope.get("unknown_or_unbounded") is True:
        return []

    first_year = scope.get("first_year")
    last_year = scope.get("last_year")

    if first_year is not None and last_year is not None:
        return []

    if first_year is not None or last_year is not None:
        return [
            "applicability_scope claims unknown_or_unbounded=false using a production-year "
            "range but only one of first_year/last_year is known"
        ]

    if any(scope.get(key) is not None for key in _NON_YEAR_APPLICABILITY_SCOPE_DIMENSION_KEYS):
        return []

    return [
        "applicability_scope claims unknown_or_unbounded=false but every bounding "
        "dimension is null -- an empty scope cannot be treated as genuinely bounded"
    ]


# ---------------------------------------------------------------------------
# 5. BoatDesign applicability + field-applicability structural validation
# ---------------------------------------------------------------------------


def validate_boatdesign_applicability(
    document: Mapping[str, Any], *, attempted_ranks: frozenset[int]
) -> list[str]:
    """Validate structural invariants of the retained BoatDesign applicability
    findings for every attempted candidate.

    *attempted_ranks* is the independently-derived set of genuinely
    researched ranks. A rank that was never attempted MUST carry no row
    here at all -- this document is never a place to assert generation/
    applicability findings for research that did not happen.
    """
    problems: list[str] = []
    found_ranks: set[int] = set()
    for model in document.get("candidates", []):
        rank = model.get("candidate_rank")
        found_ranks.add(rank)
        established = model.get("generation_boundary_established_for_this_pilot")
        if not isinstance(established, bool):
            problems.append(
                f"rank {rank}: generation_boundary_established_for_this_pilot is not a bool"
            )

        scope = model.get("applicability_scope")
        if scope is None:
            problems.append(f"rank {rank}: missing applicability_scope")
            continue
        problems.extend(f"rank {rank}: {p}" for p in validate_applicability_scope_invariant(scope))
        if established is True and scope.get("unknown_or_unbounded") is not False:
            problems.append(
                f"rank {rank}: generation_boundary_established_for_this_pilot=True but "
                "applicability_scope.unknown_or_unbounded != false"
            )
        if established is False and scope.get("unknown_or_unbounded") is not True:
            problems.append(
                f"rank {rank}: generation_boundary_established_for_this_pilot=False but "
                "applicability_scope.unknown_or_unbounded != true"
            )

    if found_ranks != attempted_ranks:
        problems.append(
            f"boatdesign_applicability rank set {sorted(found_ranks)!r} != {sorted(attempted_ranks)!r}"
        )
    return problems


def validate_field_applicability(
    document: Mapping[str, Any],
    *,
    corrected_candidate_evidence: Mapping[str, Any],
    attempted_ranks: frozenset[int],
) -> list[str]:
    """Validate the five-field applicability vocabulary/coverage invariants
    for every attempted candidate and cross-check every cited normalized
    candidate against the reused, independently-derived
    ``corrected_candidate_evidence.json`` (never reacquired/reinterpreted).

    *attempted_ranks* is the independently-derived set of genuinely
    researched ranks. A rank that was never attempted MUST carry no row
    here at all -- five-field classification is never asserted for research
    that did not happen.
    """
    problems: list[str] = []
    valid_outcomes = {o.value for o in FieldApplicabilityOutcome}

    evidence_by_rank: dict[int, dict[str, Any]] = {
        row["candidate_rank"]: row for row in corrected_candidate_evidence.get("candidates", [])
    }

    found_ranks: set[int] = set()
    for model in document.get("candidates", []):
        rank = model.get("candidate_rank")
        found_ranks.add(rank)
        seen_pointers: set[str] = set()
        evidence_row = evidence_by_rank.get(rank)
        fields_by_pointer = (
            {f["field_pointer"]: f for f in evidence_row["fields"]} if evidence_row else {}
        )

        for field in model.get("fields", []):
            pointer = field["field_pointer"]
            seen_pointers.add(pointer)
            if pointer not in ALLOWED_FIELD_POINTERS:
                problems.append(f"rank {rank}: unexpected field pointer {pointer!r}")
            if field["outcome"] not in valid_outcomes:
                problems.append(
                    f"rank {rank} field {pointer}: invalid outcome {field['outcome']!r}"
                )

            candidate_value = field.get("wikidata_normalized_candidate")
            if (
                candidate_value is None
                and field["outcome"]
                != FieldApplicabilityOutcome.NO_NORMALIZED_WIKIDATA_CANDIDATE.value
                and field["outcome"] != FieldApplicabilityOutcome.RIGHTS_BLOCKED.value
            ):
                problems.append(
                    f"rank {rank} field {pointer}: candidate is null but outcome "
                    f"{field['outcome']!r} requires a normalized candidate value"
                )
            evidence_field = fields_by_pointer.get(pointer)
            if evidence_field is not None and candidate_value is not None:
                expected = evidence_field.get("normalized_candidate")
                if expected != candidate_value:
                    problems.append(
                        f"rank {rank} field {pointer}: wikidata_normalized_candidate "
                        f"{candidate_value!r} != reused corrected_candidate_evidence "
                        f"{expected!r}"
                    )

            scope = field.get("applicability_scope")
            if scope is None:
                problems.append(f"rank {rank} field {pointer}: missing applicability_scope")
            else:
                problems.extend(
                    f"rank {rank} field {pointer}: {p}"
                    for p in validate_applicability_scope_invariant(scope)
                )
                is_safe = (
                    field["outcome"]
                    == FieldApplicabilityOutcome.SAFE_FOR_LATER_DESIGN_PROMOTION.value
                )
                if is_safe and scope.get("unknown_or_unbounded") is not False:
                    problems.append(
                        f"rank {rank} field {pointer}: outcome=SAFE_FOR_LATER_DESIGN_PROMOTION requires "
                        "applicability_scope.unknown_or_unbounded == false"
                    )

        if seen_pointers != ALLOWED_FIELD_POINTERS:
            problems.append(
                f"rank {rank}: field pointer coverage {sorted(seen_pointers)!r} != the five fixed pointers"
            )

    if found_ranks != attempted_ranks:
        problems.append(
            f"field_applicability rank set {sorted(found_ranks)!r} != {sorted(attempted_ranks)!r}"
        )
    return problems


# ---------------------------------------------------------------------------
# 6. Candidate-level and top-level deterministic result derivation
# ---------------------------------------------------------------------------


def compute_candidate_result(
    *,
    source_cleared: bool,
    generation_boundary_established: bool,
    field_outcomes: Sequence[Mapping[str, Any]],
) -> CandidateOutcome:
    """Mechanically compute one candidate's result from its rights-clearance
    state, its BoatDesign generation/configuration boundary state, and its
    five field-applicability classifications.

    READY requires ALL of: source use cleared, a genuinely bounded
    generation/configuration scope, and at least one field classified
    SAFE_FOR_LATER_DESIGN_PROMOTION with a genuinely bounded
    (``unknown_or_unbounded is False``) scope on that same field -- equality
    alone or an unbounded/half-open scope can never satisfy this (defense in
    depth alongside ``validate_field_applicability`` /
    ``validate_boatdesign_applicability``).
    """
    if not source_cleared:
        return CandidateOutcome.RIGHTS_CLEARANCE_BLOCKED

    has_safe_field = any(
        field["outcome"] == FieldApplicabilityOutcome.SAFE_FOR_LATER_DESIGN_PROMOTION.value
        and field.get("applicability_scope", {}).get("unknown_or_unbounded") is False
        for field in field_outcomes
    )
    if generation_boundary_established and has_safe_field:
        return CandidateOutcome.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT
    return CandidateOutcome.APPLICABILITY_EVIDENCE_INSUFFICIENT


def compute_top_level_result(
    attempted_candidate_results: Sequence[tuple[int, CandidateOutcome]],
) -> TopLevelResult:
    """Mechanically derive the slice's single top-level result from the
    fixed three-rule precedence: first READY wins; else any cleared-but-
    insufficient attempted candidate yields APPLICABILITY_EVIDENCE_INSUFFICIENT;
    else (every attempted candidate rights-blocked) RIGHTS_CLEARANCE_BLOCKED.

    *attempted_candidate_results* must contain ATTEMPTED candidates only --
    a candidate that was never researched has no result and must never be
    passed here at all."""
    for _rank, result in attempted_candidate_results:
        if result == CandidateOutcome.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT:
            return TopLevelResult.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT
    if any(
        result == CandidateOutcome.APPLICABILITY_EVIDENCE_INSUFFICIENT
        for _rank, result in attempted_candidate_results
    ):
        return TopLevelResult.APPLICABILITY_EVIDENCE_INSUFFICIENT
    return TopLevelResult.RIGHTS_CLEARANCE_BLOCKED


def validate_sequential_stop_invariant(
    entries: Sequence[CandidateSequenceEntry],
) -> list[str]:
    """Validate the stop-on-first-positive sequencing invariant over the
    fixed rank order, given each rank's ``(attempt_status, result)`` pair:

    - an ``ATTEMPTED`` rank MUST carry a non-null ``CandidateOutcome``;
    - a ``NOT_ATTEMPTED_AFTER_SUCCESS`` rank MUST carry a null result (it is
      not a fourth candidate-result value);
    - every rank strictly after the first READY rank MUST be
      ``NOT_ATTEMPTED_AFTER_SUCCESS``;
    - ``NOT_ATTEMPTED_AFTER_SUCCESS`` MUST NOT appear before any rank has
      reached READY.
    """
    problems: list[str] = []
    ready_rank: int | None = None
    for rank, attempt_status, result in entries:
        if attempt_status == AttemptStatus.ATTEMPTED and result is None:
            problems.append(f"rank {rank}: attempt_status=ATTEMPTED requires a non-null result")
        if attempt_status == AttemptStatus.NOT_ATTEMPTED_AFTER_SUCCESS and result is not None:
            problems.append(
                f"rank {rank}: attempt_status=NOT_ATTEMPTED_AFTER_SUCCESS requires a null "
                f"result, got {result!r} -- NOT_ATTEMPTED_AFTER_SUCCESS is not a fourth "
                "candidate result"
            )

        if ready_rank is not None:
            if attempt_status != AttemptStatus.NOT_ATTEMPTED_AFTER_SUCCESS:
                problems.append(
                    f"rank {rank} must have attempt_status=NOT_ATTEMPTED_AFTER_SUCCESS because "
                    f"rank {ready_rank} already reached "
                    "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT"
                )
            continue

        if attempt_status == AttemptStatus.NOT_ATTEMPTED_AFTER_SUCCESS:
            problems.append(
                f"rank {rank} has attempt_status=NOT_ATTEMPTED_AFTER_SUCCESS but no earlier rank "
                "reached READY"
            )
        elif result == CandidateOutcome.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT:
            ready_rank = rank
    return problems


def verify_result_self_consistency(
    document: Mapping[str, Any],
    *,
    field_applicability_document: Mapping[str, Any],
    boatdesign_applicability_document: Mapping[str, Any],
    source_clearance_document: Mapping[str, Any],
    source_retrieval_log_document: Mapping[str, Any],
) -> list[str]:
    """Independently recompute every candidate's attempt status, result, the
    sequential stop invariant, and the top-level result purely from the
    OTHER four retained documents (never from ``result.json``'s own claims),
    then compare against ``result.json``'s own asserted values -- so a
    tampered ``result.json`` cannot assert a result its own inputs do not
    mechanically produce, cannot mark a later rank ATTEMPTED after an
    earlier READY, and cannot claim retrievals occurred for a rank that was
    never attempted.
    """
    problems: list[str] = []
    fixed_ranks = [c.rank for c in FIXED_CANDIDATE_SEQUENCE]

    by_rank = {row["candidate_rank"]: row for row in document.get("candidates", [])}
    if set(by_rank) != set(fixed_ranks):
        return [f"result.json candidate rank set {sorted(by_rank)!r} != {fixed_ranks!r}"]

    entries: list[CandidateSequenceEntry] = []
    for rank in fixed_ranks:
        row = by_rank[rank]
        attempt_status_raw = row.get("attempt_status")
        try:
            attempt_status = AttemptStatus(attempt_status_raw)
        except ValueError:
            problems.append(
                f"rank {rank}: attempt_status={attempt_status_raw!r} is not a valid AttemptStatus"
            )
            entries.append((rank, AttemptStatus.NOT_ATTEMPTED_AFTER_SUCCESS, None))
            continue
        result_raw = row.get("result")
        result: CandidateOutcome | None = None
        if result_raw is not None:
            try:
                result = CandidateOutcome(result_raw)
            except ValueError:
                problems.append(
                    f"rank {rank}: result={result_raw!r} is not a valid CandidateOutcome"
                )
        entries.append((rank, attempt_status, result))

    problems.extend(validate_sequential_stop_invariant(entries))

    attempted_ranks = frozenset(
        rank for rank, status, _ in entries if status == AttemptStatus.ATTEMPTED
    )
    not_attempted_ranks = frozenset(
        rank for rank, status, _ in entries if status == AttemptStatus.NOT_ATTEMPTED_AFTER_SUCCESS
    )

    fields_by_rank = {
        row["candidate_rank"]: row["fields"]
        for row in field_applicability_document.get("candidates", [])
    }
    boundary_by_rank = {
        row["candidate_rank"]: row["generation_boundary_established_for_this_pilot"]
        for row in boatdesign_applicability_document.get("candidates", [])
    }
    clearance_by_rank = {
        row["candidate_rank"]: row for row in source_clearance_document.get("candidates", [])
    }
    for label, doc_ranks in (
        ("field_applicability", set(fields_by_rank)),
        ("boatdesign_applicability", set(boundary_by_rank)),
        ("source_clearance_assessment", set(clearance_by_rank)),
    ):
        if doc_ranks != attempted_ranks:
            problems.append(
                f"{label} rank set {sorted(doc_ranks)!r} != independently-derived "
                f"attempt_status=ATTEMPTED rank set {sorted(attempted_ranks)!r} -- an unattempted "
                "rank must carry no evidence row at all, and every attempted rank must carry "
                "exactly one"
            )

    retrieval_counts_by_rank: dict[int, int] = {}
    for retrieval_entry in source_retrieval_log_document.get("retrievals", []):
        retrieval_rank = retrieval_entry.get("candidate_rank")
        if isinstance(retrieval_rank, int):
            retrieval_counts_by_rank[retrieval_rank] = (
                retrieval_counts_by_rank.get(retrieval_rank, 0) + 1
            )

    recomputed_attempted_results: list[tuple[int, CandidateOutcome]] = []
    for rank, attempt_status, retained_result in entries:
        actual_retrieval_count = retrieval_counts_by_rank.get(rank, 0)
        retained_retrieval_count = by_rank[rank].get("retrieval_count")
        if retained_retrieval_count != actual_retrieval_count:
            problems.append(
                f"rank {rank}: retained retrieval_count={retained_retrieval_count!r} != actual "
                f"source_retrieval_log.json count {actual_retrieval_count}"
            )

        if attempt_status == AttemptStatus.NOT_ATTEMPTED_AFTER_SUCCESS:
            if actual_retrieval_count != 0:
                problems.append(
                    f"rank {rank}: attempt_status=NOT_ATTEMPTED_AFTER_SUCCESS but "
                    f"{actual_retrieval_count} retrieval(s) exist in source_retrieval_log.json -- "
                    "no semantic source retrieval may exist for an unattempted rank"
                )
            continue

        # attempt_status == ATTEMPTED
        if actual_retrieval_count == 0:
            problems.append(
                f"rank {rank}: attempt_status=ATTEMPTED but zero retrievals exist in "
                "source_retrieval_log.json -- a genuinely attempted candidate requires at least "
                "one bounded source retrieval"
            )
        if (
            rank not in fields_by_rank
            or rank not in boundary_by_rank
            or rank not in clearance_by_rank
        ):
            problems.append(
                f"rank {rank}: attempt_status=ATTEMPTED but missing from one or more of "
                "field_applicability.json / boatdesign_applicability.json / "
                "source_clearance_assessment.json"
            )
            continue
        recomputed = compute_candidate_result(
            source_cleared=candidate_source_cleared(clearance_by_rank[rank]),
            generation_boundary_established=boundary_by_rank[rank],
            field_outcomes=fields_by_rank[rank],
        )
        if retained_result != recomputed:
            retained_display = retained_result.value if retained_result is not None else None
            problems.append(
                f"rank {rank}: retained result={retained_display!r} recomputed={recomputed.value!r}"
            )
        recomputed_attempted_results.append((rank, recomputed))

    problems.extend(
        validate_stop_on_first_positive_retrievals(
            source_retrieval_log_document, not_attempted_ranks=not_attempted_ranks
        )
    )

    recomputed_top_level = compute_top_level_result(recomputed_attempted_results)
    if document.get("top_level_result") != recomputed_top_level.value:
        problems.append(
            f"top_level_result retained={document.get('top_level_result')!r} recomputed="
            f"{recomputed_top_level.value!r}"
        )

    if recomputed_top_level == TopLevelResult.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT:
        successful_rank = next(
            (
                rank
                for rank, result in recomputed_attempted_results
                if result == CandidateOutcome.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT
            ),
            None,
        )
        if document.get("successful_rank") != successful_rank:
            problems.append(
                f"successful_rank retained={document.get('successful_rank')!r} recomputed="
                f"{successful_rank!r}"
            )
    elif document.get("successful_rank") is not None:
        problems.append(
            f"successful_rank={document.get('successful_rank')!r} but top_level_result is not READY"
        )

    return problems


# ---------------------------------------------------------------------------
# 7. Retained-package artifact-integrity digests
# ---------------------------------------------------------------------------

ARTIFACT_DIGESTS_SCHEMA_VERSION = "sl0032-artifact-digests-v1"
ARTIFACT_DIGESTS_FILENAME = "ARTIFACT-DIGESTS.json"


def retained_package_filenames(package_dir: Path) -> set[str]:
    """Every regular file directly inside *package_dir* except the digest
    document itself, discovered dynamically (never a hardcoded allowlist)."""
    return {
        p.name for p in package_dir.iterdir() if p.is_file() and p.name != ARTIFACT_DIGESTS_FILENAME
    }


def build_artifact_digests(*, generated_at: str, package_dir: Path) -> dict[str, Any]:
    """Build the retained ``ARTIFACT-DIGESTS.json`` document: a SHA256 digest
    of every retained SLICE-0032 package file except the digest document
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
