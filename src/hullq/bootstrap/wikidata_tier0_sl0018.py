"""Controlled Wikidata Tier-0 2,500-window expansion — SLICE-0018.

Implements the baseline-preserving expansion-delta logic described in
``docs/slices/SLICE-0018-controlled-wikidata-tier0-2500-window-expansion.md``.

This module is pure logic: it performs no network acquisition (that remains
in ``hullq.sources.wikidata``) and no database access (that remains in
``hullq.persistence``). It builds on — and never duplicates — the accepted
SLICE-0017 classification/materialization primitives in
``hullq.bootstrap.wikidata_tier0`` (``BootstrapCandidate``,
``compute_collision_clusters``, ``search_keys_for_candidate``,
``build_bundle``, ``build_admission``, ``mint_hullq_id``).

Four structurally separate concepts are modeled explicitly and MUST NOT be
conflated (see the controlling slice's "Critical state model"):

A. the accepted SLICE-0017 baseline (``BaselineSnapshot``) — immutable input;
B. the historical retained QID -> HullQ-ID crosswalk — identity history, not
   a decision list;
C. the current SLICE-0018 discovery window — what the source returned now;
D. the SLICE-0018 expansion delta — discovery window minus all 1,000
   baseline candidate QIDs; only delta QIDs receive new decisions here.

Explicitly does NOT:
- rewrite or reclassify any accepted SLICE-0017 baseline candidate;
- infer Brand, Organization, BoatDesign generation, NamedVariant or
  DesignOption identity from any Wikidata statement;
- perform fuzzy/heuristic identity resolution or forced merge/split;
- resolve the accepted SLICE-0017 review/non-admitted queue.
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
    _collapse_qid_id_pairs_fail_closed,
    candidate_to_manifest_dict,
    compute_collision_clusters,
    load_crosswalk_from_manifest,
    mint_hullq_id,
    search_keys_for_candidate,
    validate_crosswalk_consistency,
)
from hullq.bootstrap.wikidata_tier0 import (
    build_bundle as _build_bundle_0017,
)
from hullq.research.observations import ResearchEvidenceBundle
from hullq.sources.wikidata import (
    BOOTSTRAP_ENTITY_API_ENDPOINT,
    BOOTSTRAP_ENTITY_API_VERSION,
    BOOTSTRAP_SPARQL_ENDPOINT,
    BOOTSTRAP_SPARQL_QUERY_VERSION,
    WIKIDATA_SOURCE_ID,
    WikidataEntityData,
)

__all__ = [
    "ACCEPTED_0017_ADMISSIONS",
    "ACCEPTED_0017_BASELINE_CANDIDATE_COUNT",
    "ACCEPTED_0017_BUNDLES_ON_REPLAY",
    "ACCEPTED_0017_IMPLEMENTATION_HEAD",
    "ACCEPTED_0017_MANIFEST_SHA256",
    "ACCEPTED_0017_MANIFEST_VERSION",
    "ACCEPTED_0017_NOT_ADMITTED",
    "ACCEPTED_0017_RETAINED_CROSSWALK_COUNT",
    "ACCEPTED_0017_REVIEW_REQUIRED",
    "BASELINE_MANIFEST_PATH",
    "BOOTSTRAP_REQUESTED_LIMIT_SL0018",
    "BOOTSTRAP_SAFETY_CEILING_SL0018",
    "SL0018_ACTIVITY_ID",
    "SL0018_MANIFEST_VERSION",
    "BaselineCollision",
    "BaselineIntegrityError",
    "BaselineSnapshot",
    "DeltaCompletenessError",
    "build_baseline_snapshot_from_manifest",
    "build_bundle",
    "build_sl0018_manifest",
    "classify_delta_candidates",
    "compute_baseline_absent_qids",
    "compute_baseline_collisions",
    "compute_expansion_delta",
    "load_baseline_snapshot",
    "merge_crosswalks_fail_closed",
    "verify_delta_candidate_completeness",
    "verify_entity_acquisition_completeness",
]

# ---------------------------------------------------------------------------
# SLICE-0018 bounds — mirrors the accepted candidate-set boundary contract.
# ---------------------------------------------------------------------------

BOOTSTRAP_REQUESTED_LIMIT_SL0018 = 2500
BOOTSTRAP_SAFETY_CEILING_SL0018 = 3000

SL0018_MANIFEST_VERSION = "0018-v1"
SL0018_ACTIVITY_ID = "SLICE-0018-EXPANSION-BOOTSTRAP"

ROOT = Path(__file__).resolve().parents[3]
BASELINE_MANIFEST_PATH = ROOT / "research" / "bootstrap" / "wikidata" / "manifest.json"

# Accepted SLICE-0017 baseline replay constants (docs/slices/SLICE-0018-*.md
# "Baseline replay constants"). SLICE-0018 fails closed if the retained
# baseline artifact no longer reproduces these before delta work proceeds.
ACCEPTED_0017_MANIFEST_VERSION = "0017-v4"
ACCEPTED_0017_IMPLEMENTATION_HEAD = "34c2de8fc99ab6babad054a4186cee168cc3a2da"
ACCEPTED_0017_BASELINE_CANDIDATE_COUNT = 1000
ACCEPTED_0017_BUNDLES_ON_REPLAY = 985
ACCEPTED_0017_ADMISSIONS = 965
ACCEPTED_0017_RETAINED_CROSSWALK_COUNT = 967
ACCEPTED_0017_REVIEW_REQUIRED = 20
ACCEPTED_0017_NOT_ADMITTED = 15

# Exact raw-byte SHA256 of the accepted SLICE-0017 retained manifest
# (research/bootstrap/wikidata/manifest.json), pinned so a payload/QID/ID/
# alias change that happens to preserve every aggregate count above still
# fails closed. This is the primary integrity check; the aggregate-count
# checks above remain as additional diagnostics, not a substitute for it.
ACCEPTED_0017_MANIFEST_SHA256 = "076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845"


def build_bundle(candidate: BootstrapCandidate) -> ResearchEvidenceBundle | None:
    """SLICE-0018 delta bundle builder.

    Thin wrapper over the accepted SLICE-0017 ``build_bundle`` that labels
    the produced ``ResearchObservation``/``ResearchEvidenceBundle`` with the
    genuine SLICE-0018 ``activity_id`` instead of the SLICE-0017 default, so
    delta evidence is not misattributed to the SLICE-0017 bootstrap run.
    """
    return _build_bundle_0017(candidate, activity_id=SL0018_ACTIVITY_ID)


class DeltaCompletenessError(RuntimeError):
    """Raised when an acquired/classified/assembled SLICE-0018 expansion
    delta does not exactly correspond to its expected bounded definition.

    Covers every way a delta candidate set could silently drop, duplicate or
    misattribute a QID: an incomplete Wikidata entity-acquisition response, a
    baseline QID accidentally supplied as delta input, a duplicate delta
    entity QID, or a final candidate set that does not exactly equal
    ``discovery_window_qids`` minus the accepted baseline. SLICE-0018 MUST
    fail closed rather than silently persist a partial/incorrect delta.
    """


# ---------------------------------------------------------------------------
# A. Accepted SLICE-0017 baseline — loaded, validated, immutable input
# ---------------------------------------------------------------------------


class BaselineIntegrityError(RuntimeError):
    """Raised when the retained SLICE-0017 baseline artifact no longer
    reproduces its accepted semantics.

    SLICE-0018 MUST fail closed (BLOCKED) rather than silently proceed
    against a baseline artifact that has drifted from the accepted state
    recorded in the controlling slice's "Baseline replay constants".
    """


@dataclass(frozen=True)
class BaselineSnapshot:
    """The accepted SLICE-0017 baseline as loaded and validated for SLICE-0018.

    Immutable input to every SLICE-0018 computation: nothing in this module
    ever writes back to the baseline manifest file, and no baseline QID's
    decision is ever recomputed here.
    """

    manifest_path: str
    manifest_version: str
    sha256: str
    candidate_qids: frozenset[str]
    search_key_owners: dict[str, frozenset[str]]
    crosswalk: dict[str, str]
    auto_admit_qids: frozenset[str]
    review_required_qids: frozenset[str]
    not_admitted_qids: frozenset[str]


def load_baseline_snapshot(manifest_path: Path = BASELINE_MANIFEST_PATH) -> BaselineSnapshot:
    """Load and validate the accepted SLICE-0017 baseline manifest.

    Performs no network access and never mutates *manifest_path*. Fails
    closed via ``BaselineIntegrityError`` if the retained baseline no longer
    reproduces the accepted SLICE-0017 semantics. The primary check is an
    exact raw-byte SHA256 comparison against ``ACCEPTED_0017_MANIFEST_SHA256``
    — a payload/QID/ID/alias change that happens to preserve every aggregate
    count below would otherwise pass undetected. The manifest-version and
    aggregate-count checks remain as additional diagnostics (a more specific
    failure message than a bare hash mismatch), not a substitute for the
    fingerprint. Also fails closed via ``CrosswalkConflictError`` (propagated
    from ``load_crosswalk_from_manifest``) if the baseline's own retained
    crosswalk is internally inconsistent, and via ``BaselineIntegrityError``
    if any candidate QID appears more than once.
    """
    raw_bytes = manifest_path.read_bytes()
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    manifest = json.loads(raw_bytes.decode("utf-8"))

    def _fail(msg: str) -> None:
        raise BaselineIntegrityError(
            f"Retained SLICE-0017 baseline at {manifest_path} failed integrity check: {msg}"
        )

    if sha256 != ACCEPTED_0017_MANIFEST_SHA256:
        _fail(f"sha256={sha256!r}, expected {ACCEPTED_0017_MANIFEST_SHA256!r}")

    if manifest.get("manifest_version") != ACCEPTED_0017_MANIFEST_VERSION:
        _fail(
            f"manifest_version={manifest.get('manifest_version')!r}, expected "
            f"{ACCEPTED_0017_MANIFEST_VERSION!r}"
        )

    rows = manifest.get("candidates", [])
    if len(rows) != ACCEPTED_0017_BASELINE_CANDIDATE_COUNT:
        _fail(f"candidate count={len(rows)}, expected {ACCEPTED_0017_BASELINE_CANDIDATE_COUNT}")

    counts = manifest.get("counts", {})
    expected_counts = {
        "auto_admit": ACCEPTED_0017_ADMISSIONS,
        "review_required": ACCEPTED_0017_REVIEW_REQUIRED,
        "not_admitted": ACCEPTED_0017_NOT_ADMITTED,
        "retained_crosswalk_count": ACCEPTED_0017_RETAINED_CROSSWALK_COUNT,
        "research_observation_count": ACCEPTED_0017_BUNDLES_ON_REPLAY,
        "canonical_evidence_link_count": ACCEPTED_0017_ADMISSIONS,
    }
    for key, expected in expected_counts.items():
        actual = counts.get(key)
        if actual != expected:
            _fail(f"counts.{key}={actual!r}, expected {expected!r}")

    # Explicit duplicate-candidate-QID detection and internal
    # crosswalk-inconsistency detection both fail closed inside
    # build_baseline_snapshot_from_manifest / the crosswalk loader it calls.
    return build_baseline_snapshot_from_manifest(
        manifest, manifest_path=str(manifest_path), sha256=sha256
    )


def build_baseline_snapshot_from_manifest(
    manifest: dict[str, Any], *, manifest_path: str = "<in-memory>", sha256: str = ""
) -> BaselineSnapshot:
    """Build a ``BaselineSnapshot`` from an already-parsed manifest dict, with
    NO accepted-constant/fingerprint integrity enforcement (that is
    ``load_baseline_snapshot``'s job for the real retained SLICE-0017
    artifact).

    Used internally by ``load_baseline_snapshot`` and directly by tests that
    exercise the baseline-first/delta-second replay mechanism against a
    small synthetic baseline rather than the full accepted 1,000-candidate
    artifact. Still fails closed via ``CrosswalkConflictError`` if the
    manifest's own retained crosswalk is internally inconsistent, and via
    ``BaselineIntegrityError`` if any candidate QID appears more than once —
    an explicit check, not merely reliance on ``set()`` insertion silently
    collapsing a duplicate row (two duplicate rows for the same QID with a
    mutually consistent ``hullq_id`` would otherwise pass the crosswalk
    loader's conflict check undetected).
    """
    crosswalk = load_crosswalk_from_manifest(manifest)

    candidate_qids: set[str] = set()
    search_key_owners: dict[str, set[str]] = {}
    auto_admit_qids: set[str] = set()
    review_required_qids: set[str] = set()
    not_admitted_qids: set[str] = set()
    for row in manifest.get("candidates", []):
        qid = row["qid"]
        if qid in candidate_qids:
            raise BaselineIntegrityError(
                f"Baseline manifest at {manifest_path!r} contains duplicate candidate "
                f"QID {qid!r}; each candidate QID must appear at most once."
            )
        candidate_qids.add(qid)

        decision = row["decision"]
        if decision == str(BootstrapDecision.AUTO_ADMIT):
            auto_admit_qids.add(qid)
        elif decision == str(BootstrapDecision.REVIEW_REQUIRED):
            review_required_qids.add(qid)
        else:
            not_admitted_qids.add(qid)

        label = row.get("preferred_label")
        if label:
            for key in search_keys_for_candidate(label, row.get("aliases") or ()):
                search_key_owners.setdefault(key, set()).add(qid)

    return BaselineSnapshot(
        manifest_path=manifest_path,
        manifest_version=manifest.get("manifest_version", ""),
        sha256=sha256,
        candidate_qids=frozenset(candidate_qids),
        search_key_owners={k: frozenset(v) for k, v in search_key_owners.items()},
        crosswalk=crosswalk,
        auto_admit_qids=frozenset(auto_admit_qids),
        review_required_qids=frozenset(review_required_qids),
        not_admitted_qids=frozenset(not_admitted_qids),
    )


def merge_crosswalks_fail_closed(
    *crosswalks: dict[str, str], context: str = "crosswalk merge"
) -> dict[str, str]:
    """Fail-closed union of multiple QID -> HullQ-ID crosswalks (e.g. the
    baseline's retained crosswalk and a prior SLICE-0018 run's retained
    crosswalk), raising ``CrosswalkConflictError`` on either conflict form —
    same QID mapped to two different IDs, or the same ID addressed by two
    different QIDs — before any pair is lost to insertion order.
    """
    pairs = [item for cw in crosswalks for item in cw.items()]
    return _collapse_qid_id_pairs_fail_closed(pairs, context=context)


# ---------------------------------------------------------------------------
# C -> D. Discovery window -> expansion delta
# ---------------------------------------------------------------------------


def compute_expansion_delta(discovery_qids: Sequence[str], baseline: BaselineSnapshot) -> list[str]:
    """The current discovery window's QIDs minus all 1,000 accepted SLICE-0017
    baseline candidate QIDs, preserving discovery order.

    Only these QIDs receive new SLICE-0018 admission/review/non-admission
    decisions; a baseline QID reappearing in the current window is silently
    excluded here, never reclassified.
    """
    return [qid for qid in discovery_qids if qid not in baseline.candidate_qids]


def compute_baseline_absent_qids(
    discovery_qids: Sequence[str], baseline: BaselineSnapshot
) -> frozenset[str]:
    """Baseline candidate QIDs absent from the current discovery window.

    This is observed current-source churn, not a change to the accepted
    baseline's own retained state — the baseline candidate/crosswalk entry
    remains exactly as accepted.
    """
    discovered = frozenset(discovery_qids)
    return frozenset(qid for qid in baseline.candidate_qids if qid not in discovered)


def verify_entity_acquisition_completeness(
    requested_qids: Sequence[str], entities: Sequence[WikidataEntityData]
) -> None:
    """Fail closed unless *entities* covers *requested_qids* exactly.

    Checks, before any classification or manifest work uses the acquired
    entities:

    - no requested QID is missing from the returned entities;
    - no unexpected QID appears in the returned entities;
    - no QID is returned more than once.

    An incomplete or malformed Wikidata ``wbgetentities`` response (a
    requested QID silently absent from ``entities``) MUST NOT silently drop
    that QID from the retained SLICE-0018 delta — it must block the run
    entirely rather than quietly persist a truncated manifest.
    """
    requested_set = set(requested_qids)
    returned_qids = [e.qid for e in entities]
    returned_set = set(returned_qids)

    duplicates = {qid for qid in returned_set if returned_qids.count(qid) > 1}
    missing = requested_set - returned_set
    unexpected = returned_set - requested_set

    if duplicates or missing or unexpected:
        raise DeltaCompletenessError(
            "Entity acquisition did not exactly cover the requested expansion delta "
            f"(requested={len(requested_set)}, returned={len(returned_qids)}): "
            f"missing={sorted(missing)} unexpected={sorted(unexpected)} "
            f"duplicates={sorted(duplicates)}. Refusing to classify or persist a "
            "partial/malformed delta."
        )


def verify_delta_candidate_completeness(
    delta_candidates: Sequence[BootstrapCandidate],
    discovery_window_qids: Sequence[str],
    baseline: BaselineSnapshot,
) -> None:
    """Fail closed unless the candidate QID set exactly equals the expected
    expansion delta (``compute_expansion_delta(discovery_window_qids, baseline)``).

    Independent defense-in-depth check, run inside ``build_sl0018_manifest``
    itself, so a bug anywhere upstream in the acquisition/classification
    pipeline cannot silently produce a retained manifest describing a
    truncated, over-broad, or baseline-contaminated delta.
    """
    expected = set(compute_expansion_delta(discovery_window_qids, baseline))
    actual = {c.qid for c in delta_candidates}
    if actual != expected:
        raise DeltaCompletenessError(
            "SLICE-0018 candidate set does not exactly equal the expected expansion "
            f"delta (discovery_window_qids minus baseline): missing="
            f"{sorted(expected - actual)} unexpected={sorted(actual - expected)}. "
            "Refusing to write a manifest describing an incorrect delta."
        )


# ---------------------------------------------------------------------------
# Delta collision detection — against baseline, and delta-vs-delta
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BaselineCollision:
    """One delta candidate's collision against the retained baseline search-key space."""

    delta_qid: str
    baseline_qids: tuple[str, ...]
    shared_keys: tuple[str, ...]


def compute_baseline_collisions(
    entities: list[WikidataEntityData], baseline: BaselineSnapshot
) -> dict[str, BaselineCollision]:
    """For every labeled delta entity whose deterministic search-key
    projection (``search_keys_for_candidate`` — the single accepted HullQ
    projection) overlaps the retained baseline projection, record which
    baseline QIDs and keys caused the overlap.

    Covers both accepted-baseline-AUTO_ADMIT and accepted-baseline-
    REVIEW_REQUIRED candidates uniformly, since both retain a usable label
    and both must block a colliding delta candidate from auto-admission.
    Never mutates or reclassifies the colliding baseline entity.
    """
    collisions: dict[str, BaselineCollision] = {}
    for entity in entities:
        if not entity.label:
            continue
        own_keys = search_keys_for_candidate(entity.label, entity.aliases)
        shared_keys = sorted(k for k in own_keys if k in baseline.search_key_owners)
        if not shared_keys:
            continue
        owners: set[str] = set()
        for key in shared_keys:
            owners |= baseline.search_key_owners[key]
        collisions[entity.qid] = BaselineCollision(
            delta_qid=entity.qid,
            baseline_qids=tuple(sorted(owners)),
            shared_keys=tuple(shared_keys),
        )
    return collisions


# ---------------------------------------------------------------------------
# Delta classification — pure, deterministic, no network/database access
# ---------------------------------------------------------------------------


def classify_delta_candidates(
    delta_entities: list[WikidataEntityData],
    *,
    retrieved_at: str,
    baseline: BaselineSnapshot,
    id_factory: Any = mint_hullq_id,
    existing_crosswalk: dict[str, str] | None = None,
) -> tuple[list[BootstrapCandidate], list[CollisionCluster], dict[str, BaselineCollision]]:
    """Deterministically classify SLICE-0018 expansion-delta candidates.

    Reuses the exact accepted SLICE-0017 observation/bundle/evidence-link ID
    scheme (``OBS-WD-TIER0-{qid}`` etc. via ``BootstrapCandidate``) — safe
    because a delta QID is, by construction (``compute_expansion_delta``),
    never one of the 1,000 baseline QIDs, so no ID can collide with a
    baseline row.

    A delta candidate becomes ``REVIEW_REQUIRED`` if it collides with EITHER
    the retained baseline search-key space (any accepted 0017 candidate,
    admitted or review-bound — see ``compute_baseline_collisions``) OR
    another candidate within this same delta (transitively, via
    ``compute_collision_clusters``) — never a forced merge, and never a
    mutation of the colliding baseline entity's own accepted state.

    ``existing_crosswalk`` (typically the baseline's retained crosswalk
    merged with any already-minted SLICE-0018 IDs from a prior run) is
    reused exactly for any QID it already maps — never silently reminted,
    mirroring the accepted SLICE-0017 rerun contract.

    Fails closed via ``DeltaCompletenessError`` before any classification if
    *delta_entities* contains an accepted baseline QID (which MUST NOT be
    reclassified) or a duplicate QID (which MUST NOT silently collapse into
    one candidate row).
    """
    seen_qids: set[str] = set()
    duplicate_qids: set[str] = set()
    baseline_qids_in_delta: set[str] = set()
    for entity in delta_entities:
        if entity.qid in baseline.candidate_qids:
            baseline_qids_in_delta.add(entity.qid)
        if entity.qid in seen_qids:
            duplicate_qids.add(entity.qid)
        seen_qids.add(entity.qid)

    if baseline_qids_in_delta:
        raise DeltaCompletenessError(
            "classify_delta_candidates received accepted SLICE-0017 baseline QID(s) as "
            f"delta input; a baseline QID MUST NOT be reclassified: "
            f"{sorted(baseline_qids_in_delta)}"
        )
    if duplicate_qids:
        raise DeltaCompletenessError(
            "classify_delta_candidates received duplicate delta entity QID(s), which "
            f"MUST NOT silently collapse into one candidate row: {sorted(duplicate_qids)}"
        )

    crosswalk = dict(existing_crosswalk or {})
    delta_delta_clusters = compute_collision_clusters(delta_entities)
    delta_colliding_qids = {qid for cluster in delta_delta_clusters for qid in cluster.qids}
    baseline_collisions = compute_baseline_collisions(delta_entities, baseline)

    candidates: list[BootstrapCandidate] = []
    for entity in delta_entities:
        qid = entity.qid
        label = entity.label
        retained_id = crosswalk.get(qid)

        if not label:
            candidates.append(
                BootstrapCandidate(
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
            )
            continue

        observation_id = f"OBS-WD-TIER0-{qid}"
        bundle_id = f"BUNDLE-WD-TIER0-{qid}"
        bundle_version = "1"

        if qid in baseline_collisions or qid in delta_colliding_qids:
            candidates.append(
                BootstrapCandidate(
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
            )
            continue

        hullq_id = retained_id if retained_id is not None else id_factory()
        crosswalk[qid] = hullq_id
        candidates.append(
            BootstrapCandidate(
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
        )

    return candidates, delta_delta_clusters, baseline_collisions


# ---------------------------------------------------------------------------
# Manifest (de)serialization — JSON-primitive
# ---------------------------------------------------------------------------


def build_sl0018_manifest(
    delta_candidates: list[BootstrapCandidate],
    *,
    generated_at: str,
    baseline: BaselineSnapshot,
    discovery_window_qids: list[str],
    requested_limit: int,
    target_reached: bool,
    delta_delta_clusters: list[CollisionCluster],
    baseline_collisions: dict[str, BaselineCollision],
    retrieval_count: int,
    extracted_record_count: int,
    acquisition_failure_count: int = 0,
    fetched_entity_count: int | None = None,
    acquired_at: str | None = None,
    classification_recomputed_at: str | None = None,
    historical_crosswalk: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the full versioned, JSON-serializable SLICE-0018 manifest document.

    ``delta_candidates`` MUST contain only the current expansion delta —
    never a baseline QID and never a QID carried forward merely because an
    earlier SLICE-0018 run once classified it outside the current discovery
    window. Verified independently here (fails closed via
    ``DeltaCompletenessError`` before anything else) against
    ``discovery_window_qids`` minus ``baseline.candidate_qids``, so a bug
    anywhere upstream cannot silently produce a manifest describing the
    wrong delta.

    ``historical_crosswalk`` is the full historical QID -> HullQ-ID registry
    accumulated across every prior run (accepted SLICE-0017 baseline crosswalk
    merged with every previously retained SLICE-0018 mapping — typically
    loaded via ``merge_crosswalks_fail_closed(baseline.crosswalk,
    load_crosswalk_from_manifest(prior_sl0018_manifest))``). It MUST be
    supplied whenever a prior SLICE-0018 manifest exists: omitting it falls
    back to ``baseline.crosswalk`` alone, which would silently drop any
    previously retained SLICE-0018 mapping for a QID absent from the current
    delta — the historical crosswalk MUST survive a QID's later omission and
    still be reused byte-for-byte if that QID reappears. ``retained_crosswalk``
    is the complete merged registry (historical union current delta),
    computed here by failing closed (``CrosswalkConflictError``) on any drift
    between the two. A QID present in ``historical_crosswalk`` but absent
    from the current ``delta_candidates`` remains in ``retained_crosswalk``
    — it is never dropped merely because this run did not reclassify it.
    """
    if requested_limit > BOOTSTRAP_REQUESTED_LIMIT_SL0018:
        raise ValueError(
            f"requested_limit={requested_limit} exceeds the SLICE-0018 bounded maximum "
            f"discovery window of {BOOTSTRAP_REQUESTED_LIMIT_SL0018}"
        )
    verify_delta_candidate_completeness(delta_candidates, discovery_window_qids, baseline)

    validate_crosswalk_consistency(delta_candidates)
    delta_crosswalk = {c.qid: c.hullq_id for c in delta_candidates if c.hullq_id is not None}
    historical = historical_crosswalk if historical_crosswalk is not None else baseline.crosswalk
    full_crosswalk = merge_crosswalks_fail_closed(
        historical,
        delta_crosswalk,
        context="historical crosswalk merge with SLICE-0018 delta candidates",
    )

    baseline_absent = compute_baseline_absent_qids(discovery_window_qids, baseline)
    overlap_qids = frozenset(discovery_window_qids) & baseline.candidate_qids
    overlap_count = len(overlap_qids)

    reason_breakdown: dict[str, int] = {}
    for candidate in delta_candidates:
        for reason in candidate.reason_codes:
            reason_breakdown[str(reason)] = reason_breakdown.get(str(reason), 0) + 1

    auto_admit = sum(1 for c in delta_candidates if c.decision == BootstrapDecision.AUTO_ADMIT)
    review_required = sum(
        1 for c in delta_candidates if c.decision == BootstrapDecision.REVIEW_REQUIRED
    )
    not_admitted = sum(1 for c in delta_candidates if c.decision == BootstrapDecision.NOT_ADMITTED)

    # Every hullq_id-bearing delta candidate was either reused from the
    # historical registry (AUTO_ADMIT reusing a retained ID, or a
    # REVIEW_REQUIRED candidate preserving a reserved historical ID) or
    # freshly minted this run — mutually exclusive and exhaustive.
    newly_minted_id_count = sum(
        1 for c in delta_candidates if c.hullq_id is not None and c.qid not in historical
    )
    reused_historical_id_count = sum(
        1 for c in delta_candidates if c.hullq_id is not None and c.qid in historical
    )

    return {
        "manifest_version": SL0018_MANIFEST_VERSION,
        "source_id": WIKIDATA_SOURCE_ID,
        "generated_at": generated_at,
        "acquired_at": acquired_at if acquired_at is not None else generated_at,
        "classification_recomputed_at": classification_recomputed_at,
        "requested_limit": requested_limit,
        "safety_ceiling": BOOTSTRAP_SAFETY_CEILING_SL0018,
        "discovery": {
            "unique_qids_returned": len(discovery_window_qids),
            "target_reached": target_reached,
            "delta_candidates_processed": len(delta_candidates),
            "fetched_entity_count": (
                fetched_entity_count if fetched_entity_count is not None else len(delta_candidates)
            ),
            "acquisition_failure_count": acquisition_failure_count,
            "sparql_query_version": BOOTSTRAP_SPARQL_QUERY_VERSION,
            "sparql_endpoint": BOOTSTRAP_SPARQL_ENDPOINT,
            "entity_api_endpoint": BOOTSTRAP_ENTITY_API_ENDPOINT,
            "entity_api_version": BOOTSTRAP_ENTITY_API_VERSION,
            "discovery_window_qids": list(discovery_window_qids),
        },
        "baseline_reference": {
            "manifest_path": baseline.manifest_path,
            "manifest_version": baseline.manifest_version,
            "sha256": baseline.sha256,
            "implementation_head": ACCEPTED_0017_IMPLEMENTATION_HEAD,
            "candidate_count": len(baseline.candidate_qids),
        },
        "overlap": {
            "overlap_count": overlap_count,
            "baseline_absent_count": len(baseline_absent),
            "baseline_absent_qids": sorted(baseline_absent),
        },
        "delta": {
            "delta_count": len(delta_candidates),
        },
        "usage_metrics": {
            "retrieval_count": retrieval_count,
            "extracted_record_count": extracted_record_count,
        },
        "candidates": [candidate_to_manifest_dict(c) for c in delta_candidates],
        "retained_crosswalk": [
            {"qid": qid, "hullq_id": hullq_id} for qid, hullq_id in sorted(full_crosswalk.items())
        ],
        "delta_collisions": {
            "baseline": [
                {
                    "delta_qid": bc.delta_qid,
                    "baseline_qids": list(bc.baseline_qids),
                    "shared_keys": list(bc.shared_keys),
                }
                for bc in sorted(baseline_collisions.values(), key=lambda b: b.delta_qid)
            ],
            "delta_delta": [
                {"qids": list(c.qids), "shared_keys": list(c.shared_keys)}
                for c in delta_delta_clusters
            ],
        },
        "counts": {
            "delta_candidates_processed": len(delta_candidates),
            "auto_admit": auto_admit,
            "review_required": review_required,
            "not_admitted": not_admitted,
            "reason_breakdown": reason_breakdown,
            "baseline_collision_count": len(baseline_collisions),
            "delta_delta_collision_cluster_count": len(delta_delta_clusters),
            "historical_crosswalk_count_before": len(historical),
            "retained_crosswalk_count": len(full_crosswalk),
            "newly_minted_id_count": newly_minted_id_count,
            "reused_historical_id_count": reused_historical_id_count,
            "research_observation_count": sum(
                1 for c in delta_candidates if c.observation_id is not None
            ),
            "canonical_evidence_link_count": sum(
                1 for c in delta_candidates if c.evidence_link_id is not None
            ),
            "combined_canonical_boat_model_count_expected": (
                len(baseline.auto_admit_qids) + auto_admit
            ),
        },
    }
