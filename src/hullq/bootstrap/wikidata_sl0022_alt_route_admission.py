"""Retained alternative-route Tier-0 admission safety pilot — SLICE-0022.

Implements the pure, deterministic classification/materialization logic
described in
``docs/slices/SLICE-0022-retained-alternative-route-tier0-admission-safety-pilot.md``.

This module performs no network acquisition and no database access. Its only
inputs are already-committed, immutable, retained artifacts:

- the accepted SLICE-0017 baseline manifest (1,000 candidates) and the
  accepted SLICE-0018 expansion-delta manifest (829 candidates), combined
  into the complete accepted 1,829-candidate / 1,770-AUTO_ADMIT / 1,772-
  historical-crosswalk direct-discovery identity space;
- the accepted SLICE-0021 retained ``sampled_candidates.json`` (57 candidates:
  53 R1, 0 R2, 4 R3) and ``discovery_probe.json`` (route/incremental/overlap
  cross-check), pinned by exact Git blob SHA1.

Given those retained facts, it:

- fails closed (``ImmutableInputIntegrityError``) before any classification if
  any pinned fingerprint, count or cross-document consistency check does not
  hold exactly;
- classifies each of the 57 retained candidates using the accepted Tier-0
  ``AUTO_ADMIT`` / ``REVIEW_REQUIRED`` / ``NOT_ADMITTED`` vocabulary, reusing
  the accepted ``hullq.domain.identity.generate_search_keys`` search-key
  projection (via ``hullq.bootstrap.wikidata_tier0.search_keys_for_candidate``)
  for collision detection against both the complete 1,829-candidate baseline
  identity space and the other 56 SLICE-0022 candidates;
- forces every structurally usable R3 candidate to ``REVIEW_REQUIRED`` with
  the new ``r3_repair_signal_requires_review`` reason, regardless of its own
  collision status — R3 membership can never itself produce ``AUTO_ADMIT``;
- mints stable opaque HullQ IDs for genuinely new ``AUTO_ADMIT`` candidates
  and reuses the accepted historical QID -> HullQ-ID crosswalk exactly for
  any QID it already maps, failing closed on any conflict;
- materializes the sparse Tier-0 ResearchObservation / ResearchEvidenceBundle
  / CanonicalIdentityAdmission objects needed for PostgreSQL replay, reusing
  ``hullq.bootstrap.wikidata_tier0.build_admission`` unchanged and labeling
  new evidence with the SLICE-0022 activity ID.

Explicitly does NOT:
- perform any live Wikidata (or other) network request;
- regenerate, rewrite or normalize the accepted SLICE-0017/0018/0021 retained
  artifacts;
- infer Brand, Organization, BoatDesign generation, NamedVariant or
  DesignOption identity from any Wikidata statement;
- perform fuzzy/heuristic identity resolution, punctuation rewriting,
  manufacturer-prefix manipulation, token reordering, generation collapsing
  or semantic inference;
- resolve the accepted SLICE-0017/0018 review/non-admitted queues;
- change production Wikidata discovery semantics.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hullq.bootstrap.wikidata_tier0 import (
    BootstrapCandidate,
    BootstrapDecision,
    BootstrapReasonCode,
    CollisionCluster,
    candidate_from_manifest_dict,
    candidate_to_manifest_dict,
    compute_collision_clusters,
    mint_hullq_id,
    validate_crosswalk_consistency,
)
from hullq.bootstrap.wikidata_tier0 import (
    build_bundle as _build_bundle_0017,
)
from hullq.bootstrap.wikidata_tier0_sl0018 import (
    BaselineCollision,
    BaselineSnapshot,
    build_baseline_snapshot_from_manifest,
    compute_baseline_collisions,
    merge_crosswalks_fail_closed,
)
from hullq.research.observations import ResearchEvidenceBundle
from hullq.sources.wikidata import WIKIDATA_SOURCE_ID, WikidataEntityData

__all__ = [
    "ACCEPTED_AUTO_ADMIT_COUNT",
    "ACCEPTED_DIRECT_DISCOVERY_COUNT",
    "ACCEPTED_HISTORICAL_CROSSWALK_COUNT",
    "ACCEPTED_SL0017_MANIFEST_SHA256",
    "ACCEPTED_SL0018_MANIFEST_SHA256",
    "ACCEPTED_SL0021_DISCOVERY_PROBE_BLOB_SHA1",
    "ACCEPTED_SL0021_IMPLEMENTATION_HEAD",
    "ACCEPTED_SL0021_SAMPLED_CANDIDATES_BLOB_SHA1",
    "EXPECTED_R1_COUNT",
    "EXPECTED_R2_COUNT",
    "EXPECTED_R3_COUNT",
    "EXPECTED_TOTAL_CANDIDATES",
    "SL0017_MANIFEST_PATH",
    "SL0018_MANIFEST_PATH",
    "SL0021_DISCOVERY_PROBE_PATH",
    "SL0021_SAMPLED_CANDIDATES_PATH",
    "SL0022_ACTIVITY_ID",
    "SL0022_MANIFEST_VERSION",
    "ImmutableInputIntegrityError",
    "Sl0022Candidate",
    "Sl0022ImmutableInputs",
    "build_bundle",
    "build_sl0022_manifest",
    "classify_sl0022_candidates",
    "git_blob_sha1",
    "load_and_fingerprint_immutable_inputs",
    "sl0022_candidate_from_manifest_dict",
    "sl0022_candidate_to_manifest_dict",
    "verify_sl0022_manifest_self_consistency",
]

# ---------------------------------------------------------------------------
# Fixed identity / bounds
# ---------------------------------------------------------------------------

SL0022_MANIFEST_VERSION = "0022-v1"
SL0022_ACTIVITY_ID = "SLICE-0022-ALT-ROUTE-ADMISSION"

ROOT = Path(__file__).resolve().parents[3]
SL0017_MANIFEST_PATH = ROOT / "research" / "bootstrap" / "wikidata" / "manifest.json"
SL0018_MANIFEST_PATH = (
    ROOT / "research" / "bootstrap" / "wikidata" / "sl0018-2500" / "manifest.json"
)
SL0021_DIR = ROOT / "research" / "bootstrap" / "wikidata" / "sl0021-alt-discovery"
SL0021_SAMPLED_CANDIDATES_PATH = SL0021_DIR / "sampled_candidates.json"
SL0021_DISCOVERY_PROBE_PATH = SL0021_DIR / "discovery_probe.json"

# Accepted immutable retained-input fingerprints (docs/slices/SLICE-0022-*.md
# "Immutable retained inputs"). MUST NOT change; a drifted retained artifact
# fails closed via ImmutableInputIntegrityError before any classification.
ACCEPTED_SL0017_MANIFEST_SHA256 = "076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845"
ACCEPTED_SL0018_MANIFEST_SHA256 = "41ef238c217e31cfbe03329e226a1a3dfff849061df93b8f2523a1e72493821f"

# Exact Git blob SHA1 (``git hash-object``: sha1("blob " + len + "\0" + bytes))
# of the accepted SLICE-0021 retained input files, pinned so a payload change
# that happens to preserve every aggregate count below still fails closed.
ACCEPTED_SL0021_SAMPLED_CANDIDATES_BLOB_SHA1 = "5b56851f0c719b8dcf830fcd0416471c6c60596c"
ACCEPTED_SL0021_DISCOVERY_PROBE_BLOB_SHA1 = "16af426991214c445a3c152aacbe56b8088958d6"

# Informational provenance only (the SLICE-0021 implementation head this
# retained input was produced at) — not independently git-verified here,
# mirroring how wikidata_tier0_sl0018.ACCEPTED_0017_IMPLEMENTATION_HEAD is
# recorded as an audit fact rather than re-derived from git plumbing.
ACCEPTED_SL0021_IMPLEMENTATION_HEAD = "2cf0ab437d2347a574fd5a01b3e5577ca4c6b521"

ACCEPTED_DIRECT_DISCOVERY_COUNT = 1829
ACCEPTED_AUTO_ADMIT_COUNT = 1770
ACCEPTED_HISTORICAL_CROSSWALK_COUNT = 1772

EXPECTED_TOTAL_CANDIDATES = 57
EXPECTED_R1_COUNT = 53
EXPECTED_R2_COUNT = 0
EXPECTED_R3_COUNT = 4


class ImmutableInputIntegrityError(RuntimeError):
    """Raised when a retained SLICE-0017/0018/0021 input artifact no longer
    reproduces its accepted fingerprint/count/cross-document consistency.

    SLICE-0022 MUST fail closed (BLOCKED) rather than silently classify
    against a drifted retained input.
    """


def git_blob_sha1(data: bytes) -> str:
    """The exact Git blob object ID for *data* (what ``git hash-object``
    computes): ``sha1("blob " + len(data) + "\\0" + data)``.
    """
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# Immutable input loading + fingerprinting + cross-document consistency
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Sl0022ImmutableInputs:
    """Every immutable retained fact SLICE-0022 classification depends on,
    loaded and fail-closed-validated once before any classification.
    """

    baseline: BaselineSnapshot
    retained_candidate_rows: tuple[dict[str, Any], ...]
    sl0017_manifest_path: str
    sl0017_sha256: str
    sl0018_manifest_path: str
    sl0018_sha256: str
    sl0021_sampled_candidates_path: str
    sl0021_sampled_candidates_sha1: str
    sl0021_discovery_probe_path: str
    sl0021_discovery_probe_sha1: str


def load_and_fingerprint_immutable_inputs(
    *,
    sl0017_manifest_path: Path = SL0017_MANIFEST_PATH,
    sl0018_manifest_path: Path = SL0018_MANIFEST_PATH,
    sl0021_sampled_candidates_path: Path = SL0021_SAMPLED_CANDIDATES_PATH,
    sl0021_discovery_probe_path: Path = SL0021_DISCOVERY_PROBE_PATH,
) -> Sl0022ImmutableInputs:
    """Load, fingerprint and hard-assert every accepted immutable retained
    input SLICE-0022 depends on, per the controlling slice's "Immutable
    retained inputs" section.

    Fails closed via ``ImmutableInputIntegrityError`` before any
    classification if:

    - either the SLICE-0017 or SLICE-0018 manifest's raw-byte SHA256, or
      either SLICE-0021 retained file's exact Git blob SHA1, no longer
      matches its pinned accepted value;
    - the combined SLICE-0017+0018 direct-discovery identity space is not
      exactly 1,829 candidate QIDs / 1,770 AUTO_ADMIT / 1,772 historical
      crosswalk entries;
    - the retained SLICE-0021 candidate set is not exactly 57 unique QIDs
      split 53 R1 / 0 R2 / 4 R3, with no QID belonging to more than one
      alternative route;
    - the retained SLICE-0021 ``discovery_probe.json`` incremental/overlap
      facts (R1/R2/R3 incremental counts, total union count, zero pairwise
      route overlap) do not exactly corroborate ``sampled_candidates.json``;
    - any retained SLICE-0022 candidate QID is already part of the accepted
      1,829-candidate direct-discovery identity space.

    Never writes to any of the four input files.
    """
    sl0017_bytes = sl0017_manifest_path.read_bytes()
    sl0017_sha256 = hashlib.sha256(sl0017_bytes).hexdigest()
    if sl0017_sha256 != ACCEPTED_SL0017_MANIFEST_SHA256:
        raise ImmutableInputIntegrityError(
            f"Retained SLICE-0017 manifest at {sl0017_manifest_path} failed integrity check: "
            f"sha256={sl0017_sha256!r}, expected {ACCEPTED_SL0017_MANIFEST_SHA256!r}"
        )
    sl0017_manifest = json.loads(sl0017_bytes.decode("utf-8"))

    sl0018_bytes = sl0018_manifest_path.read_bytes()
    sl0018_sha256 = hashlib.sha256(sl0018_bytes).hexdigest()
    if sl0018_sha256 != ACCEPTED_SL0018_MANIFEST_SHA256:
        raise ImmutableInputIntegrityError(
            f"Retained SLICE-0018 manifest at {sl0018_manifest_path} failed integrity check: "
            f"sha256={sl0018_sha256!r}, expected {ACCEPTED_SL0018_MANIFEST_SHA256!r}"
        )
    sl0018_manifest = json.loads(sl0018_bytes.decode("utf-8"))

    sl0017_qids = {row["qid"] for row in sl0017_manifest["candidates"]}
    sl0018_qids = {row["qid"] for row in sl0018_manifest["candidates"]}
    overlap = sl0017_qids & sl0018_qids
    if overlap:
        raise ImmutableInputIntegrityError(
            f"Retained SLICE-0017 baseline and SLICE-0018 delta manifests unexpectedly share "
            f"{len(overlap)} QID(s); the delta must be disjoint from the baseline by construction."
        )

    combined_manifest = {
        "candidates": [*sl0017_manifest["candidates"], *sl0018_manifest["candidates"]],
        # SLICE-0018's own retained_crosswalk is already the complete merged
        # historical registry (accepted SLICE-0017 baseline crosswalk union
        # every retained SLICE-0018 delta mapping) — no further merge needed.
        "retained_crosswalk": sl0018_manifest["retained_crosswalk"],
    }
    baseline = build_baseline_snapshot_from_manifest(
        combined_manifest, manifest_path="<combined SLICE-0017+0018>", sha256=""
    )
    if len(baseline.candidate_qids) != ACCEPTED_DIRECT_DISCOVERY_COUNT:
        raise ImmutableInputIntegrityError(
            "Combined SLICE-0017+0018 direct-discovery candidate count does not equal the "
            f"accepted {ACCEPTED_DIRECT_DISCOVERY_COUNT}: got {len(baseline.candidate_qids)}"
        )
    if len(baseline.auto_admit_qids) != ACCEPTED_AUTO_ADMIT_COUNT:
        raise ImmutableInputIntegrityError(
            "Combined SLICE-0017+0018 AUTO_ADMIT count does not equal the accepted "
            f"{ACCEPTED_AUTO_ADMIT_COUNT}: got {len(baseline.auto_admit_qids)}"
        )
    if len(baseline.crosswalk) != ACCEPTED_HISTORICAL_CROSSWALK_COUNT:
        raise ImmutableInputIntegrityError(
            "Combined SLICE-0017+0018 historical crosswalk count does not equal the accepted "
            f"{ACCEPTED_HISTORICAL_CROSSWALK_COUNT}: got {len(baseline.crosswalk)}"
        )

    sampled_bytes = sl0021_sampled_candidates_path.read_bytes()
    sampled_sha1 = git_blob_sha1(sampled_bytes)
    if sampled_sha1 != ACCEPTED_SL0021_SAMPLED_CANDIDATES_BLOB_SHA1:
        raise ImmutableInputIntegrityError(
            f"Retained SLICE-0021 sampled_candidates.json at {sl0021_sampled_candidates_path} "
            f"failed integrity check: git_blob_sha1={sampled_sha1!r}, expected "
            f"{ACCEPTED_SL0021_SAMPLED_CANDIDATES_BLOB_SHA1!r}"
        )
    sampled_doc = json.loads(sampled_bytes.decode("utf-8"))

    probe_bytes = sl0021_discovery_probe_path.read_bytes()
    probe_sha1 = git_blob_sha1(probe_bytes)
    if probe_sha1 != ACCEPTED_SL0021_DISCOVERY_PROBE_BLOB_SHA1:
        raise ImmutableInputIntegrityError(
            f"Retained SLICE-0021 discovery_probe.json at {sl0021_discovery_probe_path} failed "
            f"integrity check: git_blob_sha1={probe_sha1!r}, expected "
            f"{ACCEPTED_SL0021_DISCOVERY_PROBE_BLOB_SHA1!r}"
        )
    probe_doc = json.loads(probe_bytes.decode("utf-8"))

    rows = sampled_doc["candidates"]
    if len(rows) != EXPECTED_TOTAL_CANDIDATES:
        raise ImmutableInputIntegrityError(
            f"Retained SLICE-0021 sampled_candidates.json candidate count does not equal the "
            f"expected {EXPECTED_TOTAL_CANDIDATES}: got {len(rows)}"
        )
    qids = [row["qid"] for row in rows]
    if len(set(qids)) != len(qids):
        duplicates = sorted({q for q in qids if qids.count(q) > 1})
        raise ImmutableInputIntegrityError(
            f"Retained SLICE-0021 sampled_candidates.json contains duplicate QID(s): {duplicates}"
        )
    for row in rows:
        route_membership = row["route_membership"]
        if route_membership not in (["R1"], ["R3"]):
            raise ImmutableInputIntegrityError(
                f"Retained candidate {row['qid']!r} has unexpected route_membership "
                f"{route_membership!r}; SLICE-0022 requires exactly one of ['R1'] or ['R3'] "
                "per candidate (no QID may belong to more than one alternative route)."
            )
    r1_count = sum(1 for row in rows if row["route_membership"] == ["R1"])
    r3_count = sum(1 for row in rows if row["route_membership"] == ["R3"])
    if r1_count != EXPECTED_R1_COUNT or r3_count != EXPECTED_R3_COUNT:
        raise ImmutableInputIntegrityError(
            f"Retained SLICE-0021 route split does not equal the accepted "
            f"{EXPECTED_R1_COUNT} R1 / {EXPECTED_R3_COUNT} R3: got {r1_count} R1 / {r3_count} R3"
        )

    incremental = probe_doc["incremental"]
    probe_counts = {rid: incremental[rid]["count"] for rid in ("R1", "R2", "R3")}
    expected_probe_counts = {
        "R1": EXPECTED_R1_COUNT,
        "R2": EXPECTED_R2_COUNT,
        "R3": EXPECTED_R3_COUNT,
    }
    if probe_counts != expected_probe_counts:
        raise ImmutableInputIntegrityError(
            f"Retained SLICE-0021 discovery_probe.json incremental route counts "
            f"{probe_counts!r} do not match the expected {expected_probe_counts!r}"
        )
    cross = probe_doc["cross_route_overlap"]
    if cross["total_union_count"] != EXPECTED_TOTAL_CANDIDATES:
        raise ImmutableInputIntegrityError(
            "Retained SLICE-0021 discovery_probe.json cross_route_overlap.total_union_count "
            f"does not equal the expected {EXPECTED_TOTAL_CANDIDATES}: got "
            f"{cross['total_union_count']!r}"
        )
    nonzero_pairwise = [pw for pw in cross["pairwise"] if pw["count"] != 0]
    if nonzero_pairwise:
        raise ImmutableInputIntegrityError(
            "Retained SLICE-0021 discovery_probe.json reports nonzero pairwise alternative-route "
            f"overlap, which SLICE-0022 requires to be exactly zero: {nonzero_pairwise!r}"
        )

    r1_probe_qids = set(incremental["R1"]["qids"])
    r3_probe_qids = set(incremental["R3"]["qids"])
    for row in rows:
        qid = row["qid"]
        if qid in baseline.candidate_qids:
            raise ImmutableInputIntegrityError(
                f"Retained SLICE-0021 candidate {qid!r} is unexpectedly already part of the "
                "accepted 1,829-candidate direct-discovery identity space; SLICE-0022's "
                "candidate universe must be disjoint from it by construction."
            )
        expected_route = "R1" if qid in r1_probe_qids else ("R3" if qid in r3_probe_qids else None)
        if expected_route is None or [expected_route] != row["route_membership"]:
            raise ImmutableInputIntegrityError(
                f"Retained candidate {qid!r} route_membership {row['route_membership']!r} does "
                f"not match its membership in discovery_probe.json's own R1/R3 incremental sets "
                f"(expected {[expected_route] if expected_route else None!r})."
            )

    return Sl0022ImmutableInputs(
        baseline=baseline,
        retained_candidate_rows=tuple(rows),
        sl0017_manifest_path=_repo_relative(sl0017_manifest_path),
        sl0017_sha256=sl0017_sha256,
        sl0018_manifest_path=_repo_relative(sl0018_manifest_path),
        sl0018_sha256=sl0018_sha256,
        sl0021_sampled_candidates_path=_repo_relative(sl0021_sampled_candidates_path),
        sl0021_sampled_candidates_sha1=sampled_sha1,
        sl0021_discovery_probe_path=_repo_relative(sl0021_discovery_probe_path),
        sl0021_discovery_probe_sha1=probe_sha1,
    )


# ---------------------------------------------------------------------------
# Sl0022Candidate — a retained BootstrapCandidate plus its SLICE-0021 route
# membership. Composition (not inheritance) so the accepted
# BootstrapCandidate validation/round-trip is reused unchanged, and so
# hullq.bootstrap.wikidata_tier0.build_bundle/build_admission (which duck-type
# on a BootstrapCandidate's own attributes) apply unmodified to ``.base``.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Sl0022Candidate:
    """One retained SLICE-0022 candidate: an accepted-shape
    ``BootstrapCandidate`` plus which SLICE-0021 alternative route(s) it
    belongs to (exactly one of ``("R1",)`` or ``("R3",)`` for every candidate
    in the accepted retained set).
    """

    base: BootstrapCandidate
    route_membership: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "route_membership", tuple(self.route_membership))
        if self.route_membership not in (("R1",), ("R3",)):
            raise ValueError(
                f"Sl0022Candidate.route_membership must be exactly ('R1',) or ('R3',); got "
                f"{self.route_membership!r}"
            )


def sl0022_candidate_to_manifest_dict(candidate: Sl0022Candidate) -> dict[str, Any]:
    """Convert a Sl0022Candidate to a JSON-serializable manifest row."""
    return {
        **candidate_to_manifest_dict(candidate.base),
        "route_membership": list(candidate.route_membership),
    }


def sl0022_candidate_from_manifest_dict(row: dict[str, Any]) -> Sl0022Candidate:
    """Reconstruct a Sl0022Candidate from a retained manifest row.

    Deterministic and offline: performs no network access and does not mint
    a new HullQ ID.
    """
    base_row = {k: v for k, v in row.items() if k != "route_membership"}
    return Sl0022Candidate(
        base=candidate_from_manifest_dict(base_row),
        route_membership=tuple(row["route_membership"]),
    )


# ---------------------------------------------------------------------------
# Classification — pure, deterministic, no network/database access
# ---------------------------------------------------------------------------


def build_bundle(candidate: Sl0022Candidate) -> ResearchEvidenceBundle | None:
    """SLICE-0022 bundle builder.

    Thin wrapper over the accepted ``build_bundle`` that labels the produced
    ``ResearchObservation``/``ResearchEvidenceBundle`` with the genuine
    SLICE-0022 ``activity_id`` instead of the SLICE-0017 default, so this
    evidence is not misattributed to the SLICE-0017 bootstrap run.
    """
    return _build_bundle_0017(candidate.base, activity_id=SL0022_ACTIVITY_ID)


def classify_sl0022_candidates(
    retained_rows: Sequence[dict[str, Any]],
    *,
    retrieved_at: str,
    baseline: BaselineSnapshot,
    id_factory: Any = mint_hullq_id,
    existing_crosswalk: dict[str, str] | None = None,
) -> tuple[list[Sl0022Candidate], list[CollisionCluster], dict[str, BaselineCollision]]:
    """Deterministically classify the retained SLICE-0022 candidate rows.

    Each *retained_rows* entry MUST carry ``qid``, ``route_membership``
    (exactly ``["R1"]`` or ``["R3"]``), ``label`` and ``aliases`` — the exact
    shape of a ``sampled_candidates.json`` candidate row.

    Reuses the accepted SLICE-0017/0018 collision machinery unmodified:

    - ``compute_collision_clusters`` for same-search-key collisions among the
      57 SLICE-0022 candidates themselves ("within-57" collisions);
    - ``compute_baseline_collisions`` for same-search-key collisions against
      the complete accepted 1,829-candidate baseline identity space (covering
      baseline AUTO_ADMIT and REVIEW_REQUIRED candidates alike, since both
      retain a usable label).

    Decision rules, in order:

    1. no usable retained label -> ``NOT_ADMITTED`` / ``missing_label``
       (matches accepted Tier-0 semantics exactly; applies to both R1 and R3
       candidates uniformly — R3 membership does not exempt a label-less
       candidate from this rule, nor does it change its result).
    2. R3 membership (route_membership == ("R3",)) with a usable label ->
       always ``REVIEW_REQUIRED`` / ``r3_repair_signal_requires_review``,
       regardless of collision status. R3 candidates never reach the
       collision check below and can never become ``AUTO_ADMIT``.
    3. collision against the baseline identity space OR against another of
       the 57 candidates -> ``REVIEW_REQUIRED`` / ``name_collision``.
    4. otherwise -> ``AUTO_ADMIT`` / ``ok``, reusing an already-retained
       HullQ ID from *existing_crosswalk* exactly if present, else minting a
       new one via *id_factory*.

    ``existing_crosswalk`` (typically the combined baseline crosswalk merged
    with any already-minted SLICE-0022 IDs from a prior run) is reused
    exactly for any QID it already maps — never silently reminted.

    Fails closed via ``ValueError`` before any classification if any row's
    QID is already part of *baseline*'s 1,829-candidate identity space (a
    defense-in-depth repeat of the check already performed by
    ``load_and_fingerprint_immutable_inputs``, so a caller that constructs
    *retained_rows* by another path still cannot silently reclassify a
    baseline QID).
    """
    entities = [
        WikidataEntityData(
            qid=row["qid"],
            label=row.get("label"),
            aliases=list(row.get("aliases") or ()),
            raw_claims={},
        )
        for row in retained_rows
    ]
    route_by_qid: dict[str, tuple[str, ...]] = {
        row["qid"]: tuple(row["route_membership"]) for row in retained_rows
    }

    already_in_baseline = [e.qid for e in entities if e.qid in baseline.candidate_qids]
    if already_in_baseline:
        raise ValueError(
            "classify_sl0022_candidates received QID(s) already present in the accepted "
            f"1,829-candidate baseline identity space, which MUST NOT be reclassified: "
            f"{sorted(already_in_baseline)}"
        )

    crosswalk = dict(existing_crosswalk or {})
    within_57_clusters = compute_collision_clusters(entities)
    within_57_colliding_qids = {qid for cluster in within_57_clusters for qid in cluster.qids}
    baseline_collisions = compute_baseline_collisions(entities, baseline)

    candidates: list[Sl0022Candidate] = []
    for entity in entities:
        qid = entity.qid
        label = entity.label
        route_membership = route_by_qid[qid]
        retained_id = crosswalk.get(qid)

        if not label:
            base = BootstrapCandidate(
                qid=qid,
                retrieved_at=retrieved_at,
                preferred_label=None,
                aliases=tuple(entity.aliases),
                hullq_id=retained_id,
                decision=BootstrapDecision.NOT_ADMITTED,
                reason_codes=(BootstrapReasonCode.MISSING_LABEL,),
                observation_id=None,
                bundle_id=None,
                bundle_version=None,
                evidence_link_id=None,
            )
            candidates.append(Sl0022Candidate(base=base, route_membership=route_membership))
            continue

        observation_id = f"OBS-WD-TIER0-{qid}"
        bundle_id = f"BUNDLE-WD-TIER0-{qid}"
        bundle_version = "1"

        if route_membership == ("R3",):
            base = BootstrapCandidate(
                qid=qid,
                retrieved_at=retrieved_at,
                preferred_label=label,
                aliases=tuple(entity.aliases),
                hullq_id=retained_id,
                decision=BootstrapDecision.REVIEW_REQUIRED,
                reason_codes=(BootstrapReasonCode.R3_REPAIR_SIGNAL_REQUIRES_REVIEW,),
                observation_id=observation_id,
                bundle_id=bundle_id,
                bundle_version=bundle_version,
                evidence_link_id=None,
            )
            candidates.append(Sl0022Candidate(base=base, route_membership=route_membership))
            continue

        if qid in baseline_collisions or qid in within_57_colliding_qids:
            base = BootstrapCandidate(
                qid=qid,
                retrieved_at=retrieved_at,
                preferred_label=label,
                aliases=tuple(entity.aliases),
                hullq_id=retained_id,
                decision=BootstrapDecision.REVIEW_REQUIRED,
                reason_codes=(BootstrapReasonCode.NAME_COLLISION,),
                observation_id=observation_id,
                bundle_id=bundle_id,
                bundle_version=bundle_version,
                evidence_link_id=None,
            )
            candidates.append(Sl0022Candidate(base=base, route_membership=route_membership))
            continue

        hullq_id = retained_id if retained_id is not None else id_factory()
        crosswalk[qid] = hullq_id
        base = BootstrapCandidate(
            qid=qid,
            retrieved_at=retrieved_at,
            preferred_label=label,
            aliases=tuple(entity.aliases),
            hullq_id=hullq_id,
            decision=BootstrapDecision.AUTO_ADMIT,
            reason_codes=(BootstrapReasonCode.OK,),
            observation_id=observation_id,
            bundle_id=bundle_id,
            bundle_version=bundle_version,
            evidence_link_id=f"LINK-WD-TIER0-{qid}",
        )
        candidates.append(Sl0022Candidate(base=base, route_membership=route_membership))

    return candidates, within_57_clusters, baseline_collisions


# ---------------------------------------------------------------------------
# Manifest (de)serialization — JSON-primitive
# ---------------------------------------------------------------------------


def build_sl0022_manifest(
    candidates: list[Sl0022Candidate],
    *,
    generated_at: str,
    baseline: BaselineSnapshot,
    within_57_clusters: list[CollisionCluster],
    baseline_collisions: dict[str, BaselineCollision],
    inputs: Sl0022ImmutableInputs,
    retrieval_count: int = 0,
    extracted_record_count: int = 0,
    acquired_at: str | None = None,
    classification_recomputed_at: str | None = None,
    historical_crosswalk: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the full versioned, JSON-serializable SLICE-0022 manifest.

    Fails closed via ``ValueError`` before returning anything if:

    - *candidates* is not exactly the expected 57-candidate universe split
      53 R1 / 4 R3;
    - any R3 candidate is ``AUTO_ADMIT`` (the R3 fail-closed rule);
    - the current candidate set's own QID -> HullQ-ID mappings are internally
      inconsistent, or conflict with *historical_crosswalk* (both checked via
      the accepted ``validate_crosswalk_consistency`` /
      ``merge_crosswalks_fail_closed`` machinery).

    ``historical_crosswalk`` is the full historical QID -> HullQ-ID registry
    accumulated across every prior run (the combined SLICE-0017+0018 baseline
    crosswalk merged with any already-retained SLICE-0022 mapping from a
    prior classification pass). It defaults to ``baseline.crosswalk`` alone,
    which is correct for the very first SLICE-0022 classification pass.
    """
    if len(candidates) != EXPECTED_TOTAL_CANDIDATES:
        raise ValueError(
            f"SLICE-0022 candidate set must contain exactly {EXPECTED_TOTAL_CANDIDATES} "
            f"candidates; got {len(candidates)}"
        )
    r1_candidates = [c for c in candidates if c.route_membership == ("R1",)]
    r3_candidates = [c for c in candidates if c.route_membership == ("R3",)]
    if len(r1_candidates) != EXPECTED_R1_COUNT or len(r3_candidates) != EXPECTED_R3_COUNT:
        raise ValueError(
            f"SLICE-0022 candidate route split must be exactly {EXPECTED_R1_COUNT} R1 / "
            f"{EXPECTED_R3_COUNT} R3; got {len(r1_candidates)} R1 / {len(r3_candidates)} R3"
        )
    r3_auto_admitted = [c for c in r3_candidates if c.base.decision == BootstrapDecision.AUTO_ADMIT]
    if r3_auto_admitted:
        raise ValueError(
            "R3 fail-closed rule violated: the following R3 candidate(s) were classified "
            f"AUTO_ADMIT, which SLICE-0022 MUST NEVER permit: "
            f"{sorted(c.base.qid for c in r3_auto_admitted)}"
        )

    bases = [c.base for c in candidates]
    validate_crosswalk_consistency(bases)
    current_crosswalk = {
        c.base.qid: c.base.hullq_id for c in candidates if c.base.hullq_id is not None
    }
    historical = historical_crosswalk if historical_crosswalk is not None else baseline.crosswalk
    full_crosswalk = merge_crosswalks_fail_closed(
        historical,
        current_crosswalk,
        context="historical crosswalk merge with SLICE-0022 candidates",
    )

    reason_breakdown: dict[str, int] = {}
    for c in candidates:
        for reason in c.base.reason_codes:
            reason_breakdown[str(reason)] = reason_breakdown.get(str(reason), 0) + 1

    auto_admit = sum(1 for c in candidates if c.base.decision == BootstrapDecision.AUTO_ADMIT)
    review_required = sum(
        1 for c in candidates if c.base.decision == BootstrapDecision.REVIEW_REQUIRED
    )
    not_admitted = sum(1 for c in candidates if c.base.decision == BootstrapDecision.NOT_ADMITTED)
    auto_admit_r1 = sum(1 for c in r1_candidates if c.base.decision == BootstrapDecision.AUTO_ADMIT)

    newly_minted_id_count = sum(
        1 for c in candidates if c.base.hullq_id is not None and c.base.qid not in historical
    )
    reused_historical_id_count = sum(
        1 for c in candidates if c.base.hullq_id is not None and c.base.qid in historical
    )

    return {
        "manifest_version": SL0022_MANIFEST_VERSION,
        "source_id": WIKIDATA_SOURCE_ID,
        "generated_at": generated_at,
        "acquired_at": acquired_at if acquired_at is not None else generated_at,
        "classification_recomputed_at": classification_recomputed_at,
        "immutable_inputs": {
            "sl0017_manifest": {
                "path": inputs.sl0017_manifest_path,
                "sha256": inputs.sl0017_sha256,
            },
            "sl0018_manifest": {
                "path": inputs.sl0018_manifest_path,
                "sha256": inputs.sl0018_sha256,
            },
            "sl0021_sampled_candidates": {
                "path": inputs.sl0021_sampled_candidates_path,
                "git_blob_sha1": inputs.sl0021_sampled_candidates_sha1,
            },
            "sl0021_discovery_probe": {
                "path": inputs.sl0021_discovery_probe_path,
                "git_blob_sha1": inputs.sl0021_discovery_probe_sha1,
            },
            "sl0021_implementation_head": ACCEPTED_SL0021_IMPLEMENTATION_HEAD,
            "retained_direct_discovery_count": len(baseline.candidate_qids),
            "accepted_auto_admit_count": len(baseline.auto_admit_qids),
            "accepted_historical_crosswalk_count": len(baseline.crosswalk),
        },
        "candidate_universe": {
            "total": len(candidates),
            "r1_count": len(r1_candidates),
            "r2_count": 0,
            "r3_count": len(r3_candidates),
        },
        "usage_metrics": {
            "retrieval_count": retrieval_count,
            "extracted_record_count": extracted_record_count,
        },
        "candidates": [sl0022_candidate_to_manifest_dict(c) for c in candidates],
        "retained_crosswalk": [
            {"qid": qid, "hullq_id": hullq_id} for qid, hullq_id in sorted(full_crosswalk.items())
        ],
        "collisions": {
            "baseline": [
                {
                    "candidate_qid": bc.delta_qid,
                    "baseline_qids": list(bc.baseline_qids),
                    "shared_keys": list(bc.shared_keys),
                }
                for bc in sorted(baseline_collisions.values(), key=lambda b: b.delta_qid)
            ],
            "within_57": [
                {"qids": list(c.qids), "shared_keys": list(c.shared_keys)}
                for c in within_57_clusters
            ],
        },
        "counts": {
            "candidates_processed": len(candidates),
            "auto_admit": auto_admit,
            "auto_admit_r1": auto_admit_r1,
            "auto_admit_r3": 0,
            "review_required": review_required,
            "not_admitted": not_admitted,
            "reason_breakdown": reason_breakdown,
            "baseline_collision_count": len(baseline_collisions),
            "within_57_collision_cluster_count": len(within_57_clusters),
            "historical_crosswalk_count_before": len(historical),
            "retained_crosswalk_count": len(full_crosswalk),
            "newly_minted_id_count": newly_minted_id_count,
            "reused_historical_id_count": reused_historical_id_count,
            "research_observation_count": sum(
                1 for c in candidates if c.base.observation_id is not None
            ),
            "canonical_evidence_link_count": sum(
                1 for c in candidates if c.base.evidence_link_id is not None
            ),
            "accepted_baseline_canonical_boat_model_count": len(baseline.auto_admit_qids),
            "combined_canonical_boat_model_count_expected": len(baseline.auto_admit_qids)
            + auto_admit,
        },
    }


# ---------------------------------------------------------------------------
# Offline self-consistency verification of an already-retained manifest
# ---------------------------------------------------------------------------


def verify_sl0022_manifest_self_consistency(
    manifest: dict[str, Any], *, inputs: Sl0022ImmutableInputs
) -> list[str]:
    """Recompute the entire retained SLICE-0022 manifest from *inputs*
    (freshly loaded/fingerprinted immutable retained facts) and the
    manifest's OWN retained ``retained_crosswalk``, and return a list of
    human-readable mismatch descriptions (empty == fully self-consistent).

    Recomputation reuses the manifest's own retained HullQ-ID assignments via
    ``existing_crosswalk`` (so legitimate ID reuse across runs never counts as
    a mismatch) and independently re-derives every other field: per-candidate
    decision/reason codes/route membership/observation/bundle/evidence-link
    IDs, collision memberships (baseline and within-57), aggregate counts,
    and the R3-never-``AUTO_ADMIT`` invariant — never trusting the manifest's
    own already-computed summary fields as ground truth for themselves.
    """
    mismatches: list[str] = []

    retained_rows = manifest.get("candidates", [])
    retrieved_at_values = {row["retrieved_at"] for row in retained_rows}
    if len(retrieved_at_values) != 1:
        mismatches.append(
            "manifest.candidates do not share one uniform retrieved_at timestamp; cannot "
            "deterministically recompute"
        )
        return mismatches
    retrieved_at = next(iter(retrieved_at_values))

    retained_crosswalk = {
        row["qid"]: row["hullq_id"] for row in manifest.get("retained_crosswalk", [])
    }

    recomputed_candidates, within_57_clusters, baseline_collisions = classify_sl0022_candidates(
        list(inputs.retained_candidate_rows),
        retrieved_at=retrieved_at,
        baseline=inputs.baseline,
        existing_crosswalk=retained_crosswalk,
    )

    recomputed_by_qid = {c.base.qid: c for c in recomputed_candidates}
    retained_by_qid = {row["qid"]: row for row in retained_rows}

    if set(recomputed_by_qid) != set(retained_by_qid):
        mismatches.append(
            f"candidate QID set mismatch: recomputed={sorted(recomputed_by_qid)!r} != "
            f"retained={sorted(retained_by_qid)!r}"
        )

    for qid, recomputed in recomputed_by_qid.items():
        retained_row = retained_by_qid.get(qid)
        if retained_row is None:
            continue
        expected_row = sl0022_candidate_to_manifest_dict(recomputed)
        compared_fields = (
            "route_membership",
            "preferred_label",
            "aliases",
            "hullq_id",
            "decision",
            "reason_codes",
            "observation_id",
            "bundle_id",
            "bundle_version",
            "evidence_link_id",
        )
        mismatches.extend(
            f"candidate[{qid}].{field}={retained_row.get(field)!r} != recomputed "
            f"{expected_row.get(field)!r}"
            for field in compared_fields
            if retained_row.get(field) != expected_row.get(field)
        )

    # R3-never-AUTO_ADMIT invariant, re-checked directly against the retained
    # document (defense-in-depth: not merely implied by the field-by-field
    # comparison above, which already would have flagged the decision).
    mismatches.extend(
        f"candidate[{row.get('qid')}] is R3 and AUTO_ADMIT, which the R3 fail-closed "
        "rule must never permit"
        for row in retained_rows
        if row.get("route_membership") == ["R3"] and row.get("decision") == "auto_admit"
    )

    expected_baseline_collision_qids = set(baseline_collisions)
    retained_baseline_collision_qids = {
        entry["candidate_qid"] for entry in manifest.get("collisions", {}).get("baseline", [])
    }
    if expected_baseline_collision_qids != retained_baseline_collision_qids:
        mismatches.append(
            "collisions.baseline candidate-QID set does not match recomputed baseline collisions: "
            f"retained={sorted(retained_baseline_collision_qids)!r} != recomputed="
            f"{sorted(expected_baseline_collision_qids)!r}"
        )

    expected_within_57_clusters = {c.qids for c in within_57_clusters}
    retained_within_57_clusters = {
        tuple(entry["qids"]) for entry in manifest.get("collisions", {}).get("within_57", [])
    }
    if expected_within_57_clusters != retained_within_57_clusters:
        mismatches.append(
            "collisions.within_57 cluster set does not match recomputed within-57 clusters: "
            f"retained={sorted(retained_within_57_clusters)!r} != recomputed="
            f"{sorted(expected_within_57_clusters)!r}"
        )

    recomputed_counts = {
        "candidates_processed": len(recomputed_candidates),
        "auto_admit": sum(
            1 for c in recomputed_candidates if c.base.decision == BootstrapDecision.AUTO_ADMIT
        ),
        "review_required": sum(
            1 for c in recomputed_candidates if c.base.decision == BootstrapDecision.REVIEW_REQUIRED
        ),
        "not_admitted": sum(
            1 for c in recomputed_candidates if c.base.decision == BootstrapDecision.NOT_ADMITTED
        ),
    }
    retained_counts = manifest.get("counts", {})
    for key, expected in recomputed_counts.items():
        if retained_counts.get(key) != expected:
            mismatches.append(
                f"counts.{key}={retained_counts.get(key)!r} != recomputed {expected!r}"
            )

    expected_combined = len(inputs.baseline.auto_admit_qids) + recomputed_counts["auto_admit"]
    if retained_counts.get("combined_canonical_boat_model_count_expected") != expected_combined:
        mismatches.append(
            "counts.combined_canonical_boat_model_count_expected="
            f"{retained_counts.get('combined_canonical_boat_model_count_expected')!r} != "
            f"recomputed {expected_combined!r}"
        )

    immutable_inputs = manifest.get("immutable_inputs", {})
    expected_immutable_counts = {
        "retained_direct_discovery_count": len(inputs.baseline.candidate_qids),
        "accepted_auto_admit_count": len(inputs.baseline.auto_admit_qids),
        "accepted_historical_crosswalk_count": len(inputs.baseline.crosswalk),
    }
    for key, expected in expected_immutable_counts.items():
        if immutable_inputs.get(key) != expected:
            mismatches.append(
                f"immutable_inputs.{key}={immutable_inputs.get(key)!r} != actual loaded "
                f"{expected!r}"
            )
    if (
        immutable_inputs.get("sl0021_sampled_candidates", {}).get("git_blob_sha1")
        != inputs.sl0021_sampled_candidates_sha1
    ):
        mismatches.append("immutable_inputs.sl0021_sampled_candidates.git_blob_sha1 mismatch")
    if (
        immutable_inputs.get("sl0021_discovery_probe", {}).get("git_blob_sha1")
        != inputs.sl0021_discovery_probe_sha1
    ):
        mismatches.append("immutable_inputs.sl0021_discovery_probe.git_blob_sha1 mismatch")

    candidate_universe = manifest.get("candidate_universe", {})
    expected_universe = {
        "total": EXPECTED_TOTAL_CANDIDATES,
        "r1_count": EXPECTED_R1_COUNT,
        "r2_count": EXPECTED_R2_COUNT,
        "r3_count": EXPECTED_R3_COUNT,
    }
    for key, expected in expected_universe.items():
        if candidate_universe.get(key) != expected:
            mismatches.append(
                f"candidate_universe.{key}={candidate_universe.get(key)!r} != expected {expected!r}"
            )

    return mismatches
