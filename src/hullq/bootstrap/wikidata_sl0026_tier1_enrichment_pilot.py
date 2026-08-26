"""Bounded Wikidata Tier-1 enrichment evidence pilot — SLICE-0026.

Implements the pure, deterministic logic described in
``docs/slices/SLICE-0026-bounded-wikidata-tier1-enrichment-evidence-pilot.md``.

This module performs no network acquisition (that remains in
``hullq.sources.wikidata.WikidataAdapter``) and no database access (that
remains in ``hullq.persistence``). Given only the already-accepted SLICE-0017
baseline manifest and SLICE-0018 delta manifest, plus already-acquired
``WikidataEntityData``/``FieldEvidence`` produced by the existing adapter, it:

- reproduces the accepted 1,770 canonical-BoatModel / 1,772 historical-
  crosswalk identity boundary and fails closed on any drift;
- deterministically selects exactly 100 distinct canonical BoatModels (each
  with its single accepted source QID) from that boundary;
- filters already-extracted evidence down to the five allowed Tier-1 field
  pointers (LOA/LWL/beam/draft/displacement);
- buckets per-entity, per-field coverage into exactly one of four mutually
  exclusive states (normalized candidate present / source statement present
  / unsupported-or-malformed / no usable value) using only the adapter's own
  produced outputs (``WikidataEntityData.raw_claims`` presence and
  ``FieldEvidence.field_pointer``/``normalized_candidate``) — never a new
  qualifier/unit parser;
- assembles one ``ResearchEvidenceBundle`` per pilot BoatModel (subject kept
  BoatDesign-shaped and QID-keyed, per IDENTITY_MODEL.v0.1 — never rewritten
  into a fabricated canonical BoatDesign ID) for persistence via the existing
  SLICE-0013 importer;
- assembles the retained selection/evidence-manifest/report documents and
  their offline self-consistency verification.

Explicitly does NOT:
- perform any network acquisition or SPARQL/discovery query;
- infer, mint or persist a canonical BoatDesign generation;
- create or mutate a canonical BoatModel/crosswalk row;
- reimplement Wikidata qualifier/unit extraction (only property-presence
  checks and produced-evidence inspection are used for coverage bucketing).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from hullq.bootstrap.wikidata_tier0 import CrosswalkConflictError
from hullq.bootstrap.wikidata_tier0_sl0018 import (
    BASELINE_MANIFEST_PATH,
    BaselineIntegrityError,
    build_baseline_snapshot_from_manifest,
    load_baseline_snapshot,
)
from hullq.domain.provenance import FieldEvidence, JsonPointer
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import ResearchEvidenceBundle, migrate_evidence_v02_to_v03
from hullq.sources import wikidata as _wikidata_adapter_module
from hullq.sources.wikidata import WIKIDATA_SOURCE_ID, WikidataEntityData, WikidataQualityReport

__all__ = [
    "ACCEPTED_CANONICAL_BOAT_MODEL_COUNT",
    "ACCEPTED_HISTORICAL_CROSSWALK_COUNT",
    "ACCEPTED_SL0018_DELTA_MANIFEST_SHA256",
    "ALLOWED_FIELD_POINTERS",
    "DELTA_MANIFEST_PATH",
    "FIELD_LABEL_BY_POINTER",
    "PILOT_SIZE",
    "PTR_BEAM",
    "PTR_DISPLACEMENT",
    "PTR_DRAFT",
    "PTR_LOA",
    "PTR_LWL",
    "SL0026_ACTIVITY_ID",
    "EntityFieldCoverage",
    "FieldCoverageBucket",
    "IdentityBoundary",
    "IdentityBoundaryIntegrityError",
    "PilotBoatModel",
    "build_evidence_manifest_document",
    "build_pilot_bundle",
    "build_selection_document",
    "classify_entity_field_coverage",
    "filter_to_allowed_evidence",
    "load_reproduced_identity_boundary",
    "rebuild_entities_from_manifest",
    "select_pilot_boatmodels",
    "summarize_field_coverage",
    "trim_raw_claims_to_allowed_properties",
    "verify_evidence_manifest_self_consistency",
    "verify_selection_self_consistency",
]

ROOT = Path(__file__).resolve().parents[3]
DELTA_MANIFEST_PATH = ROOT / "research" / "bootstrap" / "wikidata" / "sl0018-2500" / "manifest.json"

# Exact raw-byte SHA256 of the accepted retained SLICE-0018 delta manifest
# (research/bootstrap/wikidata/sl0018-2500/manifest.json), independently
# recomputed and confirmed to equal the pinned value already accepted by
# hullq.bootstrap.wikidata_sl0022_alt_route_admission.ACCEPTED_SL0018_MANIFEST_SHA256.
# Pinned here directly (rather than imported) so SLICE-0026 depends only on
# the SLICE-0017/0018 artifacts named in its own controlling contract, not on
# the unrelated SLICE-0021/0022 retained inputs that module also fingerprints.
ACCEPTED_SL0018_DELTA_MANIFEST_SHA256 = (
    "41ef238c217e31cfbe03329e226a1a3dfff849061df93b8f2523a1e72493821f"
)

# Accepted SLICE-0025 closure boundary (docs/slices/SLICE-0025-acceptance-closure.md):
# "canonical BoatModels 1,770 / historical QID -> HullQ-ID mappings 1,772".
ACCEPTED_CANONICAL_BOAT_MODEL_COUNT = 1770
ACCEPTED_HISTORICAL_CROSSWALK_COUNT = 1772

PILOT_SIZE = 100
SL0026_ACTIVITY_ID = "SLICE-0026-TIER1-ENRICHMENT-PILOT"

# ---------------------------------------------------------------------------
# Allowed field pointers — exactly the five pointers named by the controlling
# slice's "Allowed field pointers" section. Values match, byte for byte, the
# private pointer constants already used by hullq.sources.wikidata; defined
# again here (not reimported, since the adapter does not export them) as
# plain data, not as a reimplementation of any extraction/normalization logic.
# ---------------------------------------------------------------------------

PTR_LOA = JsonPointer("/baseline/dimensions/loa_m")
PTR_LWL = JsonPointer("/baseline/dimensions/lwl_m")
PTR_BEAM = JsonPointer("/baseline/dimensions/beam_m")
PTR_DRAFT = JsonPointer("/baseline/dimensions/draft_min_m")
PTR_DISPLACEMENT = JsonPointer("/baseline/dimensions/displacement_kg")

# The adapter's own (non-allowed) ballast pointer — needed only internally to
# correctly classify displacement coverage (P2067 is shared between
# displacement and ballast); never persisted or reported as pilot output.
_PTR_BALLAST = JsonPointer("/baseline/dimensions/ballast_kg")

ALLOWED_FIELD_POINTERS: tuple[JsonPointer, ...] = (
    PTR_LOA,
    PTR_LWL,
    PTR_BEAM,
    PTR_DRAFT,
    PTR_DISPLACEMENT,
)

FIELD_LABEL_BY_POINTER: dict[JsonPointer, str] = {
    PTR_LOA: "loa",
    PTR_LWL: "lwl",
    PTR_BEAM: "beam",
    PTR_DRAFT: "draft",
    PTR_DISPLACEMENT: "displacement",
}

# Reused (not redefined) Wikidata property identifiers that already exist
# on hullq.sources.wikidata for exactly this purpose — accessed via the
# module object rather than duplicating the literal strings, since the
# adapter does not export them.
_PROP_LENGTH: str = _wikidata_adapter_module._PROP_LENGTH
_PROP_WIDTH: str = _wikidata_adapter_module._PROP_WIDTH
_PROP_HEIGHT: str = _wikidata_adapter_module._PROP_HEIGHT
_PROP_MASS: str = _wikidata_adapter_module._PROP_MASS

_FIELD_PROPERTY: dict[JsonPointer, str] = {
    PTR_LOA: _PROP_LENGTH,
    PTR_LWL: _PROP_LENGTH,
    PTR_BEAM: _PROP_WIDTH,
    PTR_DRAFT: _PROP_HEIGHT,
    PTR_DISPLACEMENT: _PROP_MASS,
}

# The sibling field pointer sharing the SAME Wikidata property (disambiguated
# only by a P642 qualifier), if any. A property statement that matched the
# sibling (not this field) is "no usable value" for this field, never
# "unsupported/malformed" — see classify_entity_field_coverage.
_FIELD_SIBLING: dict[JsonPointer, JsonPointer | None] = {
    PTR_LOA: PTR_LWL,
    PTR_LWL: PTR_LOA,
    PTR_BEAM: None,
    PTR_DRAFT: None,
    PTR_DISPLACEMENT: _PTR_BALLAST,
}


# ---------------------------------------------------------------------------
# 1. Identity boundary reproduction — fail closed on drift
# ---------------------------------------------------------------------------


class IdentityBoundaryIntegrityError(RuntimeError):
    """Raised when the retained SLICE-0017/0018 artifacts no longer reproduce
    the accepted 1,770 canonical-BoatModel / 1,772 historical-crosswalk
    identity boundary.

    SLICE-0026 MUST fail closed (BLOCKED) rather than select a pilot set
    against a drifted identity boundary.
    """


@dataclass(frozen=True)
class IdentityBoundary:
    """The reproduced accepted identity boundary and the combined AUTO_ADMIT
    QID -> HullQ-ID universe it is built from.

    ``auto_admit_qid_to_hullq_id`` is the combined SLICE-0017 baseline +
    SLICE-0018 delta AUTO_ADMIT universe only (965 + 805 = 1,770 pairs) — a
    QID/HullQ-ID pair here is always a genuinely canonical BoatModel, never a
    REVIEW_REQUIRED reserved-ID crosswalk entry (which is why this set has
    exactly 1,770 pairs rather than the 1,772-entry historical crosswalk).
    """

    baseline_manifest_sha256: str
    delta_manifest_sha256: str
    canonical_boat_model_count: int
    historical_crosswalk_count: int
    auto_admit_qid_to_hullq_id: tuple[tuple[str, str], ...]
    preferred_label_by_qid: Mapping[str, str | None]


def load_reproduced_identity_boundary(
    *,
    baseline_manifest_path: Path = BASELINE_MANIFEST_PATH,
    delta_manifest_path: Path = DELTA_MANIFEST_PATH,
) -> IdentityBoundary:
    """Load and validate the accepted SLICE-0017 baseline and SLICE-0018
    delta manifests, reproducing the accepted 1,770/1,772 identity boundary.

    Reuses ``hullq.bootstrap.wikidata_tier0_sl0018.load_baseline_snapshot``
    for the complete accepted SLICE-0017 fail-closed check (raw-byte SHA256,
    manifest_version, candidate/decision aggregate counts) and
    ``build_baseline_snapshot_from_manifest`` to build the combined
    SLICE-0017+0018 snapshot — never reimplementing that classification
    logic. Fails closed via ``IdentityBoundaryIntegrityError`` if:

    - the SLICE-0017 baseline manifest fails its own accepted integrity
      check (wrapped from ``BaselineIntegrityError``/``CrosswalkConflictError``);
    - the SLICE-0018 delta manifest's raw-byte SHA256 does not match the
      pinned accepted value;
    - the combined AUTO_ADMIT count is not exactly 1,770 or the combined
      historical crosswalk is not exactly 1,772 entries.

    Performs no network access and never mutates either input file.
    """
    try:
        baseline_only = load_baseline_snapshot(baseline_manifest_path)
    except (BaselineIntegrityError, CrosswalkConflictError) as exc:
        raise IdentityBoundaryIntegrityError(
            f"Retained SLICE-0017 baseline at {baseline_manifest_path} failed accepted "
            f"integrity check: {exc}"
        ) from exc
    except OSError as exc:
        raise IdentityBoundaryIntegrityError(
            f"Retained SLICE-0017 baseline at {baseline_manifest_path} could not be read: {exc}"
        ) from exc

    try:
        delta_bytes = delta_manifest_path.read_bytes()
    except OSError as exc:
        raise IdentityBoundaryIntegrityError(
            f"Retained SLICE-0018 delta manifest at {delta_manifest_path} could not be read: {exc}"
        ) from exc
    delta_sha256 = hashlib.sha256(delta_bytes).hexdigest()
    if delta_sha256 != ACCEPTED_SL0018_DELTA_MANIFEST_SHA256:
        raise IdentityBoundaryIntegrityError(
            f"Retained SLICE-0018 delta manifest at {delta_manifest_path} failed integrity "
            f"check: sha256={delta_sha256!r}, expected {ACCEPTED_SL0018_DELTA_MANIFEST_SHA256!r}"
        )
    delta_manifest = json.loads(delta_bytes.decode("utf-8"))
    baseline_manifest = json.loads(baseline_manifest_path.read_bytes().decode("utf-8"))

    baseline_qids = {row["qid"] for row in baseline_manifest["candidates"]}
    delta_qids = {row["qid"] for row in delta_manifest["candidates"]}
    overlap = baseline_qids & delta_qids
    if overlap:
        raise IdentityBoundaryIntegrityError(
            "Retained SLICE-0017 baseline and SLICE-0018 delta manifests unexpectedly share "
            f"{len(overlap)} QID(s); the delta must be disjoint from the baseline by construction."
        )

    combined_manifest = {
        "candidates": [*baseline_manifest["candidates"], *delta_manifest["candidates"]],
        # SLICE-0018's own retained_crosswalk is already the complete merged
        # historical registry (accepted SLICE-0017 baseline crosswalk union
        # every retained SLICE-0018 delta mapping) — no further merge needed.
        "retained_crosswalk": delta_manifest["retained_crosswalk"],
    }
    try:
        combined = build_baseline_snapshot_from_manifest(
            combined_manifest, manifest_path="<combined SLICE-0017+0018>", sha256=""
        )
    except (BaselineIntegrityError, CrosswalkConflictError) as exc:
        raise IdentityBoundaryIntegrityError(
            f"Combined SLICE-0017+0018 candidate set is internally inconsistent: {exc}"
        ) from exc

    canonical_count = len(combined.auto_admit_qids)
    crosswalk_count = len(combined.crosswalk)
    if canonical_count != ACCEPTED_CANONICAL_BOAT_MODEL_COUNT:
        raise IdentityBoundaryIntegrityError(
            "Combined SLICE-0017+0018 AUTO_ADMIT (canonical BoatModel) count does not equal "
            f"the accepted {ACCEPTED_CANONICAL_BOAT_MODEL_COUNT}: got {canonical_count}"
        )
    if crosswalk_count != ACCEPTED_HISTORICAL_CROSSWALK_COUNT:
        raise IdentityBoundaryIntegrityError(
            "Combined SLICE-0017+0018 historical crosswalk count does not equal the accepted "
            f"{ACCEPTED_HISTORICAL_CROSSWALK_COUNT}: got {crosswalk_count}"
        )

    preferred_label_by_qid: dict[str, str | None] = {
        row["qid"]: row.get("preferred_label")
        for row in (*baseline_manifest["candidates"], *delta_manifest["candidates"])
    }

    auto_admit_pairs = tuple(
        sorted((qid, combined.crosswalk[qid]) for qid in combined.auto_admit_qids)
    )

    return IdentityBoundary(
        baseline_manifest_sha256=baseline_only.sha256,
        delta_manifest_sha256=delta_sha256,
        canonical_boat_model_count=canonical_count,
        historical_crosswalk_count=crosswalk_count,
        auto_admit_qid_to_hullq_id=auto_admit_pairs,
        preferred_label_by_qid=preferred_label_by_qid,
    )


# ---------------------------------------------------------------------------
# 2. Deterministic pilot selection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PilotBoatModel:
    """One selected pilot BoatModel: its accepted canonical HullQ ID, its
    single accepted source QID, and (for descriptive/report purposes only,
    never asserting identity) its retained SLICE-0017/0018 preferred label.
    """

    hullq_id: str
    qid: str
    preferred_label: str | None


def select_pilot_boatmodels(
    boundary: IdentityBoundary, count: int = PILOT_SIZE
) -> tuple[PilotBoatModel, ...]:
    """Deterministically select exactly *count* distinct canonical BoatModels.

    Ordering is ascending canonical HullQ BoatModel ID over the combined
    SLICE-0017+0018 AUTO_ADMIT universe — stable and reproducible offline
    from the accepted retained artifacts alone, independent of discovery/
    acquisition order. Because ``IdentityBoundary.auto_admit_qid_to_hullq_id``
    is built only from AUTO_ADMIT candidates, each entry already has exactly
    one QID and one HullQ ID (enforced fail-closed upstream by
    ``validate_crosswalk_consistency``/``_collapse_qid_id_pairs_fail_closed``),
    so no BoatModel can appear twice in the selection even if a future
    upstream change ever retained multiple historical QIDs for one BoatModel.
    """
    if count > len(boundary.auto_admit_qid_to_hullq_id):
        raise ValueError(
            f"Requested pilot size {count} exceeds the accepted canonical BoatModel universe "
            f"size {len(boundary.auto_admit_qid_to_hullq_id)}"
        )
    ordered = sorted(boundary.auto_admit_qid_to_hullq_id, key=lambda pair: pair[1])
    selected = ordered[:count]

    seen_ids: set[str] = set()
    seen_qids: set[str] = set()
    for qid, hullq_id in selected:
        if hullq_id in seen_ids:
            raise ValueError(f"Duplicate BoatModel ID {hullq_id!r} in pilot selection")
        if qid in seen_qids:
            raise ValueError(f"Duplicate QID {qid!r} in pilot selection")
        seen_ids.add(hullq_id)
        seen_qids.add(qid)

    return tuple(
        PilotBoatModel(
            hullq_id=hullq_id,
            qid=qid,
            preferred_label=boundary.preferred_label_by_qid.get(qid),
        )
        for qid, hullq_id in selected
    )


# ---------------------------------------------------------------------------
# 3. Evidence filtering — admit only the five allowed field pointers
# ---------------------------------------------------------------------------


def filter_to_allowed_evidence(evidence: Sequence[FieldEvidence]) -> list[FieldEvidence]:
    """Keep only evidence items whose field pointer is one of the five
    allowed Tier-1 pointers.

    Drops any ballast/builders/designers/number_built evidence the existing
    adapter's ``extract_field_evidence`` also produces from the same acquired
    entities — the controlling slice's "Allowed field pointers" admits only
    LOA/LWL/beam/draft/displacement to the retained pilot output.
    """
    return [ev for ev in evidence if ev.field_pointer in ALLOWED_FIELD_POINTERS]


# ---------------------------------------------------------------------------
# 4. Per-field coverage classification
# ---------------------------------------------------------------------------


class FieldCoverageBucket(StrEnum):
    """One of four mutually exclusive, exhaustive per-entity-per-field
    coverage states (controlling slice requirement 10)."""

    NORMALIZED_CANDIDATE_PRESENT = "normalized_candidate_present"
    SOURCE_STATEMENT_PRESENT = "source_statement_present"
    UNSUPPORTED_OR_MALFORMED = "unsupported_or_malformed"
    NO_USABLE_VALUE = "no_usable_value"


@dataclass(frozen=True)
class EntityFieldCoverage:
    qid: str
    field_pointer: JsonPointer
    bucket: FieldCoverageBucket


def _prop_present(entity: WikidataEntityData, prop_id: str) -> bool:
    claims = entity.raw_claims.get(prop_id, [])
    return isinstance(claims, list) and len(claims) > 0


# The exact set of raw Wikidata properties any of the five allowed fields can
# ever be extracted from. Used only to trim retained raw_claims to the fields
# this pilot is scoped to (never widening scope to manufacturer/designer/
# total_produced, which the pilot does not admit) while still retaining
# enough raw source representation for full offline (zero-network)
# recomputation of extract_field_evidence/coverage in --verify.
_RELEVANT_RAW_PROPERTIES: tuple[str, ...] = (
    _PROP_LENGTH,
    _PROP_WIDTH,
    _PROP_HEIGHT,
    _PROP_MASS,
)


def trim_raw_claims_to_allowed_properties(raw_claims: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only the raw claim arrays for properties the five allowed fields
    can be extracted from, dropping everything else (manufacturer, designer,
    total_produced, and any other statement the source entity carries).

    A plain key-filter over already-acquired raw claims — not a statement
    parser — so retaining this trimmed form for offline replay does not
    reimplement any extraction/normalization logic.
    """
    return {prop: raw_claims[prop] for prop in _RELEVANT_RAW_PROPERTIES if prop in raw_claims}


def classify_entity_field_coverage(
    entity: WikidataEntityData,
    *,
    field_pointer: JsonPointer,
    own_field_evidence: Sequence[FieldEvidence],
    sibling_field_evidence: Sequence[FieldEvidence],
) -> FieldCoverageBucket:
    """Classify one entity's coverage for one allowed field pointer.

    Uses only already-produced adapter outputs — never a new qualifier/unit
    parser:

    - ``own_field_evidence`` / ``sibling_field_evidence`` are the (unfiltered,
      pre-``filter_to_allowed_evidence``) ``FieldEvidence`` items the adapter's
      own ``extract_field_evidence`` already produced for *this* entity's
      *this* pointer and its property-sharing sibling pointer (LOA<->LWL via
      P2043; displacement<->ballast via P2067; beam/draft have no sibling).
    - ``entity.raw_claims`` presence-checking (a plain dict lookup, not a
      statement parser) distinguishes "the property had statements that
      matched neither this field nor its sibling" (unsupported/malformed)
      from "the property is entirely absent" (no usable value).

    A property statement that matched the sibling field (not this one) is
    classified ``NO_USABLE_VALUE`` for this field, not ``UNSUPPORTED_OR_
    MALFORMED`` — the boat's Wikidata entry simply records the sibling
    measurement (e.g. LWL but not LOA), which is not a parsing failure.
    Because a genuinely unmatched/malformed shared-property statement cannot
    be attributed to only one of two sibling fields from the adapter's public
    outputs alone, such a statement is conservatively counted as unsupported/
    malformed against BOTH sibling fields — documented here and in the
    retained REPORT.md as a known upper-bound property of the shared-property
    fields (LOA/LWL, displacement) only.
    """
    if any(ev.normalized_candidate is not None for ev in own_field_evidence):
        return FieldCoverageBucket.NORMALIZED_CANDIDATE_PRESENT
    if own_field_evidence:
        return FieldCoverageBucket.SOURCE_STATEMENT_PRESENT
    if sibling_field_evidence:
        return FieldCoverageBucket.NO_USABLE_VALUE
    prop_id = _FIELD_PROPERTY[field_pointer]
    if _prop_present(entity, prop_id):
        return FieldCoverageBucket.UNSUPPORTED_OR_MALFORMED
    return FieldCoverageBucket.NO_USABLE_VALUE


def _evidence_index(
    full_evidence: Sequence[FieldEvidence],
) -> dict[tuple[str, JsonPointer], list[FieldEvidence]]:
    index: dict[tuple[str, JsonPointer], list[FieldEvidence]] = {}
    for ev in full_evidence:
        index.setdefault((ev.subject.id, ev.field_pointer), []).append(ev)
    return index


def summarize_field_coverage(
    entities: Sequence[WikidataEntityData],
    full_evidence: Sequence[FieldEvidence],
) -> tuple[dict[str, dict[str, int]], tuple[EntityFieldCoverage, ...]]:
    """Compute per-field coverage bucket counts (and every individual
    per-entity-per-field classification, for the retained evidence manifest)
    over exactly *entities*, for the five allowed field pointers only.

    *full_evidence* MUST be the unfiltered evidence the adapter's
    ``extract_field_evidence`` produced for *entities* (including ballast/
    builders/designers/number_built) — filtering to the five allowed
    pointers happens only for the retained/persisted evidence output
    (``filter_to_allowed_evidence``), never before coverage classification,
    or sibling-field disambiguation (LOA<->LWL, displacement<->ballast) would
    be impossible.
    """
    index = _evidence_index(full_evidence)
    counts: dict[str, dict[str, int]] = {
        FIELD_LABEL_BY_POINTER[ptr]: {bucket.value: 0 for bucket in FieldCoverageBucket}
        for ptr in ALLOWED_FIELD_POINTERS
    }
    details: list[EntityFieldCoverage] = []
    for entity in entities:
        for ptr in ALLOWED_FIELD_POINTERS:
            sibling = _FIELD_SIBLING[ptr]
            own = index.get((entity.qid, ptr), [])
            sib = index.get((entity.qid, sibling), []) if sibling is not None else []
            bucket = classify_entity_field_coverage(
                entity, field_pointer=ptr, own_field_evidence=own, sibling_field_evidence=sib
            )
            counts[FIELD_LABEL_BY_POINTER[ptr]][bucket.value] += 1
            details.append(EntityFieldCoverage(qid=entity.qid, field_pointer=ptr, bucket=bucket))
    return counts, tuple(details)


# ---------------------------------------------------------------------------
# 5. Research evidence bundle assembly
# ---------------------------------------------------------------------------


def build_pilot_bundle(
    pilot_model: PilotBoatModel, allowed_evidence_for_qid: Sequence[FieldEvidence]
) -> ResearchEvidenceBundle:
    """Build the retained ``ResearchEvidenceBundle`` for one pilot BoatModel.

    ``allowed_evidence_for_qid`` MUST already be filtered to
    ``ALLOWED_FIELD_POINTERS`` (``filter_to_allowed_evidence``) and restricted
    to this BoatModel's own QID. Each ``FieldEvidence`` (v0.2, as produced
    directly by the existing adapter) is losslessly migrated to
    ``FieldEvidenceV3`` via the existing SLICE-0012
    ``migrate_evidence_v02_to_v03`` adapter (absent claim_semantics/
    applicability map to explicit unknown, never a nominal/global default).
    The evidence subject (set by the adapter itself) remains BoatDesign-
    shaped and keyed by the Wikidata QID — never rewritten to
    ``pilot_model.hullq_id`` or any fabricated canonical BoatDesign ID; the
    BoatModel<->QID link is retained separately in the selection document.
    An empty bundle (no usable evidence for any of the five fields) is valid
    and retained — absence is preserved as an explicit empty bundle, never
    converted to a fabricated value.
    """
    for ev in allowed_evidence_for_qid:
        if ev.subject.id != pilot_model.qid:
            raise ValueError(
                f"Evidence subject id {ev.subject.id!r} does not match pilot BoatModel QID "
                f"{pilot_model.qid!r}"
            )
        if ev.field_pointer not in ALLOWED_FIELD_POINTERS:
            raise ValueError(
                f"Evidence field_pointer {ev.field_pointer!r} is not one of the five allowed "
                "Tier-1 field pointers"
            )

    promoted = tuple(migrate_evidence_v02_to_v03(ev) for ev in allowed_evidence_for_qid)
    return ResearchEvidenceBundle(
        bundle_id=f"BUNDLE-SL0026-{pilot_model.qid}",
        bundle_version="1",
        research_target=ResearchTarget(
            manufacturer=None,
            model=pilot_model.preferred_label or pilot_model.qid,
            first_built=None,
        ),
        research_job_id=None,
        activity_id=SL0026_ACTIVITY_ID,
        observations=(),
        unresolved_findings=(),
        promoted_evidence=promoted,
        reference_crosschecks=(),
    )


# ---------------------------------------------------------------------------
# 6. Retained document assembly — JSON-primitive, pure
# ---------------------------------------------------------------------------

SELECTION_SCHEMA_VERSION = "sl0026-selection-v1"
EVIDENCE_MANIFEST_SCHEMA_VERSION = "sl0026-evidence-manifest-v1"


def build_selection_document(
    *, generated_at: str, boundary: IdentityBoundary, selection: Sequence[PilotBoatModel]
) -> dict[str, Any]:
    """Assemble the retained ``selection.json`` document: the deterministic
    100-BoatModel selection with explicit BoatModel<->QID links, plus the
    reproduced identity boundary it was selected from."""
    return {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "generated_at": generated_at,
        "identity_boundary": {
            "baseline_manifest_path": "research/bootstrap/wikidata/manifest.json",
            "baseline_manifest_sha256": boundary.baseline_manifest_sha256,
            "delta_manifest_path": "research/bootstrap/wikidata/sl0018-2500/manifest.json",
            "delta_manifest_sha256": boundary.delta_manifest_sha256,
            "canonical_boat_model_count": boundary.canonical_boat_model_count,
            "historical_crosswalk_count": boundary.historical_crosswalk_count,
        },
        "selection_ordering": (
            "ascending canonical HullQ BoatModel ID over the combined SLICE-0017+0018 "
            "AUTO_ADMIT QID->HullQ-ID universe; first pilot_size taken"
        ),
        "pilot_size": len(selection),
        "boat_models": [
            {"hullq_id": m.hullq_id, "qid": m.qid, "preferred_label": m.preferred_label}
            for m in selection
        ],
    }


def verify_selection_self_consistency(
    *, boundary: IdentityBoundary, selection_document: Mapping[str, Any]
) -> list[str]:
    """Independently rebuild the expected selection from a freshly
    reproduced identity boundary and compare against a retained
    ``selection.json`` document. Never trusts the retained document's own
    boundary/selection fields as verification input."""
    problems: list[str] = []
    expected_boundary = {
        "baseline_manifest_path": "research/bootstrap/wikidata/manifest.json",
        "baseline_manifest_sha256": boundary.baseline_manifest_sha256,
        "delta_manifest_path": "research/bootstrap/wikidata/sl0018-2500/manifest.json",
        "delta_manifest_sha256": boundary.delta_manifest_sha256,
        "canonical_boat_model_count": boundary.canonical_boat_model_count,
        "historical_crosswalk_count": boundary.historical_crosswalk_count,
    }
    if dict(selection_document.get("identity_boundary", {})) != expected_boundary:
        problems.append("retained selection.identity_boundary != live reproduced boundary")

    pilot_size = selection_document.get("pilot_size")
    if not isinstance(pilot_size, int):
        problems.append("retained selection.pilot_size is missing or not an integer")
        return problems

    expected_selection = select_pilot_boatmodels(boundary, count=pilot_size)
    expected_rows = [
        {"hullq_id": m.hullq_id, "qid": m.qid, "preferred_label": m.preferred_label}
        for m in expected_selection
    ]
    if list(selection_document.get("boat_models", [])) != expected_rows:
        problems.append(
            "retained selection.boat_models != independently rebuilt selection from the live "
            "reproduced boundary via select_pilot_boatmodels"
        )
    return problems


def _evidence_row(ev: FieldEvidence) -> dict[str, Any]:
    return {
        "evidence_id": ev.evidence_id,
        "field_pointer": str(ev.field_pointer),
        "subject_kind": str(ev.subject.kind),
        "subject_qid": ev.subject.id,
        "raw": {
            "kind": str(ev.raw.kind),
            "value": ev.raw.value,
            "unit": ev.raw.unit,
        },
        "normalized_candidate": (
            {
                "value": str(ev.normalized_candidate.value),
                "unit": str(ev.normalized_candidate.unit),
            }
            if ev.normalized_candidate is not None
            else None
        ),
    }


def _boat_model_evidence_rows(
    selection: Sequence[PilotBoatModel],
    allowed_evidence_by_qid: Mapping[str, Sequence[FieldEvidence]],
) -> list[dict[str, Any]]:
    return [
        {
            "hullq_id": model.hullq_id,
            "qid": model.qid,
            "bundle_id": f"BUNDLE-SL0026-{model.qid}",
            "evidence": [_evidence_row(ev) for ev in allowed_evidence_by_qid.get(model.qid, ())],
        }
        for model in selection
    ]


def _raw_entity_row(entity: WikidataEntityData) -> dict[str, Any]:
    """Retained raw-entity row: enough of the acquired entity to fully
    reconstruct a ``WikidataEntityData`` and rerun extraction/coverage
    classification offline, trimmed to only the four Wikidata properties any
    of the five allowed fields can ever be extracted from."""
    return {
        "qid": entity.qid,
        "label": entity.label,
        "aliases": list(entity.aliases),
        "raw_claims": trim_raw_claims_to_allowed_properties(entity.raw_claims),
    }


def rebuild_entities_from_manifest(
    evidence_manifest: Mapping[str, Any],
) -> list[WikidataEntityData]:
    """Reconstruct the exact ``WikidataEntityData`` list used to produce a
    retained ``evidence_manifest.json``, purely from its own retained
    ``raw_entities`` — zero network access.
    """
    return [
        WikidataEntityData(
            qid=row["qid"],
            label=row["label"],
            aliases=list(row["aliases"]),
            raw_claims=dict(row["raw_claims"]),
        )
        for row in evidence_manifest.get("raw_entities", [])
    ]


def build_evidence_manifest_document(
    *,
    generated_at: str,
    acquired_at: str,
    selection: Sequence[PilotBoatModel],
    entities: Sequence[WikidataEntityData],
    allowed_evidence_by_qid: Mapping[str, Sequence[FieldEvidence]],
    coverage_counts: Mapping[str, Mapping[str, int]],
    quality_report: WikidataQualityReport,
    requested_qid_count: int,
) -> dict[str, Any]:
    """Assemble the retained ``evidence_manifest.json`` document: normalized
    per-BoatModel evidence rows (raw representation + normalized candidate,
    when present), per-field coverage counts, request/record counts, and the
    trimmed raw-entity data needed to fully reproduce all of the above with
    zero network access (see ``rebuild_entities_from_manifest`` /
    ``verify_evidence_manifest_self_consistency``).

    Preserves the distinction between the source technical subject
    (BoatDesign-shaped, QID-keyed) and canonical BoatModel identity: each row
    carries both ``hullq_id`` (the pilot BoatModel link) and the evidence's
    own untouched ``subject_qid``.
    """
    return {
        "schema_version": EVIDENCE_MANIFEST_SCHEMA_VERSION,
        "generated_at": generated_at,
        "acquired_at": acquired_at,
        "source_id": WIKIDATA_SOURCE_ID,
        "activity_id": SL0026_ACTIVITY_ID,
        "allowed_field_pointers": [str(p) for p in ALLOWED_FIELD_POINTERS],
        "usage_metrics": {
            "requested_qid_count": requested_qid_count,
            "fetched_entity_count": len(entities),
            "retrieval_count_attributed": quality_report.retrieval_count_attributed,
        },
        "quality_report_global": {
            "malformed_statement_count": quality_report.malformed_statement_count,
            "unsupported_qualifier_count": quality_report.unsupported_qualifier_count,
            "note": (
                "Global totals produced directly by the existing adapter's "
                "extract_field_evidence across ALL extracted properties (including "
                "manufacturer/designer/ballast/total_produced, which are not part of this "
                "pilot's five allowed fields) — not decomposed per field. Per-field "
                "unsupported/malformed counts are reported separately below in "
                "field_coverage."
            ),
        },
        "field_coverage": dict(coverage_counts),
        "boat_models": _boat_model_evidence_rows(selection, allowed_evidence_by_qid),
        "raw_entities": [_raw_entity_row(e) for e in entities],
    }


def verify_evidence_manifest_self_consistency(
    *,
    selection: Sequence[PilotBoatModel],
    entities: Sequence[WikidataEntityData],
    full_evidence: Sequence[FieldEvidence],
    evidence_manifest: Mapping[str, Any],
) -> list[str]:
    """Independently rebuild the expected coverage counts and per-BoatModel
    evidence rows purely from *entities*/*full_evidence* and compare against
    a retained ``evidence_manifest.json`` document.

    The caller obtains *entities*/*full_evidence* with zero network access by
    calling ``rebuild_entities_from_manifest(evidence_manifest)`` and rerunning
    the existing adapter's ``extract_field_evidence`` on the result — never by
    trusting the manifest's own already-computed ``field_coverage``/
    ``boat_models`` fields, so a tampered summary field cannot silently
    validate itself.
    """
    problems: list[str] = []

    expected_counts, _details = summarize_field_coverage(entities, full_evidence)
    if dict(evidence_manifest.get("field_coverage", {})) != expected_counts:
        problems.append(
            "retained evidence_manifest.field_coverage != independently recomputed "
            "summarize_field_coverage(entities, full_evidence)"
        )

    allowed = filter_to_allowed_evidence(full_evidence)
    by_qid: dict[str, list[FieldEvidence]] = {}
    for ev in allowed:
        by_qid.setdefault(ev.subject.id, []).append(ev)

    expected_rows = _boat_model_evidence_rows(selection, by_qid)
    if list(evidence_manifest.get("boat_models", [])) != expected_rows:
        problems.append(
            "retained evidence_manifest.boat_models != independently rebuilt evidence rows "
            "from the already-acquired entities/evidence"
        )

    expected_raw_entities = [_raw_entity_row(e) for e in entities]
    if list(evidence_manifest.get("raw_entities", [])) != expected_raw_entities:
        problems.append(
            "retained evidence_manifest.raw_entities != independently rebuilt raw-entity rows "
            "from the already-acquired entities"
        )

    return problems
