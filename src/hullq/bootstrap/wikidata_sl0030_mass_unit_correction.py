"""Wikidata mass-unit QID correction + full-boundary offline replay — SLICE-0030.

Implements the pure, deterministic logic described in
``docs/slices/SLICE-0030-wikidata-mass-unit-qid-correction-full-boundary-offline-replay.md``.

Given only:

- a small, fixed, bounded live entity-identity snapshot for the seven fixed
  Wikidata mass-unit QIDs the controlling slice names (retained once, then
  offline-reproducible forever — see ``build_unit_qid_assessment_document`` /
  ``verify_unit_qid_assessment_self_consistency``);
- the already-accepted, unmodified SLICE-0028 retained package
  (``research/stage3/sl0028-wikidata-tier1-full-boundary/``), used exactly as
  the fixed full-boundary replay input (no reacquisition, no new discovery);

this module measures the exact displacement-coverage effect of the
SLICE-0030 mass-unit-map correction (``hullq.sources.wikidata.
UNIT_QID_MAP_VERSION_SLICE0030`` vs the legacy ``UNIT_QID_MAP_VERSION_SLICE0008``)
over the fixed 1,770-entity boundary, with zero network access after the
identity snapshot has been retained, zero canonical BoatModel/BoatDesign
mutation, and zero mutation of any accepted SLICE-0026/0027/0028/0029
retained package.

Explicitly does NOT:
- reacquire the 1,770-QID full-boundary dataset or run a new discovery query;
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
from hullq.domain.provenance import FieldEvidence
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import ResearchEvidenceBundle, migrate_evidence_v02_to_v03
from hullq.sources.wikidata import (
    DEFAULT_UNIT_QID_MAP_VERSION,
    UNIT_QID_MAP_VERSION_SLICE0008,
    WikidataEntityData,
)

__all__ = [
    "ARTIFACT_DIGESTS_FILENAME",
    "ARTIFACT_DIGESTS_SCHEMA_VERSION",
    "COVERAGE_BEFORE_AFTER_SCHEMA_VERSION",
    "FIXED_UNIT_QIDS",
    "SL0030_ACTIVITY_ID",
    "UNIT_QID_ASSESSMENT_SCHEMA_VERSION",
    "VERIFIED_MASS_UNIT_INSTANCE_QID",
    "UnitEntitySnapshot",
    "UnitIdentityValidationError",
    "build_artifact_digests",
    "build_coverage_before_after_document",
    "build_sl0030_bundle",
    "build_unit_qid_assessment_document",
    "compute_before_after_coverage",
    "count_mass_unit_qid_occurrences",
    "retained_package_filenames",
    "validate_unit_qid_snapshots",
    "verify_artifact_digests_self_consistency",
    "verify_coverage_before_after_self_consistency",
    "verify_unit_qid_assessment_self_consistency",
]

SL0030_ACTIVITY_ID = "SLICE-0030-MASS-UNIT-CORRECTION"

# Reused directly (not redefined) from the accepted SLICE-0026 pilot module.
ALLOWED_FIELD_POINTERS = sl0026.ALLOWED_FIELD_POINTERS
FIELD_LABEL_BY_POINTER = sl0026.FIELD_LABEL_BY_POINTER

_WIKIDATA_ENTITY_URL = "https://www.wikidata.org/entity/{qid}"

# ---------------------------------------------------------------------------
# 1. Unit-QID identity assessment
# ---------------------------------------------------------------------------

# The exact, fixed unit-QID set the controlling slice authorizes assessment
# of — the four corrected/default mass units plus the three rejected legacy
# QIDs. Never expanded by discovery; any QID outside this fixed set is out of
# scope for SLICE-0030 by contract.
FIXED_UNIT_QIDS: tuple[str, ...] = (
    "Q11570",
    "Q41803",
    "Q191118",
    "Q100995",
    "Q12152",
    "Q11369",
    "Q37795",
)

_CLASSIFICATION_BY_QID: dict[str, str] = {
    "Q11570": "correct_existing_mapping",
    "Q41803": "corrected_positively_verified_mapping",
    "Q191118": "corrected_positively_verified_mapping",
    "Q100995": "corrected_positively_verified_mapping",
    "Q12152": "incorrect_legacy_mapping",
    "Q11369": "incorrect_legacy_mapping",
    "Q37795": "incorrect_legacy_mapping",
}

_INTENDED_UNIT_ENUM_BY_QID: dict[str, str | None] = {
    "Q11570": "MassUnit.KILOGRAM",
    "Q41803": "MassUnit.GRAM",
    "Q191118": "MassUnit.METRIC_TONNE",
    "Q100995": "MassUnit.POUND",
    "Q12152": None,
    "Q11369": None,
    "Q37795": None,
}

# Wikidata "unit of mass" (https://www.wikidata.org/entity/Q3647172) —
# positively confirmed via a live wbgetentities lookup: label="unit of mass",
# description="physical unit which measures mass". This is the fail-closed,
# structural (P31/instance-of) criterion for "is a Wikidata mass unit",
# independent of and stronger than the entity's label — a label alone
# (e.g. "gram") is supporting evidence only, never the sole criterion.
VERIFIED_MASS_UNIT_INSTANCE_QID = "Q3647172"

# What FIXED_UNIT_QIDS is expected to positively verify as, per the
# controlling slice's required corrected/rejected boundary. Independent
# review requirement: this expectation must be checked against the live P31
# evidence before classification/intended_hullq_unit are ever assigned from
# _CLASSIFICATION_BY_QID / _INTENDED_UNIT_ENUM_BY_QID — those static tables
# encode the *intended* SLICE-0030 decision, not a substitute for verifying
# the actually-fetched entity matches it.
_EXPECTED_IS_MASS_UNIT_BY_QID: dict[str, bool] = {
    "Q11570": True,
    "Q41803": True,
    "Q191118": True,
    "Q100995": True,
    "Q12152": False,
    "Q11369": False,
    "Q37795": False,
}


class UnitIdentityValidationError(ValueError):
    """Raised when a fixed unit QID's live-verified P31 evidence contradicts
    the physical-unit identity SLICE-0030 is about to assign it.

    Fail-closed: no unit_qid_assessment.json document is ever built (live or
    replayed offline) while this condition holds — a contradictory or
    ambiguous Wikidata response must stop BLOCKED rather than being silently
    retained/reported as positively verified.
    """


def _snapshot_is_verified_mass_unit(snap: UnitEntitySnapshot) -> bool:
    """Structural, evidence-backed criterion: does *snap*'s live-retrieved
    P31 (instance-of) claim set include ``VERIFIED_MASS_UNIT_INSTANCE_QID``?
    """
    return VERIFIED_MASS_UNIT_INSTANCE_QID in snap.p31_qids


def validate_unit_qid_snapshots(snapshots: Sequence[UnitEntitySnapshot]) -> None:
    """Fail-closed identity validator.

    Raises ``UnitIdentityValidationError`` if any snapshot in *snapshots*
    whose QID is a member of ``_EXPECTED_IS_MASS_UNIT_BY_QID`` has live P31
    evidence that disagrees with that expectation — e.g. a QID SLICE-0030
    intends to recognize as a mass unit whose fetched entity does NOT carry
    the ``VERIFIED_MASS_UNIT_INSTANCE_QID`` instance-of claim, or a QID
    SLICE-0030 intends to reject that unexpectedly DOES carry it. Called
    before every ``build_unit_qid_assessment_document`` construction — both
    the live ``--identity-check`` path and the offline
    ``verify_unit_qid_assessment_self_consistency`` replay path — so neither
    can ever retain or report a contradictory identity as verified.
    """
    problems = []
    for snap in snapshots:
        if snap.qid not in _EXPECTED_IS_MASS_UNIT_BY_QID:
            continue  # unknown QID is surfaced separately by the FIXED_UNIT_QIDS coverage check
        expected = _EXPECTED_IS_MASS_UNIT_BY_QID[snap.qid]
        actual = _snapshot_is_verified_mass_unit(snap)
        if actual != expected:
            problems.append(
                f"{snap.qid}: expected verified_is_unit_of_mass={expected} per the SLICE-0030 "
                f"classification, but live P31 evidence gives {actual} "
                f"(p31_qids={list(snap.p31_qids)!r}, label={snap.label!r})"
            )
    if problems:
        raise UnitIdentityValidationError(
            f"fail-closed unit-identity check failed for {len(problems)} QID(s): "
            + "; ".join(problems)
        )


@dataclass(frozen=True)
class UnitEntitySnapshot:
    """A retained, snapshot-safe live Wikidata identity check for one fixed
    unit QID: label, English description, and instance-of (P31) QIDs — enough
    to positively establish (or positively reject) the entity's physical
    identity as a unit, without collecting any broader boat-technical field.

    Retained verbatim in ``unit_qid_assessment.json`` so the SLICE-0030
    primary verifier can recompute the full assessment document from this
    snapshot alone, with zero further Wikidata access.
    """

    qid: str
    label: str | None
    description_en: str | None
    p31_qids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "p31_qids", tuple(self.p31_qids))


def count_mass_unit_qid_occurrences(
    entities: Sequence[WikidataEntityData], qids: Sequence[str] = FIXED_UNIT_QIDS
) -> dict[str, int]:
    """Deterministically count P2067 (mass) statements in *entities*' raw
    claims whose unit resolves to each of *qids*.

    A plain raw-claim scan over the literal Wikidata quantity-unit URI —
    deliberately independent of ``hullq.sources.wikidata.extract_field_evidence``
    so this occurrence count can never share a bug with the adapter's own
    unit-QID recognition logic it is being used to characterize.
    """
    counts = dict.fromkeys(qids, 0)
    target_uris = {
        q: _WIKIDATA_ENTITY_URL.format(qid=q).replace("https://", "http://") for q in qids
    }
    for entity in entities:
        for claim in entity.raw_claims.get("P2067", []) or []:
            if not isinstance(claim, dict):
                continue
            mainsnak = claim.get("mainsnak", {})
            if not isinstance(mainsnak, dict) or mainsnak.get("snaktype") != "value":
                continue
            datavalue = mainsnak.get("datavalue", {})
            if not isinstance(datavalue, dict) or datavalue.get("type") != "quantity":
                continue
            value_obj = datavalue.get("value", {})
            if not isinstance(value_obj, dict):
                continue
            unit_uri = value_obj.get("unit", "1")
            if not isinstance(unit_uri, str):
                continue
            for qid, target in target_uris.items():
                if unit_uri == target:
                    counts[qid] += 1
    return counts


UNIT_QID_ASSESSMENT_SCHEMA_VERSION = "sl0030-unit-qid-assessment-v1"


def build_unit_qid_assessment_document(
    *,
    generated_at: str,
    verified_at: str,
    snapshots: Sequence[UnitEntitySnapshot],
    occurrence_counts: Mapping[str, int],
) -> dict[str, Any]:
    """Assemble the retained ``unit_qid_assessment.json`` document: one row
    per fixed unit QID, combining the positively-verified live identity
    snapshot with its deterministic occurrence count in the fixed SLICE-0028
    retained raw claims.

    ``snapshots`` MUST cover exactly ``FIXED_UNIT_QIDS`` (no more, no fewer) —
    SLICE-0030 does not assess any QID outside this fixed set.

    Fail-closed: ``validate_unit_qid_snapshots`` is called before any row is
    assembled. If any snapshot's live P31 evidence contradicts the physical
    identity SLICE-0030 is about to assign it, this function raises
    ``UnitIdentityValidationError`` instead of returning a document — the
    static ``_CLASSIFICATION_BY_QID`` / ``_INTENDED_UNIT_ENUM_BY_QID`` tables
    encode the *intended* decision, never a substitute for checking it
    against what was actually fetched.
    """
    snapshot_qids = {s.qid for s in snapshots}
    if snapshot_qids != set(FIXED_UNIT_QIDS):
        raise ValueError(
            f"snapshots must cover exactly FIXED_UNIT_QIDS; missing="
            f"{sorted(set(FIXED_UNIT_QIDS) - snapshot_qids)!r} "
            f"unexpected={sorted(snapshot_qids - set(FIXED_UNIT_QIDS))!r}"
        )
    validate_unit_qid_snapshots(snapshots)
    rows = [
        {
            "qid": snap.qid,
            "wikidata_entity_locator": _WIKIDATA_ENTITY_URL.format(qid=snap.qid),
            "intended_hullq_unit": _INTENDED_UNIT_ENUM_BY_QID[snap.qid],
            "classification": _CLASSIFICATION_BY_QID[snap.qid],
            "verified_label_en": snap.label,
            "verified_description_en": snap.description_en,
            "verified_instance_of_qids": list(snap.p31_qids),
            "verified_unit_of_mass_instance_qid": VERIFIED_MASS_UNIT_INSTANCE_QID,
            "verified_is_unit_of_mass": _snapshot_is_verified_mass_unit(snap),
            "verification_retrieved_at": verified_at,
            "occurs_in_sl0028_retained_raw_claims": occurrence_counts.get(snap.qid, 0) > 0,
            "observed_retained_statement_count": occurrence_counts.get(snap.qid, 0),
        }
        for snap in sorted(snapshots, key=lambda s: s.qid)
    ]
    return {
        "schema_version": UNIT_QID_ASSESSMENT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "source_id": "SRC_WIKIDATA_API_2026",
        "note": (
            "One row per fixed SLICE-0030 unit QID (FIXED_UNIT_QIDS): a bounded, "
            "rights-gated wbgetentities identity check (label/description/P31 "
            "instance-of only — no broader boat-technical field is collected), "
            "combined with a deterministic count of P2067 mass statements in the "
            "fixed accepted SLICE-0028 retained raw claims whose unit resolves to "
            "this QID. classification is one of: correct_existing_mapping "
            "(Q11570/kilogram, unchanged since SLICE-0008), "
            "corrected_positively_verified_mapping (Q41803/Q191118/Q100995, newly "
            "recognized by the SLICE-0030 default map), incorrect_legacy_mapping "
            "(Q12152/Q11369/Q37795, recognized by the pre-SLICE-0030 default map "
            "but never the intended physical unit and never observed as a real "
            "unit reference in the fixed retained evidence). Fail-closed identity "
            "criterion (independent-review requirement): verified_is_unit_of_mass "
            "is true iff verified_instance_of_qids contains "
            "verified_unit_of_mass_instance_qid (Q3647172, Wikidata 'unit of "
            "mass') — a structural P31 check, not the label alone. "
            "validate_unit_qid_snapshots raises UnitIdentityValidationError "
            "before this document is built if any QID's expected "
            "classification (correct/corrected_positively_verified vs "
            "incorrect_legacy) disagrees with its verified_is_unit_of_mass "
            "value; this document could not have been produced or replayed "
            "if that check failed."
        ),
        "assessed_units": rows,
        "raw_entity_snapshots": [
            {
                "qid": snap.qid,
                "label": snap.label,
                "description_en": snap.description_en,
                "p31_qids": list(snap.p31_qids),
            }
            for snap in sorted(snapshots, key=lambda s: s.qid)
        ],
    }


def verify_unit_qid_assessment_self_consistency(
    *,
    sl0028_entities: Sequence[WikidataEntityData],
    document: Mapping[str, Any],
) -> list[str]:
    """Independently rebuild the expected ``unit_qid_assessment.json`` purely
    from its own retained ``raw_entity_snapshots`` (the one-time live identity
    check, never re-fetched) and a fresh occurrence-count scan over
    *sl0028_entities* (the fixed accepted SLICE-0028 retained raw claims), and
    compare against a retained ``unit_qid_assessment.json`` document.

    Zero network access: this is what makes the retained package's own
    identity-check result reproducible forever without re-querying Wikidata.

    Because this rebuild goes through ``build_unit_qid_assessment_document``
    unchanged, it re-runs ``validate_unit_qid_snapshots`` against the
    retained ``raw_entity_snapshots`` on every call — the same fail-closed
    identity criterion enforced at live acquisition time, never a second,
    weaker offline-only check. A retained snapshot whose P31 evidence would
    no longer satisfy that criterion is reported as a problem here (via the
    ``except ValueError`` below), not silently accepted.
    """
    raw_snapshots = document.get("raw_entity_snapshots", [])
    snapshots = tuple(
        UnitEntitySnapshot(
            qid=row["qid"],
            label=row.get("label"),
            description_en=row.get("description_en"),
            p31_qids=tuple(row.get("p31_qids", ())),
        )
        for row in raw_snapshots
    )
    occurrence_counts = count_mass_unit_qid_occurrences(sl0028_entities)
    try:
        expected = build_unit_qid_assessment_document(
            generated_at=str(document.get("generated_at", "")),
            verified_at=(
                raw_snapshots[0].get("verification_retrieved_at", "") if raw_snapshots else ""
            ),
            snapshots=snapshots,
            occurrence_counts=occurrence_counts,
        )
    except ValueError as exc:
        return [f"retained unit_qid_assessment.json snapshots are invalid: {exc}"]

    # verification_retrieved_at is retained per-row on the already-built
    # document (not on raw_entity_snapshots), so pull it from the retained
    # assessed_units instead of re-deriving a value this function has no
    # other source for.
    retained_rows = {row["qid"]: row for row in document.get("assessed_units", [])}
    for row in expected["assessed_units"]:
        retained = retained_rows.get(row["qid"], {})
        row["verification_retrieved_at"] = retained.get("verification_retrieved_at")

    if dict(document) != expected:
        return [
            "retained unit_qid_assessment.json != independently rebuilt assessment from its "
            "own raw_entity_snapshots and a fresh SLICE-0028 occurrence-count scan"
        ]
    return []


# ---------------------------------------------------------------------------
# 2. Before/after coverage over the fixed SLICE-0028 full-boundary entities
# ---------------------------------------------------------------------------

COVERAGE_BEFORE_AFTER_SCHEMA_VERSION = "sl0030-coverage-before-after-v1"


def compute_before_after_coverage(
    entities: Sequence[WikidataEntityData],
    full_evidence_before: Sequence[FieldEvidence],
    full_evidence_after: Sequence[FieldEvidence],
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]]:
    """Compute source-QID-level coverage counts for all five allowed fields
    under the legacy (*before*) and corrected (*after*) mass-unit maps,
    reusing the existing accepted
    ``hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot.summarize_field_coverage``
    classification unchanged.

    The fixed SLICE-0028 full-boundary linkage is bijective (exactly one
    accepted QID per canonical BoatModel), so source-QID-level and canonical-
    BoatModel-level coverage are numerically identical over this boundary —
    only the source-QID level is computed here to avoid retaining a
    duplicate, never-differing table.
    """
    before_counts, _ = sl0026.summarize_field_coverage(entities, full_evidence_before)
    after_counts, _ = sl0026.summarize_field_coverage(entities, full_evidence_after)
    return before_counts, after_counts


def build_coverage_before_after_document(
    *,
    generated_at: str,
    qid_count: int,
    before_counts: Mapping[str, Mapping[str, int]],
    after_counts: Mapping[str, Mapping[str, int]],
) -> dict[str, Any]:
    """Assemble the retained ``coverage_before_after.json`` document."""
    fields = {
        label: {"before": dict(before_counts[label]), "after": dict(after_counts[label])}
        for label in FIELD_LABEL_BY_POINTER.values()
    }
    displacement_delta = (
        after_counts["displacement"]["normalized_candidate_present"]
        - before_counts["displacement"]["normalized_candidate_present"]
    )
    non_displacement_unchanged = all(
        dict(before_counts[label]) == dict(after_counts[label])
        for label in FIELD_LABEL_BY_POINTER.values()
        if label != "displacement"
    )
    return {
        "schema_version": COVERAGE_BEFORE_AFTER_SCHEMA_VERSION,
        "generated_at": generated_at,
        "qid_count": qid_count,
        "note": (
            "Source-QID-level coverage over the fixed, unmodified accepted "
            "SLICE-0028 full-boundary raw claims (1,770 requested QIDs), replayed "
            "offline through the current adapter twice: 'before' pins "
            "hullq.sources.wikidata.UNIT_QID_MAP_VERSION_SLICE0008 (the legacy, "
            "uncorrected mass-unit map in force through SLICE-0029); 'after' uses "
            "the current SLICE-0030 corrected/default map. Because the fixed "
            "SLICE-0028 linkage is bijective (one accepted QID per canonical "
            "BoatModel), qid_count also equals the canonical BoatModel count over "
            "this exact boundary. Everything except the mass-unit map (adapter "
            "code, qualifier-carrier version, the fixed input entities) is held "
            "constant between before and after."
        ),
        "before_unit_map_version": UNIT_QID_MAP_VERSION_SLICE0008,
        "after_unit_map_version": DEFAULT_UNIT_QID_MAP_VERSION,
        "displacement_normalized_candidate_delta": displacement_delta,
        "non_displacement_fields_unchanged": non_displacement_unchanged,
        "fields": fields,
    }


def verify_coverage_before_after_self_consistency(
    *,
    entities: Sequence[WikidataEntityData],
    full_evidence_before: Sequence[FieldEvidence],
    full_evidence_after: Sequence[FieldEvidence],
    document: Mapping[str, Any],
) -> list[str]:
    """Independently recompute both coverage states purely from *entities*/
    *full_evidence_before*/*full_evidence_after* and compare against a
    retained ``coverage_before_after.json`` document."""
    before_counts, after_counts = compute_before_after_coverage(
        entities, full_evidence_before, full_evidence_after
    )
    expected = build_coverage_before_after_document(
        generated_at=str(document.get("generated_at", "")),
        qid_count=len(entities),
        before_counts=before_counts,
        after_counts=after_counts,
    )
    if dict(document) != expected:
        return [
            "retained coverage_before_after.json != independently recomputed before/after "
            "coverage over the fixed SLICE-0028 entities"
        ]
    return []


# ---------------------------------------------------------------------------
# 3. Research evidence bundle assembly — QID-keyed, one bundle per request QID
# ---------------------------------------------------------------------------


def build_sl0030_bundle(
    qid: str, preferred_label: str | None, allowed_evidence_for_qid: Sequence[FieldEvidence]
) -> ResearchEvidenceBundle:
    """Build the retained ``ResearchEvidenceBundle`` for one requested QID
    under the SLICE-0030 corrected mass-unit map.

    Identical construction contract to the accepted SLICE-0026/0027/0028
    bundle builders, but with a distinct ``bundle_id``/``activity_id``
    namespace (``BUNDLE-SL0030-*`` / ``SL0030_ACTIVITY_ID``) so persisting the
    corrected full-boundary evidence never collides with or overwrites the
    already-imported SLICE-0026/0027/0028 bundles.
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
        bundle_id=f"BUNDLE-SL0030-{qid}",
        bundle_version="1",
        research_target=ResearchTarget(
            manufacturer=None, model=preferred_label or qid, first_built=None
        ),
        research_job_id=None,
        activity_id=SL0030_ACTIVITY_ID,
        observations=(),
        unresolved_findings=(),
        promoted_evidence=promoted,
        reference_crosschecks=(),
    )


# ---------------------------------------------------------------------------
# 4. Retained-package artifact-integrity digests
# ---------------------------------------------------------------------------

ARTIFACT_DIGESTS_SCHEMA_VERSION = "sl0030-artifact-digests-v1"
ARTIFACT_DIGESTS_FILENAME = "ARTIFACT-DIGESTS.json"


def retained_package_filenames(package_dir: Path) -> set[str]:
    """Every regular file directly inside *package_dir* except the digest
    document itself, discovered dynamically (never a hardcoded allowlist)."""
    return {
        p.name for p in package_dir.iterdir() if p.is_file() and p.name != ARTIFACT_DIGESTS_FILENAME
    }


def build_artifact_digests(*, generated_at: str, package_dir: Path) -> dict[str, Any]:
    """Build the retained ``ARTIFACT-DIGESTS.json`` document: a SHA256 digest
    of every retained SLICE-0030 package file except the digest document
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
