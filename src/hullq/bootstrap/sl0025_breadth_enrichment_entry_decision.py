"""Stage-3.2 breadth-sufficiency / Stage-3.3 parallel-entry governance
decision -- SLICE-0025.

Implements the pure, deterministic decision logic described in
``docs/slices/SLICE-0025-stage-3-2-breadth-sufficiency-stage-3-3-parallel-entry-decision.md``.

This module performs no network acquisition, no new external research and no
canonical HullQ mutation. Given only already-retained SLICE-0018/0020/0021/
0022/0023/0024 accepted artifacts, it:

- reproduces the slice's fixed accepted evidence boundary directly from those
  retained artifacts and fails closed (``BLOCKED_ON_ACCEPTED_STATE``) on any
  drift;
- evaluates the accepted evidence against the four known Stage-3.2 breadth
  mechanisms (SLICE-0018 larger direct-discovery limit, SLICE-0020
  manufacturer/archive bulk bootstrap, SLICE-0021/0022 alternative Wikidata
  route, SLICE-0023/0024 full Wikimedia-lead verification campaign) for a
  qualifying already-cleared, materially-different, unexecuted, >=100-yield
  route;
- evaluates the accepted Stage-3.3 parallel-enrichment readiness conditions;
- applies the precommitted decision rule in exact order to produce exactly
  one of ``CONTINUE_STAGE_3_2_ONLY``, ``BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL``
  or ``BLOCKED_ON_ACCEPTED_STATE``.

Explicitly does NOT:
- perform any web/search/network acquisition;
- create, modify or delete any canonical HullQ row;
- declare Stage 3.2 complete, G4 passed, or authorize broad enrichment;
- invent an unexecuted source or an unmeasured expected yield.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from hullq.bootstrap.wikimedia_sl0024_independent_verification import (
    IN_SCOPE_MIN_INDEPENDENT_SUPPORTED,
)

__all__ = [
    "BOUNDED_SUBSET_STRUCTURALLY_ACHIEVABLE",
    "FIXED_ACCEPTED_BOUNDARY",
    "KNOWN_BREADTH_PATH_CANDIDATES",
    "SL0018_MANIFEST_PATH",
    "SL0020_ARCHIVE_CLEARANCE_PATH",
    "SL0021_DISCOVERY_PROBE_PATH",
    "SL0022_MANIFEST_PATH",
    "SL0022_REPLAY_RESULT_PATH",
    "SL0023_QUALITY_SAMPLE_PATH",
    "SL0024_VERIFICATION_RESULTS_PATH",
    "AcceptedBoundaryIntegrityError",
    "BreadthPathCandidate",
    "Decision",
    "ParallelReadinessConditions",
    "build_decision_input_document",
    "build_decision_result_document",
    "build_known_breadth_path_candidates",
    "determine_decision",
    "evaluate_boundary_consistency",
    "evaluate_parallel_readiness",
    "find_qualifying_breadth_path",
    "load_reproduced_boundary",
    "verify_artifact_digests_self_consistency",
    "verify_decision_result_self_consistency",
]


# ---------------------------------------------------------------------------
# Fixed accepted evidence boundary (controlling slice "Fixed accepted
# evidence boundary")
# ---------------------------------------------------------------------------

FIXED_ACCEPTED_BOUNDARY: dict[str, Any] = {
    "accepted_canonical_boat_models": 1770,
    "historical_qid_to_hullq_id_mappings": 1772,
    "sl0018_direct_discovery_unique_qids": 1829,
    "sl0018_requested_direct_discovery_limit": 2500,
    "sl0020_adapter_ready_archive_sources": 0,
    "sl0021_alternative_route_candidate_union": 57,
    "sl0022_auto_admit_from_57": 0,
    "sl0022_review_required": 31,
    "sl0022_not_admitted": 26,
    "sl0023_incremental_wikimedia_qid_leads": 409,
    "sl0024_threshold_set_independently_supported_in_scope": 11,
    "sl0024_threshold_required": IN_SCOPE_MIN_INDEPENDENT_SUPPORTED,
    "sl0024_final_recommendation": "LOW_INDEPENDENT_VERIFICATION_YIELD",
}

ROOT = Path(__file__).resolve().parents[3]
SL0018_MANIFEST_PATH = (
    ROOT / "research" / "bootstrap" / "wikidata" / "sl0018-2500" / "manifest.json"
)
SL0020_ARCHIVE_CLEARANCE_PATH = (
    ROOT / "research" / "manufacturers" / "archive_clearance" / "archive_source_clearance.json"
)
SL0021_DISCOVERY_PROBE_PATH = (
    ROOT / "research" / "bootstrap" / "wikidata" / "sl0021-alt-discovery" / "discovery_probe.json"
)
SL0022_MANIFEST_PATH = (
    ROOT / "research" / "bootstrap" / "wikidata" / "sl0022-alt-route-admission" / "manifest.json"
)
SL0022_REPLAY_RESULT_PATH = (
    ROOT
    / "research"
    / "bootstrap"
    / "wikidata"
    / "sl0022-alt-route-admission"
    / "REPLAY-RESULT.json"
)
SL0023_QUALITY_SAMPLE_PATH = (
    ROOT / "research" / "bootstrap" / "wikimedia" / "sl0023-category-leads" / "quality_sample.json"
)
SL0024_VERIFICATION_RESULTS_PATH = (
    ROOT
    / "research"
    / "bootstrap"
    / "wikimedia"
    / "sl0024-independent-verification"
    / "verification_results.json"
)


class AcceptedBoundaryIntegrityError(RuntimeError):
    """Raised when a retained SLICE-0018/0020/0021/0022/0023/0024 artifact
    cannot be read or does not carry the expected fixed-boundary field.

    SLICE-0025 MUST fail closed (BLOCKED) rather than silently proceed on a
    missing or structurally broken retained artifact.
    """


def load_reproduced_boundary(
    *,
    sl0018_manifest_path: Path = SL0018_MANIFEST_PATH,
    sl0020_archive_clearance_path: Path = SL0020_ARCHIVE_CLEARANCE_PATH,
    sl0021_discovery_probe_path: Path = SL0021_DISCOVERY_PROBE_PATH,
    sl0022_manifest_path: Path = SL0022_MANIFEST_PATH,
    sl0022_replay_result_path: Path = SL0022_REPLAY_RESULT_PATH,
    sl0023_quality_sample_path: Path = SL0023_QUALITY_SAMPLE_PATH,
    sl0024_verification_results_path: Path = SL0024_VERIFICATION_RESULTS_PATH,
) -> dict[str, Any]:
    """Read every retained accepted artifact and mechanically extract the
    fixed accepted evidence boundary facts, plus the two zero-tolerance
    identity-foundation flags used by the parallel-readiness rule.

    Pure file I/O only -- no network access. Raises
    ``AcceptedBoundaryIntegrityError`` if a retained artifact is missing or
    does not carry an expected field; never invents a substitute value.
    """
    try:
        sl0018 = json.loads(sl0018_manifest_path.read_bytes().decode("utf-8"))
        sl0020 = json.loads(sl0020_archive_clearance_path.read_bytes().decode("utf-8"))
        sl0021 = json.loads(sl0021_discovery_probe_path.read_bytes().decode("utf-8"))
        sl0022 = json.loads(sl0022_manifest_path.read_bytes().decode("utf-8"))
        sl0022_replay = json.loads(sl0022_replay_result_path.read_bytes().decode("utf-8"))
        sl0023 = json.loads(sl0023_quality_sample_path.read_bytes().decode("utf-8"))
        sl0024 = json.loads(sl0024_verification_results_path.read_bytes().decode("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptedBoundaryIntegrityError(
            f"a retained SLICE-0025 input artifact could not be read: {exc}"
        ) from exc

    try:
        adapter_ready_count = sum(
            1 for source in sl0020["sources"] if source["adapter_ready_test"]["result"] is True
        )
        prior_baseline_verified = sl0022_replay["first_pass"][
            "prior_baseline_verified_before_sl0022"
        ]
        return {
            "accepted_canonical_boat_models": sl0018["counts"][
                "combined_canonical_boat_model_count_expected"
            ],
            "historical_qid_to_hullq_id_mappings": len(sl0018["retained_crosswalk"]),
            "sl0018_direct_discovery_unique_qids": sl0018["discovery"]["unique_qids_returned"],
            "sl0018_requested_direct_discovery_limit": sl0018["requested_limit"],
            "sl0020_adapter_ready_archive_sources": adapter_ready_count,
            "sl0021_alternative_route_candidate_union": sl0021["cross_route_overlap"][
                "total_union_count"
            ],
            "sl0022_auto_admit_from_57": sl0022["counts"]["auto_admit"],
            "sl0022_review_required": sl0022["counts"]["review_required"],
            "sl0022_not_admitted": sl0022["counts"]["not_admitted"],
            "sl0023_incremental_wikimedia_qid_leads": sl0023["unique_incremental_qid_lead_count"],
            "sl0024_threshold_set_independently_supported_in_scope": sl0024["metrics"][
                "threshold_set_independently_supported_in_scope_count"
            ],
            "sl0024_threshold_required": IN_SCOPE_MIN_INDEPENDENT_SUPPORTED,
            "sl0024_final_recommendation": sl0024["recommendation"],
            "zero_tolerance_conditions_clear": bool(
                sl0022_replay["all_zero_tolerance_conditions_clear"]
            ),
            "prior_baseline_verified_before_sl0022": bool(prior_baseline_verified["counts_match"])
            and bool(prior_baseline_verified["id_set_matches"])
            and prior_baseline_verified["readback_mismatches"] == 0,
        }
    except KeyError as exc:
        raise AcceptedBoundaryIntegrityError(
            f"a retained SLICE-0025 input artifact is missing an expected field: {exc}"
        ) from exc


_MISSING = object()


def evaluate_boundary_consistency(
    reproduced: Mapping[str, Any], fixed: Mapping[str, Any] | None = None
) -> list[str]:
    """Pure comparison: every key in ``fixed`` must equal ``reproduced``.

    Returns the (possibly empty) list of mismatch descriptions. Never raises
    -- this is the input to rule 1 of the precommitted decision rule
    (``determine_decision``), and is deliberately pure/synthetic-testable
    independent of file I/O so the ``BLOCKED_ON_ACCEPTED_STATE`` branch can
    be exercised with a synthetic ``reproduced`` mapping.
    """
    if fixed is None:
        fixed = FIXED_ACCEPTED_BOUNDARY
    mismatches: list[str] = []
    for key, expected in fixed.items():
        actual = reproduced.get(key, _MISSING)
        if actual != expected:
            mismatches.append(f"{key}: expected {expected!r}, reproduced {actual!r}")
    return mismatches


# ---------------------------------------------------------------------------
# Rule 2 -- known executable high-yield breadth path (controlling slice
# "Known executable high-yield breadth path")
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BreadthPathCandidate:
    """One known Stage-3.2 breadth mechanism, evaluated against the fixed
    accepted evidence. All boolean/count fields must be traceable to an
    accepted closure or reproduced boundary value -- never invented."""

    name: str
    source_slices: str
    already_executed: bool
    production_bulk_cleared: bool
    materially_different_from_sl0018: bool
    likely_incremental_yield: int
    requires_full_wikimedia_campaign: bool
    requires_upstream_governance_decision: bool
    rationale: str

    def qualifies(self) -> bool:
        """Rule-2 qualification test: an *unexecuted*, already-cleared,
        materially-different mechanism with a likely yield of >=100 that
        does not require the rejected full 409-lead Wikimedia campaign and
        does not require resolving an open upstream governance question."""
        return (
            not self.already_executed
            and self.production_bulk_cleared
            and self.materially_different_from_sl0018
            and self.likely_incremental_yield >= 100
            and not self.requires_full_wikimedia_campaign
            and not self.requires_upstream_governance_decision
        )


def build_known_breadth_path_candidates(
    reproduced: Mapping[str, Any],
) -> tuple[BreadthPathCandidate, ...]:
    """Build the four known Stage-3.2 breadth mechanisms from the reproduced
    accepted boundary, per the controlling slice's "Required analysis"."""
    return (
        BreadthPathCandidate(
            name="sl0018_larger_direct_discovery_limit",
            source_slices="SLICE-0018",
            already_executed=True,
            production_bulk_cleared=True,
            materially_different_from_sl0018=False,
            likely_incremental_yield=0,
            requires_full_wikimedia_campaign=False,
            requires_upstream_governance_decision=False,
            rationale=(
                "Same exact direct-instance Wikidata strategy already measured a "
                f"{reproduced['sl0018_direct_discovery_unique_qids']}-QID source ceiling against a "
                f"requested limit of {reproduced['sl0018_requested_direct_discovery_limit']}. The "
                "accepted SLICE-0018 closure states that simply increasing the limit is not "
                "evidence that further direct-instance candidates exist."
            ),
        ),
        BreadthPathCandidate(
            name="sl0020_manufacturer_archive_bulk_bootstrap",
            source_slices="SLICE-0020",
            already_executed=True,
            production_bulk_cleared=reproduced["sl0020_adapter_ready_archive_sources"] > 0,
            materially_different_from_sl0018=True,
            likely_incremental_yield=0,
            requires_full_wikimedia_campaign=False,
            requires_upstream_governance_decision=False,
            rationale=(
                f"{reproduced['sl0020_adapter_ready_archive_sources']} of 10 assessed "
                "manufacturer/heritage archive sources reached ADAPTER_READY under the accepted "
                "source-rights model; no cleared bulk-bootstrap source exists to measure a yield "
                "from."
            ),
        ),
        BreadthPathCandidate(
            name="sl0021_sl0022_alternative_wikidata_route",
            source_slices="SLICE-0021, SLICE-0022",
            already_executed=True,
            production_bulk_cleared=True,
            materially_different_from_sl0018=True,
            likely_incremental_yield=reproduced["sl0022_auto_admit_from_57"],
            requires_full_wikimedia_campaign=False,
            requires_upstream_governance_decision=False,
            rationale=(
                f"Already executed: the {reproduced['sl0021_alternative_route_candidate_union']}-QID "
                "alternative-route union was already run through Tier-0 admission and produced "
                f"{reproduced['sl0022_auto_admit_from_57']} AUTO_ADMIT "
                f"({reproduced['sl0022_review_required']} REVIEW_REQUIRED, "
                f"{reproduced['sl0022_not_admitted']} NOT_ADMITTED). It is not an unexecuted "
                "mechanism, and its realized yield is far below 100."
            ),
        ),
        BreadthPathCandidate(
            name="sl0023_sl0024_full_wikimedia_verification_campaign",
            source_slices="SLICE-0023, SLICE-0024",
            already_executed=False,
            production_bulk_cleared=False,
            materially_different_from_sl0018=True,
            likely_incremental_yield=reproduced["sl0023_incremental_wikimedia_qid_leads"],
            requires_full_wikimedia_campaign=True,
            requires_upstream_governance_decision=False,
            rationale=(
                f"The {reproduced['sl0023_incremental_wikimedia_qid_leads']}-lead yield is >=100, "
                "but Wikipedia/Wikimedia remains cleared for research-lead use only (not bulk "
                "canonical admission), and a full campaign over all leads is exactly what the "
                f"accepted SLICE-0024 result ({reproduced['sl0024_final_recommendation']}, "
                f"{reproduced['sl0024_threshold_set_independently_supported_in_scope']} < "
                f"{reproduced['sl0024_threshold_required']} required) rejected as unjustified."
            ),
        ),
    )


# Snapshot built from the real accepted boundary for direct import/inspection
# (e.g. by the runner/report). Rule-2 evaluation for the actual decision
# always rebuilds this from the freshly reproduced boundary via
# ``build_known_breadth_path_candidates`` -- this constant is a convenience
# view over that same real accepted evidence, not a second source of truth.
KNOWN_BREADTH_PATH_CANDIDATES: tuple[BreadthPathCandidate, ...] = (
    build_known_breadth_path_candidates(FIXED_ACCEPTED_BOUNDARY)
)


def find_qualifying_breadth_path(
    candidates: Sequence[BreadthPathCandidate],
) -> BreadthPathCandidate | None:
    """Return the first candidate satisfying every rule-2 condition, or
    ``None`` if none qualifies. Deliberately pure/synthetic-testable: pass a
    synthetic candidate list to exercise the qualifying-path branch without
    representing it as real project evidence."""
    for candidate in candidates:
        if candidate.qualifies():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Rule 3 -- parallel-enrichment readiness (controlling slice
# "Parallel-enrichment readiness")
# ---------------------------------------------------------------------------

# Any future Stage-3.3 pilot slice authorized by this decision is, by this
# decision's own "Interpretation" section, restricted to a bounded
# deterministic subset of already-canonical BoatModels using the existing
# unknown/conflict/provenance vocabulary -- the same pattern already used by
# every SLICE-0018/0021/0022/0023/0024 retained package. This condition is
# therefore a structural property of how such a slice must be scoped, not a
# fact requiring a separate numeric artifact; it is recorded explicitly
# (rather than silently assumed) so a reviewer can see and challenge it.
BOUNDED_SUBSET_STRUCTURALLY_ACHIEVABLE = True


@dataclass(frozen=True)
class ParallelReadinessConditions:
    """The rule-3 parallel-enrichment readiness conditions, each traceable
    to a reproduced accepted-boundary fact or the rule-2 result."""

    zero_tolerance_identity_foundation_accepted: bool
    canonical_count_at_least_1000: bool
    canonical_count_at_least_1770: bool
    no_qualifying_breadth_path_pending: bool
    sl0022_zero_auto_admit_established: bool
    sl0024_below_yield_threshold: bool
    bounded_subset_and_provenance_preservable: bool

    def all_met(self) -> bool:
        return all(
            (
                self.zero_tolerance_identity_foundation_accepted,
                self.canonical_count_at_least_1000,
                self.canonical_count_at_least_1770,
                self.no_qualifying_breadth_path_pending,
                self.sl0022_zero_auto_admit_established,
                self.sl0024_below_yield_threshold,
                self.bounded_subset_and_provenance_preservable,
            )
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "zero_tolerance_identity_foundation_accepted": self.zero_tolerance_identity_foundation_accepted,
            "canonical_count_at_least_1000": self.canonical_count_at_least_1000,
            "canonical_count_at_least_1770": self.canonical_count_at_least_1770,
            "no_qualifying_breadth_path_pending": self.no_qualifying_breadth_path_pending,
            "sl0022_zero_auto_admit_established": self.sl0022_zero_auto_admit_established,
            "sl0024_below_yield_threshold": self.sl0024_below_yield_threshold,
            "bounded_subset_and_provenance_preservable": self.bounded_subset_and_provenance_preservable,
            "all_met": self.all_met(),
        }


def evaluate_parallel_readiness(
    reproduced: Mapping[str, Any],
    *,
    qualifying_breadth_path: BreadthPathCandidate | None,
    bounded_subset_achievable: bool = BOUNDED_SUBSET_STRUCTURALLY_ACHIEVABLE,
) -> ParallelReadinessConditions:
    """Mechanically evaluate every rule-3 condition from the reproduced
    accepted boundary and the rule-2 result."""
    return ParallelReadinessConditions(
        zero_tolerance_identity_foundation_accepted=bool(
            reproduced.get("zero_tolerance_conditions_clear")
        )
        and bool(reproduced.get("prior_baseline_verified_before_sl0022")),
        canonical_count_at_least_1000=reproduced["accepted_canonical_boat_models"] >= 1000,
        canonical_count_at_least_1770=reproduced["accepted_canonical_boat_models"] >= 1770,
        no_qualifying_breadth_path_pending=qualifying_breadth_path is None,
        sl0022_zero_auto_admit_established=reproduced["sl0022_auto_admit_from_57"] == 0,
        sl0024_below_yield_threshold=(
            reproduced["sl0024_threshold_set_independently_supported_in_scope"]
            < reproduced["sl0024_threshold_required"]
        ),
        bounded_subset_and_provenance_preservable=bounded_subset_achievable,
    )


# ---------------------------------------------------------------------------
# Precommitted decision rule (controlling slice "Precommitted decision rule")
# ---------------------------------------------------------------------------


class Decision(StrEnum):
    CONTINUE_STAGE_3_2_ONLY = "CONTINUE_STAGE_3_2_ONLY"
    BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL = "BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL"
    BLOCKED_ON_ACCEPTED_STATE = "BLOCKED_ON_ACCEPTED_STATE"


def determine_decision(
    *,
    boundary_mismatches: Sequence[str],
    qualifying_breadth_path: BreadthPathCandidate | None,
    readiness: ParallelReadinessConditions,
) -> Decision:
    """Apply the precommitted decision rule in exact order:

    1. accepted-state integrity;
    2. known executable high-yield breadth path;
    3. parallel-enrichment readiness, else ``CONTINUE_STAGE_3_2_ONLY``.
    """
    if boundary_mismatches:
        return Decision.BLOCKED_ON_ACCEPTED_STATE
    if qualifying_breadth_path is not None:
        return Decision.CONTINUE_STAGE_3_2_ONLY
    if readiness.all_met():
        return Decision.BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL
    return Decision.CONTINUE_STAGE_3_2_ONLY


# ---------------------------------------------------------------------------
# Retained document assembly -- JSON-primitive, pure (no network/DB access)
# ---------------------------------------------------------------------------

DECISION_INPUT_SCHEMA_VERSION = "sl0025-decision-input-v1"
DECISION_RESULT_SCHEMA_VERSION = "sl0025-decision-result-v1"


def _candidate_to_dict(candidate: BreadthPathCandidate) -> dict[str, Any]:
    return {
        "name": candidate.name,
        "source_slices": candidate.source_slices,
        "already_executed": candidate.already_executed,
        "production_bulk_cleared": candidate.production_bulk_cleared,
        "materially_different_from_sl0018": candidate.materially_different_from_sl0018,
        "likely_incremental_yield": candidate.likely_incremental_yield,
        "requires_full_wikimedia_campaign": candidate.requires_full_wikimedia_campaign,
        "requires_upstream_governance_decision": candidate.requires_upstream_governance_decision,
        "qualifies": candidate.qualifies(),
        "rationale": candidate.rationale,
    }


def build_decision_input_document(
    *, generated_at: str, reproduced: Mapping[str, Any], candidates: Sequence[BreadthPathCandidate]
) -> dict[str, Any]:
    """Assemble the retained ``decision_input.json`` document."""
    return {
        "schema_version": DECISION_INPUT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "fixed_accepted_boundary": dict(FIXED_ACCEPTED_BOUNDARY),
        "reproduced_accepted_boundary": dict(reproduced),
        "boundary_mismatches": evaluate_boundary_consistency(reproduced),
        "known_breadth_path_candidates": [_candidate_to_dict(c) for c in candidates],
    }


def build_decision_result_document(
    *, generated_at: str, decision_input: Mapping[str, Any]
) -> dict[str, Any]:
    """Assemble the retained ``decision_result.json`` document by
    mechanically applying the precommitted decision rule to an already-built
    ``decision_input`` document."""
    reproduced = decision_input["reproduced_accepted_boundary"]
    boundary_mismatches = list(decision_input["boundary_mismatches"])
    candidates = [
        BreadthPathCandidate(
            name=c["name"],
            source_slices=c["source_slices"],
            already_executed=c["already_executed"],
            production_bulk_cleared=c["production_bulk_cleared"],
            materially_different_from_sl0018=c["materially_different_from_sl0018"],
            likely_incremental_yield=c["likely_incremental_yield"],
            requires_full_wikimedia_campaign=c["requires_full_wikimedia_campaign"],
            requires_upstream_governance_decision=c["requires_upstream_governance_decision"],
            rationale=c["rationale"],
        )
        for c in decision_input["known_breadth_path_candidates"]
    ]
    qualifying_breadth_path = (
        find_qualifying_breadth_path(candidates) if not boundary_mismatches else None
    )
    readiness = (
        evaluate_parallel_readiness(reproduced, qualifying_breadth_path=qualifying_breadth_path)
        if not boundary_mismatches
        else None
    )
    decision = determine_decision(
        boundary_mismatches=boundary_mismatches,
        qualifying_breadth_path=qualifying_breadth_path,
        readiness=readiness
        if readiness is not None
        else ParallelReadinessConditions(False, False, False, False, False, False, False),
    )

    return {
        "schema_version": DECISION_RESULT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "boundary_mismatches": boundary_mismatches,
        "qualifying_breadth_path": (
            _candidate_to_dict(qualifying_breadth_path)
            if qualifying_breadth_path is not None
            else None
        ),
        "parallel_readiness_conditions": (readiness.as_dict() if readiness is not None else None),
        "decision": str(decision),
        "interpretation": {
            "declares_stage_3_2_complete": False,
            "declares_g4_pass": False,
            "authorizes_broad_enrichment": False,
            "stage_3_2_remains_open": True,
        },
    }


# ---------------------------------------------------------------------------
# Offline self-consistency verification of already-retained documents
# ---------------------------------------------------------------------------


def verify_decision_result_self_consistency(
    *, decision_input: Mapping[str, Any], decision_result: Mapping[str, Any]
) -> list[str]:
    """Recompute the decision result fresh from a retained
    ``decision_input.json`` document and compare against a retained
    ``decision_result.json`` document."""
    recomputed = build_decision_result_document(
        generated_at=decision_result.get("generated_at", ""), decision_input=decision_input
    )
    keys = (
        "boundary_mismatches",
        "qualifying_breadth_path",
        "parallel_readiness_conditions",
        "decision",
        "interpretation",
    )
    return [
        f"{key}: stored={decision_result.get(key)!r} != recomputed {recomputed.get(key)!r}"
        for key in keys
        if decision_result.get(key) != recomputed.get(key)
    ]


def verify_artifact_digests_self_consistency(
    *, artifact_digests: Mapping[str, Any], package_dir: Path
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
