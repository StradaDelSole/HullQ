"""Wikidata qualifier-semantics correction + offline replay — SLICE-0027.

Implements the pure, deterministic logic described in
``docs/slices/SLICE-0027-wikidata-qualifier-semantics-correction-offline-replay.md``.

Given only the already-accepted, unmodified SLICE-0026 retained package
(``research/stage3/sl0026-wikidata-tier1-enrichment/``), this module:

- offline-verifies that retained package reproduces exactly the extraction
  behavior it originally captured (pinned to
  ``hullq.sources.wikidata.QUALIFIER_CARRIER_VERSION_SLICE0008``), failing
  closed on any digest/schema/self-consistency drift, before deriving or
  replaying anything;
- reproduces the exact 100-BoatModel / 100-QID retained input boundary from
  that package;
- deterministically characterizes every (statement property, qualifier
  property, qualifier-value QID) combination present on the retained raw
  claims for the three shared/qualified Wikidata measurement properties the
  five allowed fields use (P2043, P2048, P2067), distinguishing evidence-
  backed accepted carriers from unsupported shapes;
- replays the exact retained 100 entities offline through the SLICE-0027-
  amended adapter default (``QUALIFIER_CARRIER_VERSION_SLICE0027``) to
  produce independently-recomputed "after" per-field coverage, alongside the
  retained SLICE-0026 "before" coverage, for the same four mutually
  exclusive coverage states;
- assembles one ``ResearchEvidenceBundle`` per pilot BoatModel from the
  amended ("after") evidence for persistence via the existing SLICE-0013
  importer;
- assembles the retained qualifier-shape-analysis/coverage-before-after/
  artifact-digest documents and their offline self-consistency verification.

Explicitly does NOT:
- perform any network acquisition or SPARQL/discovery query;
- mutate or regenerate the accepted SLICE-0026 retained package;
- infer, mint or persist a canonical BoatDesign generation;
- create or mutate a canonical BoatModel/crosswalk row;
- reimplement Wikidata qualifier/unit extraction (qualifier-shape counting
  uses only the adapter's own qualifier-snak QID reader and the single
  ``QUALIFIER_CARRIERS_BY_VERSION`` source of truth already defined on the
  adapter — never a second parser).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from hullq.bootstrap import wikidata_sl0026_tier1_enrichment_pilot as sl0026
from hullq.domain.provenance import FieldEvidence
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import ResearchEvidenceBundle, migrate_evidence_v02_to_v03
from hullq.sources import wikidata as _wikidata_adapter_module
from hullq.sources.wikidata import (
    DEFAULT_QUALIFIER_CARRIER_VERSION,
    QUALIFIER_CARRIER_VERSION_SLICE0008,
    QUALIFIER_CARRIERS_BY_VERSION,
    WIKIDATA_SOURCE_ID,
    WikidataAdapter,
    WikidataAdapterConfig,
    WikidataEntityData,
    WikidataQualityReport,
)

__all__ = [
    "ARTIFACT_DIGESTS_FILENAME",
    "ARTIFACT_DIGESTS_SCHEMA_VERSION",
    "COVERAGE_BEFORE_AFTER_SCHEMA_VERSION",
    "QUALIFIER_SHAPE_ANALYSIS_SCHEMA_VERSION",
    "SL0026_PACKAGE_DIR",
    "SL0027_ACTIVITY_ID",
    "QualifierShapeCount",
    "RetainedSl0026Package",
    "Sl0026RetainedPackageIntegrityError",
    "analyze_qualifier_shapes",
    "build_artifact_digests",
    "build_coverage_before_after_document",
    "build_qualifier_shape_analysis_document",
    "build_sl0027_pilot_bundle",
    "compute_after_extraction",
    "load_and_verify_retained_sl0026_package",
    "retained_package_filenames",
    "verify_artifact_digests_self_consistency",
    "verify_coverage_before_after_self_consistency",
    "verify_qualifier_shape_analysis_self_consistency",
]

ROOT = Path(__file__).resolve().parents[3]
SL0026_PACKAGE_DIR = ROOT / "research" / "stage3" / "sl0026-wikidata-tier1-enrichment"

SL0027_ACTIVITY_ID = "SLICE-0027-QUALIFIER-SEMANTICS-CORRECTION"

EXPECTED_PILOT_SIZE = sl0026.PILOT_SIZE  # 100, reused not re-pinned separately.

# The three Wikidata measurement properties the five allowed fields share
# and/or require qualifier disambiguation on (P2043 length: LOA/LWL; P2048
# height: draft; P2067 mass: displacement/ballast). Beam's underlying
# property (P2049) needs no qualifier disambiguation in the accepted adapter
# and is out of scope for this analysis.
_SHARED_QUALIFIED_PROPERTIES: tuple[str, ...] = (
    _wikidata_adapter_module._PROP_LENGTH,
    _wikidata_adapter_module._PROP_HEIGHT,
    _wikidata_adapter_module._PROP_MASS,
)


# ---------------------------------------------------------------------------
# 1. Offline verification of the accepted, unmodified SLICE-0026 retained
#    package — reproducing exactly the extraction behavior it captured.
# ---------------------------------------------------------------------------


class Sl0026RetainedPackageIntegrityError(RuntimeError):
    """Raised when the accepted SLICE-0026 retained package does not verify
    offline (digest/schema/self-consistency drift), or the exact 100-
    BoatModel / 100-QID input boundary does not reproduce.

    SLICE-0027 MUST fail closed (BLOCKED) rather than derive or replay
    anything against a drifted retained package.
    """


@dataclass(frozen=True)
class RetainedSl0026Package:
    """The offline-verified accepted SLICE-0026 retained package, reproduced
    purely from its own retained artifacts with zero network access."""

    selection_document: Mapping[str, Any]
    evidence_manifest: Mapping[str, Any]
    selection: tuple[sl0026.PilotBoatModel, ...]
    entities: tuple[WikidataEntityData, ...]


def _offline_adapter(user_agent: str) -> WikidataAdapter:
    """Construct a WikidataAdapter for pure offline re-extraction only.

    The injected httpx.Client is never used for a network request by any
    caller in this module — only the adapter's pure
    ``extract_field_evidence`` is invoked.
    """
    source = {"source_id": WIKIDATA_SOURCE_ID}
    config = WikidataAdapterConfig(user_agent=user_agent)
    return WikidataAdapter(source=source, config=config, http_client=httpx.Client())


def load_and_verify_retained_sl0026_package(
    *,
    package_dir: Path = SL0026_PACKAGE_DIR,
    boundary: sl0026.IdentityBoundary | None = None,
    expected_size: int = EXPECTED_PILOT_SIZE,
) -> RetainedSl0026Package:
    """Load and offline-verify the accepted SLICE-0026 retained package.

    Fails closed via ``Sl0026RetainedPackageIntegrityError`` unless ALL of
    the following hold:

    - the SLICE-0017+0018 identity boundary reproduces at the accepted
      1,770/1,772 counts (``load_reproduced_identity_boundary`` itself fails
      closed on drift);
    - the retained ``selection.json`` reproduces exactly from that boundary;
    - re-extracting ``FieldEvidence`` from the retained ``raw_entities`` with
      the extraction behavior SLICE-0026 originally captured
      (``QUALIFIER_CARRIER_VERSION_SLICE0008`` — never the SLICE-0027-amended
      default) reproduces the retained ``evidence_manifest.json`` exactly;
    - every retained package file's SHA256 matches ``ARTIFACT-DIGESTS.json``;
    - the reproduced selection/entities are exactly ``expected_size`` distinct
      BoatModels and distinct QIDs.

    ``boundary``/``expected_size`` default to the real accepted SLICE-0017+
    0018 identity boundary and the real pilot size (100) but may be
    overridden (e.g. by ``tests/persistence/``) to exercise this exact
    mechanism against a small synthetic SLICE-0026-shaped package without
    touching the real retained artifacts or the real identity-boundary
    manifests.

    Performs no network access and never mutates any SLICE-0026 retained
    file.
    """
    problems: list[str] = []

    selection_path = package_dir / "selection.json"
    evidence_manifest_path = package_dir / "evidence_manifest.json"
    artifact_digests_path = package_dir / "ARTIFACT-DIGESTS.json"
    for required_path in (selection_path, evidence_manifest_path, artifact_digests_path):
        if not required_path.is_file():
            raise Sl0026RetainedPackageIntegrityError(
                f"required retained SLICE-0026 file not found: {required_path}"
            )

    selection_doc = json.loads(selection_path.read_text(encoding="utf-8"))
    evidence_manifest = json.loads(evidence_manifest_path.read_text(encoding="utf-8"))
    artifact_digests = json.loads(artifact_digests_path.read_text(encoding="utf-8"))

    boundary = boundary if boundary is not None else sl0026.load_reproduced_identity_boundary()
    problems.extend(
        sl0026.verify_selection_self_consistency(
            boundary=boundary, selection_document=selection_doc
        )
    )

    selection = tuple(
        sl0026.PilotBoatModel(
            hullq_id=row["hullq_id"], qid=row["qid"], preferred_label=row["preferred_label"]
        )
        for row in selection_doc.get("boat_models", [])
    )
    entities = tuple(sl0026.rebuild_entities_from_manifest(evidence_manifest))

    adapter = _offline_adapter("HullQ/0.1 (sl0027-offline-verify@example.org)")
    full_evidence, _report = adapter.extract_field_evidence(
        list(entities),
        evidence_manifest.get("acquired_at", ""),
        requested_qid_count=len(entities),
        qualifier_carrier_version=QUALIFIER_CARRIER_VERSION_SLICE0008,
    )
    problems.extend(
        sl0026.verify_evidence_manifest_self_consistency(
            selection=selection,
            entities=list(entities),
            full_evidence=full_evidence,
            evidence_manifest=evidence_manifest,
        )
    )
    problems.extend(
        sl0026.verify_artifact_digests_self_consistency(
            artifact_digests=artifact_digests, package_dir=package_dir
        )
    )

    if len(selection) != expected_size:
        problems.append(
            f"retained selection has {len(selection)} BoatModels; expected exactly {expected_size}"
        )
    if len({m.hullq_id for m in selection}) != expected_size:
        problems.append(
            f"retained selection BoatModel IDs are not exactly {expected_size} distinct"
        )
    if len({m.qid for m in selection}) != expected_size:
        problems.append(f"retained selection QIDs are not exactly {expected_size} distinct")
    if len(entities) != expected_size:
        problems.append(
            f"retained evidence_manifest has {len(entities)} raw entities; expected exactly "
            f"{expected_size}"
        )

    if problems:
        raise Sl0026RetainedPackageIntegrityError(
            "SLICE-0026 retained package failed offline verification: " + "; ".join(problems)
        )

    return RetainedSl0026Package(
        selection_document=selection_doc,
        evidence_manifest=evidence_manifest,
        selection=selection,
        entities=entities,
    )


# ---------------------------------------------------------------------------
# 2. Deterministic qualifier-shape analysis over the retained raw claims
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QualifierShapeCount:
    """One observed (statement property, qualifier property, qualifier-value
    QID) combination and its retained-sample occurrence count."""

    statement_property: str
    qualifier_property: str
    qualifier_value_qid: str
    count: int
    recognized: bool
    mapped_field: str | None


def analyze_qualifier_shapes(
    entities: Sequence[WikidataEntityData],
    *,
    qualifier_carrier_version: str = DEFAULT_QUALIFIER_CARRIER_VERSION,
) -> tuple[QualifierShapeCount, ...]:
    """Deterministically count every (statement property, qualifier
    property, qualifier-value QID) combination present in *entities*' raw
    claims for the three shared/qualified properties, and classify each as
    ``recognized`` (an evidence-backed accepted carrier for an already-
    accepted concept QID, per ``QUALIFIER_CARRIERS_BY_VERSION``) or not.

    Uses only the adapter's own plain qualifier-snak QID reader
    (``_get_qualifier_qids``) and counting — never a new statement/unit
    parser. Iterates qualifier property keys in sorted order per claim so the
    result is deterministic regardless of the source JSON's key order.
    """
    counts: dict[tuple[str, str, str], int] = {}
    for entity in entities:
        for prop_id in _SHARED_QUALIFIED_PROPERTIES:
            claims = entity.raw_claims.get(prop_id, [])
            if not isinstance(claims, list):
                continue
            for claim in claims:
                if not isinstance(claim, dict):
                    continue
                qualifiers = claim.get("qualifiers", {})
                if not isinstance(qualifiers, dict):
                    continue
                for qualifier_property in sorted(qualifiers):
                    qids = _wikidata_adapter_module._get_qualifier_qids(
                        qualifiers, qualifier_property
                    )
                    for qid_value in qids:
                        key = (prop_id, qualifier_property, qid_value)
                        counts[key] = counts.get(key, 0) + 1

    accepted = QUALIFIER_CARRIERS_BY_VERSION[qualifier_carrier_version]
    results: list[QualifierShapeCount] = []
    for (prop_id, qualifier_property, qid_value), count in sorted(counts.items()):
        recognized = False
        mapped_field: str | None = None
        for carrier_qualifier_property, concept_map in accepted.get(prop_id, ()):
            if carrier_qualifier_property == qualifier_property and qid_value in concept_map:
                recognized = True
                mapped_field = concept_map[qid_value]
                break
        results.append(
            QualifierShapeCount(
                statement_property=prop_id,
                qualifier_property=qualifier_property,
                qualifier_value_qid=qid_value,
                count=count,
                recognized=recognized,
                mapped_field=mapped_field,
            )
        )
    return tuple(results)


QUALIFIER_SHAPE_ANALYSIS_SCHEMA_VERSION = "sl0027-qualifier-shape-analysis-v1"


def build_qualifier_shape_analysis_document(
    *, generated_at: str, shapes: Sequence[QualifierShapeCount]
) -> dict[str, Any]:
    """Assemble the retained ``qualifier_shape_analysis.json`` document."""
    return {
        "schema_version": QUALIFIER_SHAPE_ANALYSIS_SCHEMA_VERSION,
        "generated_at": generated_at,
        "source_id": WIKIDATA_SOURCE_ID,
        "analyzed_statement_properties": list(_SHARED_QUALIFIED_PROPERTIES),
        "note": (
            "Deterministic characterization of every (statement property, qualifier "
            "property, qualifier-value QID) combination observed on the accepted, "
            "unmodified SLICE-0026 retained raw claims for the three shared/qualified "
            "Wikidata measurement properties the five allowed fields use (P2043 length: "
            "LOA/LWL; P2048 height: draft; P2067 mass: displacement/ballast). Beam (P2049) "
            "needs no qualifier disambiguation in the accepted adapter and is excluded. "
            "'recognized'=true means the exact combination is an evidence-backed accepted "
            "carrier for an already-accepted concept QID (see "
            "hullq.sources.wikidata.QUALIFIER_CARRIERS_BY_VERSION); 'recognized'=false "
            "combinations remain unsupported, never guessed."
        ),
        "shapes": [
            {
                "statement_property": s.statement_property,
                "qualifier_property": s.qualifier_property,
                "qualifier_value_qid": s.qualifier_value_qid,
                "count": s.count,
                "recognized": s.recognized,
                "mapped_field": s.mapped_field,
            }
            for s in shapes
        ],
    }


def verify_qualifier_shape_analysis_self_consistency(
    *, entities: Sequence[WikidataEntityData], document: Mapping[str, Any]
) -> list[str]:
    """Independently rebuild the expected qualifier-shape analysis purely
    from *entities* and compare against a retained
    ``qualifier_shape_analysis.json`` document."""
    expected = build_qualifier_shape_analysis_document(
        generated_at=str(document.get("generated_at", "")),
        shapes=analyze_qualifier_shapes(entities),
    )
    if dict(document) != expected:
        return [
            "retained qualifier_shape_analysis.json != independently recomputed "
            "analyze_qualifier_shapes(entities)"
        ]
    return []


# ---------------------------------------------------------------------------
# 3. Before/after coverage over the exact retained 100-entity sample
# ---------------------------------------------------------------------------


def compute_after_extraction(
    entities: Sequence[WikidataEntityData], *, acquired_at: str
) -> tuple[tuple[FieldEvidence, ...], WikidataQualityReport]:
    """Re-extract FieldEvidence from *entities* offline using the SLICE-0027-
    amended adapter default (``DEFAULT_QUALIFIER_CARRIER_VERSION`` ==
    ``QUALIFIER_CARRIER_VERSION_SLICE0027``). Zero network access."""
    adapter = _offline_adapter("HullQ/0.1 (sl0027-replay@example.org)")
    full_evidence, report = adapter.extract_field_evidence(
        list(entities),
        acquired_at,
        requested_qid_count=len(entities),
        qualifier_carrier_version=DEFAULT_QUALIFIER_CARRIER_VERSION,
    )
    return tuple(full_evidence), report


COVERAGE_BEFORE_AFTER_SCHEMA_VERSION = "sl0027-coverage-before-after-v1"


def build_coverage_before_after_document(
    *,
    generated_at: str,
    sample_size: int,
    before_counts: Mapping[str, Mapping[str, int]],
    after_counts: Mapping[str, Mapping[str, int]],
) -> dict[str, Any]:
    """Assemble the retained ``coverage_before_after.json`` document."""
    fields = {
        label: {"before": dict(before_counts[label]), "after": dict(after_counts[label])}
        for label in sl0026.FIELD_LABEL_BY_POINTER.values()
    }
    return {
        "schema_version": COVERAGE_BEFORE_AFTER_SCHEMA_VERSION,
        "generated_at": generated_at,
        "sample_size": sample_size,
        "note": (
            "'before' is the accepted SLICE-0026 retained evidence_manifest.json's own "
            "field_coverage, computed with the P642-only qualifier carriers in force at "
            "SLICE-0026 acceptance (QUALIFIER_CARRIER_VERSION_SLICE0008). 'after' is "
            "independently recomputed over the identical retained 100-entity raw claims "
            "using the SLICE-0027-amended adapter default (QUALIFIER_CARRIER_VERSION_SLICE0027), "
            "which additionally recognizes evidence-backed P518/P3831 alternate carriers for "
            "the same already-accepted concept QIDs, on top of (never instead of) the existing "
            "accepted P642 path. Four mutually exclusive, exhaustive coverage states per "
            "(BoatModel, field); counts sum to sample_size for every field, in both before "
            "and after."
        ),
        "fields": fields,
    }


def verify_coverage_before_after_self_consistency(
    *,
    before_counts: Mapping[str, Mapping[str, int]],
    entities: Sequence[WikidataEntityData],
    after_full_evidence: Sequence[FieldEvidence],
    document: Mapping[str, Any],
) -> list[str]:
    """Independently recompute "after" coverage from *entities*/
    *after_full_evidence* and compare the full before/after document against
    a retained ``coverage_before_after.json`` document."""
    after_counts, _details = sl0026.summarize_field_coverage(entities, after_full_evidence)
    expected = build_coverage_before_after_document(
        generated_at=str(document.get("generated_at", "")),
        sample_size=len(entities),
        before_counts=before_counts,
        after_counts=after_counts,
    )
    if dict(document) != expected:
        return [
            "retained coverage_before_after.json != independently recomputed before/after "
            "coverage over entities/after_full_evidence"
        ]
    return []


# ---------------------------------------------------------------------------
# 4. Research evidence bundle assembly (amended/"after" evidence)
# ---------------------------------------------------------------------------


def build_sl0027_pilot_bundle(
    pilot_model: sl0026.PilotBoatModel, allowed_evidence_for_qid: Sequence[FieldEvidence]
) -> ResearchEvidenceBundle:
    """Build the retained ``ResearchEvidenceBundle`` for one pilot BoatModel
    from the amended ("after") evidence.

    Identical construction contract to
    ``hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot.build_pilot_bundle``
    (BoatDesign-shaped, QID-keyed subject; existing SLICE-0012
    ``migrate_evidence_v02_to_v03`` promotion; empty bundle valid), but with a
    distinct ``bundle_id``/``activity_id`` namespace (``BUNDLE-SL0027-*`` /
    ``SL0027_ACTIVITY_ID``) so persisting the amended SLICE-0027 evidence
    never collides with or overwrites the already-imported SLICE-0026
    ``BUNDLE-SL0026-*`` bundles.
    """
    for ev in allowed_evidence_for_qid:
        if ev.subject.id != pilot_model.qid:
            raise ValueError(
                f"Evidence subject id {ev.subject.id!r} does not match pilot BoatModel QID "
                f"{pilot_model.qid!r}"
            )
        if ev.field_pointer not in sl0026.ALLOWED_FIELD_POINTERS:
            raise ValueError(
                f"Evidence field_pointer {ev.field_pointer!r} is not one of the five allowed "
                "Tier-1 field pointers"
            )

    promoted = tuple(migrate_evidence_v02_to_v03(ev) for ev in allowed_evidence_for_qid)
    return ResearchEvidenceBundle(
        bundle_id=f"BUNDLE-SL0027-{pilot_model.qid}",
        bundle_version="1",
        research_target=ResearchTarget(
            manufacturer=None,
            model=pilot_model.preferred_label or pilot_model.qid,
            first_built=None,
        ),
        research_job_id=None,
        activity_id=SL0027_ACTIVITY_ID,
        observations=(),
        unresolved_findings=(),
        promoted_evidence=promoted,
        reference_crosschecks=(),
    )


# ---------------------------------------------------------------------------
# 5. Retained-package artifact-integrity digests
# ---------------------------------------------------------------------------

ARTIFACT_DIGESTS_SCHEMA_VERSION = "sl0027-artifact-digests-v1"
ARTIFACT_DIGESTS_FILENAME = "ARTIFACT-DIGESTS.json"


def retained_package_filenames(package_dir: Path) -> set[str]:
    """Every regular file directly inside *package_dir* except the digest
    document itself, discovered dynamically (never a hardcoded allowlist)."""
    return {
        p.name for p in package_dir.iterdir() if p.is_file() and p.name != ARTIFACT_DIGESTS_FILENAME
    }


def build_artifact_digests(*, generated_at: str, package_dir: Path) -> dict[str, Any]:
    """Build the retained ``ARTIFACT-DIGESTS.json`` document: a SHA256 digest
    of every retained SLICE-0027 package file except the digest document
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
