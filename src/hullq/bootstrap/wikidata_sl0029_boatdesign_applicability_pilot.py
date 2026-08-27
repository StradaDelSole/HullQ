"""Primary-source BoatDesign applicability & conditional-clearance pilot — SLICE-0029.

Implements the pure, deterministic logic described in
``docs/slices/SLICE-0029-primary-source-boatdesign-applicability-clearance-pilot.md``.

Scope is deliberately tiny relative to the SLICE-0028 full-boundary rollout: exactly
two fixed pilot BoatModels (Wikidata Q5051252 "Catalina 22" and Q5051253 "Catalina
30", already retained in ``research/manufacturers/overlap_result.json`` and the
SLICE-0028 linkage/evidence manifest) and exactly the five existing Tier-1 dimension
field pointers.

This module performs no network acquisition. The bounded manual official-Catalina
research itself (<=25 retrievals) was performed interactively and is retained as data
in ``research/stage3/sl0029-primary-source-boatdesign-applicability/
source_retrieval_log.json``; the qualitative BoatDesign-generation/option findings
derived from it are retained in ``boatdesign_applicability.json``. What this module
*does* make deterministic and offline-reproducible is:

- reproducing the exact two-QID -> canonical-BoatModel pilot identity boundary from
  the already-accepted SLICE-0028 linkage document and the SLICE-0019/0020
  ``overlap_result.json``, hard-failing on any drift from the accepted 1,770/1,772
  identity boundary;
- validating internal consistency/ceiling of the retained retrieval log;
- evaluating the retained, schema-valid Catalina Source record through the existing
  SLICE-0007 deterministic source-use gate (``hullq.sources.rights.check_source_use``)
  for all seven use keys, rather than hand-asserting gate outcomes;
- validating that every retained field-applicability classification cites a
  ``sl0028_normalized_candidate`` that matches, byte-for-byte, the reused SLICE-0028
  evidence bundle (guards against silently reinterpreting already-accepted evidence);
- mechanically recomputing the slice's single deterministic next-step recommendation
  from the retained rights-gate outcome and applicability classifications;
- building/verifying the retained-package SHA-256 artifact-integrity digest document.

Explicitly does NOT:
- perform any network acquisition or browse a live Catalina/Wikidata source;
- infer, mint or persist a canonical BoatDesign generation, DesignOption or
  NamedVariant;
- create or mutate a canonical BoatModel/crosswalk row;
- create a FieldResolution or choose a canonical technical value;
- weaken or bypass ``hullq.sources.rights.check_source_use``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any

from hullq.sources.rights import DecisionOutcome, SourceUse, check_source_use

__all__ = [
    "ALLOWED_FIELD_POINTERS",
    "ARTIFACT_DIGESTS_FILENAME",
    "ARTIFACT_DIGESTS_SCHEMA_VERSION",
    "FIXED_QIDS",
    "RETRIEVAL_CEILING",
    "SL0029_ACTIVITY_ID",
    "ApplicabilityOutcome",
    "IdentityBoundaryIntegrityError",
    "RecommendationCode",
    "RetrievalLogIntegrityError",
    "build_artifact_digests",
    "build_pilot_identity_boundary",
    "compute_recommendation",
    "evaluate_source_use_gate",
    "retained_package_filenames",
    "validate_boatdesign_applicability",
    "validate_source_retrieval_log",
    "validate_wikidata_candidate_applicability",
    "verify_artifact_digests_self_consistency",
    "verify_pilot_identity_boundary_self_consistency",
    "verify_source_clearance_assessment_self_consistency",
]

SL0029_ACTIVITY_ID = "SLICE-0029-PRIMARY-SOURCE-BOATDESIGN-APPLICABILITY-PILOT"

# The exact, fixed SLICE-0019/0020 exact-overlap pilot QIDs. Never expanded.
FIXED_QIDS: tuple[str, str] = ("Q5051252", "Q5051253")

RETRIEVAL_CEILING = 25

ALLOWED_FIELD_POINTERS: frozenset[str] = frozenset(
    {
        "/baseline/dimensions/loa_m",
        "/baseline/dimensions/lwl_m",
        "/baseline/dimensions/beam_m",
        "/baseline/dimensions/draft_min_m",
        "/baseline/dimensions/displacement_kg",
    }
)

_ALLOWED_RETRIEVAL_HOSTS: frozenset[str] = frozenset({"www.catalinayachts.com"})


class ApplicabilityOutcome(StrEnum):
    """Fail-closed field-level applicability vocabulary (controlling slice)."""

    SAFE_FOR_LATER_DESIGN_PROMOTION = "SAFE_FOR_LATER_DESIGN_PROMOTION"
    MODEL_SCOPE_ONLY_NOT_PROMOTABLE = "MODEL_SCOPE_ONLY_NOT_PROMOTABLE"
    GENERATION_AMBIGUOUS = "GENERATION_AMBIGUOUS"
    OPTION_SENSITIVE = "OPTION_SENSITIVE"
    SOURCE_VALUE_CONFLICT = "SOURCE_VALUE_CONFLICT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NO_NORMALIZED_WIKIDATA_CANDIDATE = "NO_NORMALIZED_WIKIDATA_CANDIDATE"
    RIGHTS_BLOCKED = "RIGHTS_BLOCKED"


class RecommendationCode(StrEnum):
    """The slice's single deterministic next-step recommendation vocabulary."""

    READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT = "READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT"
    RIGHTS_CLEARANCE_BLOCKED = "RIGHTS_CLEARANCE_BLOCKED"
    APPLICABILITY_EVIDENCE_INSUFFICIENT = "APPLICABILITY_EVIDENCE_INSUFFICIENT"


class IdentityBoundaryIntegrityError(Exception):
    """Raised when the reproduced pilot identity boundary drifts from the accepted
    SLICE-0017/0018/0028 identity boundary or the fixed SLICE-0019/0020 overlap."""


class RetrievalLogIntegrityError(Exception):
    """Raised when the retained retrieval log violates the bounded-research contract."""


# ---------------------------------------------------------------------------
# 1. Pilot identity boundary
# ---------------------------------------------------------------------------


def build_pilot_identity_boundary(
    *,
    linkage_document: Mapping[str, Any],
    overlap_result: Mapping[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """Reproduce the exact two-QID -> canonical-BoatModel pilot identity boundary.

    Hard-fails (``IdentityBoundaryIntegrityError``) on any drift from the accepted
    1,770 canonical BoatModel / 1,772 historical crosswalk boundary, or if either
    fixed QID is missing from the SLICE-0028 linkage document or from the retained
    SLICE-0019/0020 exact-overlap result under the "Catalina Yachts" sample.
    """
    identity_boundary = linkage_document["identity_boundary"]
    canonical_count = identity_boundary["canonical_boat_model_count"]
    historical_count = identity_boundary["historical_crosswalk_count"]
    if canonical_count != 1770:
        raise IdentityBoundaryIntegrityError(
            f"linkage_document canonical_boat_model_count={canonical_count!r} != 1770"
        )
    if historical_count != 1772:
        raise IdentityBoundaryIntegrityError(
            f"linkage_document historical_crosswalk_count={historical_count!r} != 1772"
        )

    by_qid: dict[str, dict[str, Any]] = {}
    for entry in linkage_document["boat_models"]:
        for qid in entry["qids"]:
            by_qid[qid] = entry

    overlap_qids: dict[str, str] = {}
    for overlap_entry in overlap_result.get("exact_overlap", []):
        if overlap_entry.get("manufacturer_sample") != "Catalina Yachts":
            continue
        for match in overlap_entry.get("accepted_matches", []):
            overlap_qids[match["qid"]] = overlap_entry["probe_model_name"]

    pilot_boat_models: list[dict[str, Any]] = []
    for qid in FIXED_QIDS:
        if qid not in by_qid:
            raise IdentityBoundaryIntegrityError(
                f"fixed pilot QID {qid!r} not found in SLICE-0028 linkage document"
            )
        if qid not in overlap_qids:
            raise IdentityBoundaryIntegrityError(
                f"fixed pilot QID {qid!r} not found as a Catalina Yachts exact_overlap "
                "entry in research/manufacturers/overlap_result.json"
            )
        linkage_entry = by_qid[qid]
        pilot_boat_models.append(
            {
                "qid": qid,
                "preferred_label": linkage_entry["preferred_label_by_qid"][qid],
                "hullq_id": linkage_entry["hullq_id"],
                "overlap_result_manufacturer_sample": "Catalina Yachts",
                "overlap_result_match_kind": "exact_overlap",
            }
        )

    return {
        "schema_version": "sl0029-pilot-identity-boundary-v1",
        "generated_at": generated_at,
        "source_identity_boundary": {
            "linkage_document_path": "research/stage3/sl0028-wikidata-tier1-full-boundary/linkage.json",
            "overlap_result_path": "research/manufacturers/overlap_result.json",
            "canonical_boat_model_count": canonical_count,
            "historical_crosswalk_count": historical_count,
            "note": (
                "Both counts are reproduced unchanged from the accepted "
                "SLICE-0017+0018/0028 identity boundary. SLICE-0029 performs no "
                "discovery and admits no new BoatModel."
            ),
        },
        "pilot_boat_models": pilot_boat_models,
        "boundary_invariants": {
            "fixed_qid_count": len(FIXED_QIDS),
            "no_identity_expansion": True,
            "no_fuzzy_matching_used": True,
            "no_canonical_boat_model_id_changed": True,
            "no_historical_qid_to_hullq_id_mapping_changed": True,
        },
    }


def verify_pilot_identity_boundary_self_consistency(
    document: Mapping[str, Any],
    *,
    linkage_document: Mapping[str, Any],
    overlap_result: Mapping[str, Any],
) -> list[str]:
    """Recompute the pilot identity boundary from the reused inputs and compare."""
    mismatches: list[str] = []
    try:
        rebuilt = build_pilot_identity_boundary(
            linkage_document=linkage_document,
            overlap_result=overlap_result,
            generated_at=str(document.get("generated_at", "")),
        )
    except IdentityBoundaryIntegrityError as exc:
        return [f"identity boundary integrity error while recomputing: {exc}"]

    mismatches.extend(
        f"pilot_identity_boundary field {key!r} does not match recomputed value"
        for key in ("source_identity_boundary", "pilot_boat_models", "boundary_invariants")
        if document.get(key) != rebuilt[key]
    )
    return mismatches


# ---------------------------------------------------------------------------
# 2. Bounded retrieval log
# ---------------------------------------------------------------------------


def validate_source_retrieval_log(document: Mapping[str, Any]) -> list[str]:
    """Validate internal consistency and the <=25 bounded-retrieval ceiling."""
    problems: list[str] = []
    ceiling = document.get("retrieval_ceiling")
    if ceiling != RETRIEVAL_CEILING:
        problems.append(f"retrieval_ceiling={ceiling!r} != {RETRIEVAL_CEILING}")

    retrievals = document.get("retrievals", [])
    declared_count = document.get("retrieval_count")
    if declared_count != len(retrievals):
        problems.append(f"retrieval_count={declared_count!r} != len(retrievals)={len(retrievals)}")
    if len(retrievals) > RETRIEVAL_CEILING:
        problems.append(
            f"len(retrievals)={len(retrievals)} exceeds retrieval_ceiling={RETRIEVAL_CEILING}"
        )

    seen_indices: set[int] = set()
    for entry in retrievals:
        index = entry.get("retrieval_index")
        if not isinstance(index, int) or index in seen_indices:
            problems.append(f"duplicate or non-integer retrieval_index: {index!r}")
        if isinstance(index, int):
            seen_indices.add(index)

        url = entry.get("url", "")
        host = url.split("/")[2] if url.startswith("https://") and url.count("/") >= 2 else None
        if host not in _ALLOWED_RETRIEVAL_HOSTS:
            problems.append(f"retrieval {index!r} host {host!r} not in permitted host set")

        sha256 = entry.get("sha256", "")
        if not (len(sha256) == 64 and all(c in "0123456789abcdef" for c in sha256)):
            problems.append(
                f"retrieval {index!r} sha256 {sha256!r} is not a valid lowercase hex digest"
            )

    if seen_indices and seen_indices != set(range(1, len(retrievals) + 1)):
        problems.append(
            f"retrieval_index set {sorted(seen_indices)!r} is not exactly 1..{len(retrievals)}"
        )

    return problems


# ---------------------------------------------------------------------------
# 3. Source-rights gate evaluation (reuses hullq.sources.rights unchanged)
# ---------------------------------------------------------------------------


def evaluate_source_use_gate(source_record: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """Evaluate the retained Catalina Source record through the unmodified
    SLICE-0007 deterministic gate for all seven use keys."""
    results: dict[str, dict[str, str]] = {}
    for use in SourceUse:
        decision = check_source_use(dict(source_record), use)
        results[use.value] = {"outcome": decision.outcome.value}
    return results


def verify_source_clearance_assessment_self_consistency(
    document: Mapping[str, Any],
) -> list[str]:
    """Recompute the source-use gate decisions and the SR-6.6 boolean, and compare
    against the retained document."""
    mismatches: list[str] = []
    source_record = document["source_record"]
    recomputed = evaluate_source_use_gate(source_record)
    retained = document["source_use_gate_decisions"]["decisions"]
    if recomputed != retained:
        mismatches.append(
            f"source_use_gate_decisions mismatch: retained={retained!r} recomputed={recomputed!r}"
        )

    conditions = document["sr_6_6_condition_evaluation"]["conditions"]
    all_satisfied = all(c["satisfied"] in (True, "partial_left_unresolved") for c in conditions)
    retained_flag = document["sr_6_6_condition_evaluation"][
        "conditions_satisfied_for_bounded_manual_use"
    ]
    if retained_flag != all_satisfied:
        mismatches.append(
            "conditions_satisfied_for_bounded_manual_use "
            f"retained={retained_flag!r} recomputed={all_satisfied!r}"
        )
    return mismatches


def source_use_allowed(gate_decisions: Mapping[str, Any], use: str) -> bool:
    """True only if the given use key's gate outcome is exactly 'allowed'."""
    entry = gate_decisions.get(use, {})
    return bool(entry.get("outcome") == DecisionOutcome.ALLOWED.value)


# ---------------------------------------------------------------------------
# 4. BoatDesign applicability structural validation
# ---------------------------------------------------------------------------


def validate_boatdesign_applicability(
    document: Mapping[str, Any], *, pilot_identity_boundary: Mapping[str, Any]
) -> list[str]:
    """Validate structural invariants of the retained BoatDesign applicability findings."""
    problems: list[str] = []
    expected_hullq_ids = {m["hullq_id"] for m in pilot_identity_boundary["pilot_boat_models"]}
    found_hullq_ids: set[str] = set()
    for model in document.get("boat_models", []):
        found_hullq_ids.add(model["hullq_id"])
        if not isinstance(model.get("generation_boundary_established_for_this_pilot"), bool):
            problems.append(
                f"boat_model {model.get('qid')!r}: "
                "generation_boundary_established_for_this_pilot is not a bool"
            )
    if found_hullq_ids != expected_hullq_ids:
        problems.append(
            f"boatdesign_applicability hullq_id set {sorted(found_hullq_ids)!r} != "
            f"pilot identity boundary set {sorted(expected_hullq_ids)!r}"
        )
    return problems


# ---------------------------------------------------------------------------
# 5. Wikidata candidate field-applicability validation
# ---------------------------------------------------------------------------


def validate_wikidata_candidate_applicability(
    document: Mapping[str, Any],
    *,
    pilot_identity_boundary: Mapping[str, Any],
    evidence_manifest: Mapping[str, Any],
) -> list[str]:
    """Validate the five-field applicability vocabulary/coverage invariants and cross-check
    every cited ``sl0028_normalized_candidate`` against the reused SLICE-0028 evidence bundle
    (never reacquired/reinterpreted)."""
    problems: list[str] = []

    if set(document.get("allowed_field_pointers", [])) != ALLOWED_FIELD_POINTERS:
        problems.append("allowed_field_pointers does not match the five fixed Tier-1 pointers")

    valid_outcomes = {o.value for o in ApplicabilityOutcome}
    expected_hullq_ids = {m["hullq_id"] for m in pilot_identity_boundary["pilot_boat_models"]}

    evidence_by_hullq_id: dict[str, dict[str, Any]] = {
        bundle["hullq_id"]: bundle for bundle in evidence_manifest["requested_qid_evidence"]
    }

    found_hullq_ids: set[str] = set()
    for model in document.get("boat_models", []):
        hullq_id = model["hullq_id"]
        found_hullq_ids.add(hullq_id)
        seen_pointers: set[str] = set()
        bundle = evidence_by_hullq_id.get(hullq_id)
        evidence_by_id = {e["evidence_id"]: e for e in bundle["evidence"]} if bundle else {}

        for field in model.get("fields", []):
            pointer = field["field_pointer"]
            seen_pointers.add(pointer)
            if pointer not in ALLOWED_FIELD_POINTERS:
                problems.append(f"boat_model {hullq_id}: unexpected field pointer {pointer!r}")
            if field["outcome"] not in valid_outcomes:
                problems.append(
                    f"boat_model {hullq_id} field {pointer}: invalid outcome {field['outcome']!r}"
                )
            candidate = field.get("sl0028_normalized_candidate")
            if (
                candidate is None
                and field["outcome"] != ApplicabilityOutcome.NO_NORMALIZED_WIKIDATA_CANDIDATE.value
            ):
                problems.append(
                    f"boat_model {hullq_id} field {pointer}: candidate is null but outcome "
                    f"{field['outcome']!r} != NO_NORMALIZED_WIKIDATA_CANDIDATE"
                )
            evidence_id = field.get("sl0028_evidence_id")
            if evidence_id is not None:
                evidence_entry = evidence_by_id.get(evidence_id)
                if evidence_entry is None:
                    problems.append(
                        f"boat_model {hullq_id} field {pointer}: evidence_id {evidence_id!r} "
                        "not found in reused SLICE-0028 evidence_manifest.json"
                    )
                elif evidence_entry.get("normalized_candidate") != candidate:
                    problems.append(
                        f"boat_model {hullq_id} field {pointer}: sl0028_normalized_candidate "
                        f"{candidate!r} != reused SLICE-0028 evidence "
                        f"{evidence_entry.get('normalized_candidate')!r}"
                    )

        if seen_pointers != ALLOWED_FIELD_POINTERS:
            problems.append(
                f"boat_model {hullq_id}: field pointer coverage {sorted(seen_pointers)!r} != "
                f"the five fixed Tier-1 pointers"
            )

    if found_hullq_ids != expected_hullq_ids:
        problems.append(
            f"wikidata_candidate_applicability hullq_id set {sorted(found_hullq_ids)!r} != "
            f"pilot identity boundary set {sorted(expected_hullq_ids)!r}"
        )
    return problems


# ---------------------------------------------------------------------------
# 6. Deterministic next-step recommendation
# ---------------------------------------------------------------------------


def compute_recommendation(
    *,
    source_use_gate_decisions: Mapping[str, Any],
    boatdesign_applicability: Mapping[str, Any],
    wikidata_candidate_applicability: Mapping[str, Any],
) -> str:
    """Mechanically recompute the slice's single deterministic next-step recommendation."""
    rights_ok = source_use_allowed(
        source_use_gate_decisions, SourceUse.IDENTITY_SEED.value
    ) and source_use_allowed(source_use_gate_decisions, SourceUse.PRODUCTION_VALUE.value)
    if not rights_ok:
        return RecommendationCode.RIGHTS_CLEARANCE_BLOCKED.value

    established_hullq_ids = {
        m["hullq_id"]
        for m in boatdesign_applicability["boat_models"]
        if m["generation_boundary_established_for_this_pilot"]
    }

    for model in wikidata_candidate_applicability["boat_models"]:
        hullq_id = model["hullq_id"]
        if hullq_id not in established_hullq_ids:
            continue
        has_safe_field = any(
            field["outcome"] == ApplicabilityOutcome.SAFE_FOR_LATER_DESIGN_PROMOTION.value
            for field in model["fields"]
        )
        if has_safe_field:
            return RecommendationCode.READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT.value

    return RecommendationCode.APPLICABILITY_EVIDENCE_INSUFFICIENT.value


# ---------------------------------------------------------------------------
# 7. Retained-package artifact-integrity digests
# ---------------------------------------------------------------------------

ARTIFACT_DIGESTS_SCHEMA_VERSION = "sl0029-artifact-digests-v1"
ARTIFACT_DIGESTS_FILENAME = "ARTIFACT-DIGESTS.json"


def retained_package_filenames(package_dir: Path) -> set[str]:
    """Every regular file directly inside *package_dir* except the digest document
    itself, discovered dynamically (never a hardcoded allowlist)."""
    return {
        p.name for p in package_dir.iterdir() if p.is_file() and p.name != ARTIFACT_DIGESTS_FILENAME
    }


def build_artifact_digests(*, generated_at: str, package_dir: Path) -> dict[str, Any]:
    """Build the retained ``ARTIFACT-DIGESTS.json`` document: a SHA256 digest of every
    retained SLICE-0029 package file except the digest document itself."""
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
    """Recompute the SHA256 digest of every file currently in *package_dir* (except
    the digest document itself) and compare against a retained ``ARTIFACT-DIGESTS.json``
    document."""
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
