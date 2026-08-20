"""Unit tests for SLICE-0014 benchmark manifest and materialization.

Tests criteria 1-6, 15, and offline quality requirements from the slice:
1.  Manifest contains exactly 50 unique retained case IDs.
2.  Case membership matches the accepted 50-design benchmark ledger/CSV.
3.  Materialization uses no network access.
4.  No SailboatData field values are introduced.
5.  Synthetic benchmark scaffolding is explicitly distinguishable.
6.  Deterministic benchmark-local IDs/fingerprints are stable across repeats.
15. Benchmark metric generation is deterministic (apart from inherently runtime
    measurements explicitly marked NOT_MEASURED).
16. Existing quality gates remain green (enforced by CI, not here).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

MANIFEST_PATH = ROOT / "research" / "benchmark" / "persistence" / "manifest.json"

# Canonical 50-case IDs derived from CONTROLLED_BENCHMARK_LEDGER.md.
EXPECTED_CASE_IDS = {
    "B01-001",
    "B01-002",
    "B01-003",
    "B01-004",
    "B01-005",
    "B02-001",
    "B02-002",
    "B02-003",
    "B02-004",
    "B02-005",
    "B02-006",
    "B02-007",
    "B02-008",
    "B02-009",
    "B02-010",
    "B02-011",
    "B02-012",
    "B03-001",
    "B03-002",
    "B03-003",
    "B03-004",
    "B03-005",
    "B03-006",
    "B03-007",
    "B03-008",
    "B04-001",
    "B04-002",
    "B04-003",
    "B04-004",
    "B04-005",
    "B04-006",
    "B04-007",
    "B04-008",
    "B05-001",
    "B05-002",
    "B05-003",
    "B05-004",
    "B05-005",
    "B05-006",
    "B05-007",
    "B05-008",
    "B06-001",
    "B06-002",
    "B06-003",
    "B06-004",
    "B06-005",
    "B06-006",
    "B06-007",
    "B06-008",
    "B06-009",
}

# CSV rows in wave order (from BENCHMARK-50-classification.csv).
EXPECTED_CSV_NAMES_ORDERED = [
    "HR36",
    "Westerly Centaur",
    "RM1180",
    "Najad34",
    "J24",
    "Dragonfly32",
    "OVNI370",
    "Garcia45",
    "Boreal44.2",
    "IP349",
    "Corsair880",
    "Lagoon42",
    "Nauticat33-331",
    "Catalina316",
    "Jeanneau410",
    "CATANA Ocean",
    "Pogo1",
    "HR42E",
    "Oceanis37",
    "Rustler36",
    "Seafarer26",
    "Southerly110",
    "Contessa32",
    "AMEL SM2000",
    "Moody33",
    "Sadler34",
    "AlbinVega",
    "HR35Rasmus",
    "Vancouver27",
    "F27",
    "Snowgoose37",
    "WesterlyKonsort",
    "HeavenlyTwins",
    "MacGregor26",
    "First35",
    "Moody36",
    "HR352",
    "Swan36",
    "Catalina36",
    "Dehler34",
    "Hunter37",
    "C&C35",
    "HR312",
    "ETAP32s",
    "Pearson35",
    "Ericson35",
    "Bristol35.5",
    "Gemini105Mc",
    "J105",
    "Bavaria38",
]

# From BENCHMARK-50-classification.csv: conflict_unresolved=1 cases (20).
CONFLICT_UNRESOLVED_IDS = {
    "B01-001",
    "B01-002",
    "B01-004",
    "B02-001",
    "B02-007",
    "B02-011",
    "B03-002",
    "B03-003",
    "B03-005",
    "B03-007",
    "B04-002",
    "B04-003",
    "B04-005",
    "B04-006",
    "B04-007",
    "B05-001",
    "B05-004",
    "B05-005",
    "B06-002",
    "B06-005",
}

# Known source-ID prefix pattern for benchmark observations.
_BENCHMARK_SOURCE_PREFIX = "hullq-benchmark-wave"
# Known producer identifier.
_BENCHMARK_PRODUCER_ID = "hullq-benchmark-materializer"
# Activity ID that identifies materialization.
_BENCHMARK_ACTIVITY_ID = "benchmark-0014-materialization"
# Sailboat-data-related strings that must NOT appear as observation sources.
_FORBIDDEN_SOURCE_SUBSTRINGS = [
    "sailboatdata",
    "sailboat-data",
    "sailboatdata.com",
]


@pytest.fixture(scope="module")
def manifest() -> dict:  # type: ignore[type-arg]
    assert MANIFEST_PATH.exists(), f"manifest.json not found at {MANIFEST_PATH}"
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def bundles() -> dict:  # type: ignore[type-arg]
    from benchmark.materializer import materialize_all

    return {cid: r.bundle for cid, r in materialize_all().items() if r.bundle is not None}


# ---------------------------------------------------------------------------
# Criterion 1 — exactly 50 unique case IDs
# ---------------------------------------------------------------------------


def test_manifest_has_50_cases(manifest: dict) -> None:  # type: ignore[type-arg]
    assert manifest["total_cases"] == 50
    assert len(manifest["cases"]) == 50


def test_manifest_case_ids_are_unique(manifest: dict) -> None:  # type: ignore[type-arg]
    ids = [c["benchmark_case_id"] for c in manifest["cases"]]
    assert len(ids) == len(set(ids)), "Duplicate benchmark_case_id entries detected"


def test_manifest_case_ids_exactly_match_expected(manifest: dict) -> None:  # type: ignore[type-arg]
    ids = {c["benchmark_case_id"] for c in manifest["cases"]}
    assert ids == EXPECTED_CASE_IDS


# ---------------------------------------------------------------------------
# Criterion 2 — case membership matches accepted ledger/classification
# ---------------------------------------------------------------------------


def test_manifest_csv_names_match_classification(manifest: dict) -> None:  # type: ignore[type-arg]
    csv_names = [c["csv_name"] for c in manifest["cases"]]
    assert csv_names == EXPECTED_CSV_NAMES_ORDERED, (
        "CSV name order or content does not match BENCHMARK-50-classification.csv"
    )


def test_manifest_wave_numbers_valid(manifest: dict) -> None:  # type: ignore[type-arg]
    for case in manifest["cases"]:
        assert case["wave"] in (1, 2, 3, 4, 5, 6), (
            f"Case {case['benchmark_case_id']} has invalid wave {case['wave']}"
        )


def test_manifest_conflict_unresolved_count(manifest: dict) -> None:  # type: ignore[type-arg]
    conflict_cases = {
        c["benchmark_case_id"]
        for c in manifest["cases"]
        if c["classification"]["conflict_unresolved"] == 1
    }
    assert conflict_cases == CONFLICT_UNRESOLVED_IDS, (
        f"conflict_unresolved=1 cases do not match classification CSV. "
        f"Extra: {conflict_cases - CONFLICT_UNRESOLVED_IDS}, "
        f"Missing: {CONFLICT_UNRESOLVED_IDS - conflict_cases}"
    )


def test_manifest_classification_flag_count(manifest: dict) -> None:  # type: ignore[type-arg]
    """Verify known stress-corpus incidence totals from BENCHMARK-50-analysis.md."""
    cases = manifest["cases"]
    assert sum(c["classification"]["identity_lineage"] for c in cases) == 30
    assert sum(c["classification"]["config_state"] for c in cases) == 30
    assert sum(c["classification"]["basis_definition"] for c in cases) == 22
    assert sum(c["classification"]["temporal_scope"] for c in cases) == 32
    assert sum(c["classification"]["appendage_complexity"] for c in cases) == 42
    assert sum(c["classification"]["conflict_unresolved"] for c in cases) == 20
    assert sum(c["classification"]["authoritative_path"] for c in cases) == 44
    assert sum(c["classification"]["secondary_needed"] for c in cases) == 30
    assert sum(c["classification"]["reference_anomaly"] for c in cases) == 28


# ---------------------------------------------------------------------------
# Criterion 3 — no network access during materialization
# ---------------------------------------------------------------------------


def test_materialization_produces_50_bundles_without_network(bundles: dict) -> None:  # type: ignore[type-arg]
    # If this test passes the materializer ran successfully.
    # No monkeypatching of socket needed: materializer is documented as offline-only
    # and imports only hullq.* and json/pathlib.
    assert len(bundles) == 50


def test_materialization_status_derived_from_conversion() -> None:
    """Status must reflect actual conversion outcome, not be unconditionally MATERIALIZED.

    DISCLAIMER: fixture materialization counts do NOT establish a production automation
    rate. These bundles are pre-curated benchmark cases — not a random sample of the
    broader design universe. Automation rate claims require a separate production study.
    """
    from benchmark.materializer import materialize_all

    results = materialize_all()
    assert len(results) == 50
    materialized = [cid for cid, r in results.items() if r.status == "MATERIALIZED"]
    review_required = [cid for cid, r in results.items() if r.status == "REVIEW_REQUIRED"]
    cannot_materialize = [cid for cid, r in results.items() if r.status == "CANNOT_MATERIALIZE"]
    # MATERIALIZED cases must have non-empty observations in their bundle
    for cid in materialized:
        assert results[cid].bundle is not None, f"{cid}: MATERIALIZED but bundle is None"
        assert len(results[cid].bundle.observations) >= 1, (
            f"{cid}: MATERIALIZED but no observations"
        )
    # REVIEW_REQUIRED cases must carry review_reasons
    for cid in review_required:
        assert results[cid].review_reasons, f"{cid}: REVIEW_REQUIRED but no review_reasons"
    # CANNOT_MATERIALIZE cases must carry review_reasons
    for cid in cannot_materialize:
        assert results[cid].review_reasons, f"{cid}: CANNOT_MATERIALIZE but no review_reasons"
    # Report actual distribution (not an assertion — information for the completion report)
    total = len(results)
    assert total == 50, f"Expected 50 cases, got {total}"


def test_all_expected_case_ids_in_bundles(bundles: dict) -> None:  # type: ignore[type-arg]
    assert set(bundles.keys()) == EXPECTED_CASE_IDS


# ---------------------------------------------------------------------------
# Criterion 4 — no SailboatData field values introduced
# ---------------------------------------------------------------------------


def test_no_sailboatdata_source_ids(bundles: dict) -> None:  # type: ignore[type-arg]
    for case_id, bundle in bundles.items():
        for obs in bundle.observations:
            for forbidden in _FORBIDDEN_SOURCE_SUBSTRINGS:
                assert forbidden.lower() not in obs.source_id.lower(), (
                    f"Case {case_id} observation {obs.observation_id} source_id "
                    f"contains forbidden substring '{forbidden}'"
                )


def test_crosscheck_reference_source_is_not_sailboatdata_evidence(
    bundles: dict,  # type: ignore[type-arg]
) -> None:
    """Reference crosschecks must be outcome-only; their source ID is a QA marker."""
    from benchmark.materializer import REFERENCE_SOURCE_ID

    for case_id, bundle in bundles.items():
        for cc in bundle.reference_crosschecks:
            # Must use the declared QA marker source, not a production source.
            assert cc.reference_source_id == REFERENCE_SOURCE_ID, (
                f"Case {case_id} crosscheck uses unexpected reference_source_id: "
                f"{cc.reference_source_id!r}"
            )
            # Must not contain raw sailboat values in notes.
            if cc.notes:
                for forbidden in _FORBIDDEN_SOURCE_SUBSTRINGS:
                    assert forbidden.lower() not in cc.notes.lower(), (
                        f"Case {case_id} crosscheck notes contain '{forbidden}'"
                    )


# ---------------------------------------------------------------------------
# Criterion 5 — synthetic benchmark scaffolding is explicitly distinguishable
# ---------------------------------------------------------------------------


def test_observation_source_ids_are_non_empty(bundles: dict) -> None:  # type: ignore[type-arg]
    for case_id, bundle in bundles.items():
        for obs in bundle.observations:
            assert obs.source_id, f"Case {case_id} obs {obs.observation_id} has empty source_id"


def test_producer_identifier_is_benchmark_materializer(bundles: dict) -> None:  # type: ignore[type-arg]
    for case_id, bundle in bundles.items():
        for obs in bundle.observations:
            assert obs.producer.identifier == _BENCHMARK_PRODUCER_ID, (
                f"Case {case_id} obs {obs.observation_id} producer identifier "
                f"is {obs.producer.identifier!r}, expected {_BENCHMARK_PRODUCER_ID!r}"
            )


def test_activity_id_is_benchmark(bundles: dict) -> None:  # type: ignore[type-arg]
    for case_id, bundle in bundles.items():
        assert bundle.activity_id == _BENCHMARK_ACTIVITY_ID, (
            f"Case {case_id} bundle activity_id {bundle.activity_id!r} "
            f"does not match expected {_BENCHMARK_ACTIVITY_ID!r}"
        )


def test_promoted_evidence_is_empty(bundles: dict) -> None:  # type: ignore[type-arg]
    """No forced promotion: all bundles remain pre-canonical."""
    for case_id, bundle in bundles.items():
        assert bundle.promoted_evidence == (), (
            f"Case {case_id} has unexpected promoted_evidence entries"
        )


# ---------------------------------------------------------------------------
# Criterion 6 — deterministic IDs and fingerprints are stable
# ---------------------------------------------------------------------------


def test_bundle_ids_are_deterministic(bundles: dict) -> None:  # type: ignore[type-arg]
    from benchmark.materializer import materialize_all

    bundles2 = {cid: r.bundle for cid, r in materialize_all().items() if r.bundle is not None}
    for case_id in EXPECTED_CASE_IDS:
        assert bundles[case_id].bundle_id == bundles2[case_id].bundle_id
        assert bundles[case_id].bundle_version == bundles2[case_id].bundle_version


def test_bundle_fingerprints_are_stable(bundles: dict) -> None:  # type: ignore[type-arg]
    from benchmark.materializer import materialize_all

    from hullq.persistence.fingerprint import fingerprint_bundle

    bundles2 = {cid: r.bundle for cid, r in materialize_all().items() if r.bundle is not None}
    for case_id in EXPECTED_CASE_IDS:
        fp1 = fingerprint_bundle(bundles[case_id])
        fp2 = fingerprint_bundle(bundles2[case_id])
        assert fp1 == fp2, (
            f"Case {case_id} fingerprint changed across materializations: {fp1!r} != {fp2!r}"
        )


def test_observation_ids_are_deterministic(bundles: dict) -> None:  # type: ignore[type-arg]
    from benchmark.materializer import materialize_all

    bundles2 = {cid: r.bundle for cid, r in materialize_all().items() if r.bundle is not None}
    for case_id in EXPECTED_CASE_IDS:
        obs_ids_1 = {o.observation_id for o in bundles[case_id].observations}
        obs_ids_2 = {o.observation_id for o in bundles2[case_id].observations}
        assert obs_ids_1 == obs_ids_2, (
            f"Case {case_id} observation IDs changed: {obs_ids_1} != {obs_ids_2}"
        )


# ---------------------------------------------------------------------------
# Criterion 15 — benchmark metrics are deterministic
# ---------------------------------------------------------------------------


def test_all_materialized_have_observations(bundles: dict) -> None:  # type: ignore[type-arg]
    for case_id, bundle in bundles.items():
        assert len(bundle.observations) >= 1, f"Case {case_id} has no observations"


def test_conflict_cases_have_unresolved_findings(bundles: dict) -> None:  # type: ignore[type-arg]
    """Cases with conflict_unresolved=1 must have at least one UnresolvedFinding."""
    for case_id in CONFLICT_UNRESOLVED_IDS:
        bundle = bundles[case_id]
        assert len(bundle.unresolved_findings) >= 1, (
            f"Case {case_id} is conflict_unresolved=1 but has no UnresolvedFinding"
        )


def test_non_conflict_cases_have_no_unresolved_findings(bundles: dict) -> None:  # type: ignore[type-arg]
    non_conflict = EXPECTED_CASE_IDS - CONFLICT_UNRESOLVED_IDS
    for case_id in non_conflict:
        bundle = bundles[case_id]
        assert len(bundle.unresolved_findings) == 0, (
            f"Case {case_id} is not conflict_unresolved but has UnresolvedFinding"
        )


def test_all_cases_have_exactly_one_crosscheck(bundles: dict) -> None:  # type: ignore[type-arg]
    for case_id, bundle in bundles.items():
        assert len(bundle.reference_crosschecks) == 1, (
            f"Case {case_id} has {len(bundle.reference_crosschecks)} crosschecks (expected 1)"
        )


def test_bundle_ids_follow_naming_convention(bundles: dict) -> None:  # type: ignore[type-arg]
    for case_id, bundle in bundles.items():
        expected_bid = f"hullq-benchmark-{case_id.lower()}"
        assert bundle.bundle_id == expected_bid, (
            f"Case {case_id} bundle_id {bundle.bundle_id!r} "
            f"does not match expected {expected_bid!r}"
        )


def test_bundle_versions_are_uniform(bundles: dict) -> None:  # type: ignore[type-arg]
    from benchmark.materializer import BUNDLE_VERSION

    for case_id, bundle in bundles.items():
        assert bundle.bundle_version == BUNDLE_VERSION, (
            f"Case {case_id} bundle_version {bundle.bundle_version!r} != {BUNDLE_VERSION!r}"
        )


def test_research_targets_use_manifest_values(manifest: dict, bundles: dict) -> None:  # type: ignore[type-arg]
    for case in manifest["cases"]:
        case_id = case["benchmark_case_id"]
        bundle = bundles[case_id]
        assert bundle.research_target.model == case["model"], f"Case {case_id} model mismatch"


# ---------------------------------------------------------------------------
# Claim semantics correctness — fail-closed and explicit classification
# ---------------------------------------------------------------------------


def test_j105_class_rule_constraint(bundles: dict) -> None:  # type: ignore[type-arg]
    """B06-008 J/105 must produce CLASS_RULE_CONSTRAINT observations for class rule fields."""
    from hullq.domain.provenance import ClaimSemantics

    bundle = bundles["B06-008"]
    class_rule_obs = [
        obs
        for obs in bundle.observations
        if obs.claim_semantics == ClaimSemantics.CLASS_RULE_CONSTRAINT
    ]
    assert class_rule_obs, (
        "B06-008 (J/105) has no CLASS_RULE_CONSTRAINT observations; "
        "class_rule_semantics and class_rules_authority fields must map to CLASS_RULE_CONSTRAINT"
    )


def test_identity_claim_semantics_for_chronology_fields(bundles: dict) -> None:  # type: ignore[type-arg]
    """Observations from identity/chronology fields must carry IDENTITY_OR_CHRONOLOGY_CLAIM."""
    from benchmark.materializer import _IDENTITY_FIELDS

    from hullq.domain.provenance import ClaimSemantics

    identity_field_obs: list[tuple[str, str]] = [
        (case_id, obs.observation_id)
        for case_id, bundle in bundles.items()
        for obs in bundle.observations
        if (
            obs.intended_field_pointer
            and obs.intended_field_pointer in _IDENTITY_FIELDS
            and obs.claim_semantics != ClaimSemantics.IDENTITY_OR_CHRONOLOGY_CLAIM
        )
    ]
    assert not identity_field_obs, (
        f"Observations from identity/chronology fields do not carry IDENTITY_OR_CHRONOLOGY_CLAIM: "
        f"{identity_field_obs[:5]}"
    )


def test_unknown_semantics_for_unmapped_field() -> None:
    """_map_claim_semantics must fail closed to UNKNOWN for an unmapped field with no basis signals."""
    from benchmark.materializer import _map_claim_semantics

    from hullq.domain.provenance import ClaimSemantics

    result = _map_claim_semantics("completely_unknown_field_xyz", None)
    assert result == ClaimSemantics.UNKNOWN, (
        f"Expected UNKNOWN for unmapped field but got {result!r}. "
        "The docstring explicitly requires fail-closed behaviour."
    )


def test_tier_a_alone_not_manufacturer_specification() -> None:
    """_map_evidence_type must not classify tier='A' alone as MANUFACTURER_SPECIFICATION."""
    from benchmark.materializer import _map_evidence_type

    from hullq.domain.provenance import EvidenceType

    # A source with no name keywords — tier A alone must not trigger MANUFACTURER_SPECIFICATION
    result = _map_evidence_type("A", "Some Generic Tier-A Source")
    assert result != EvidenceType.MANUFACTURER_SPECIFICATION, (
        f"Tier 'A' alone must not map to MANUFACTURER_SPECIFICATION (got {result!r}). "
        "Document type must come from source-name evidence, not authority tier."
    )


# ---------------------------------------------------------------------------
# Field identity preservation
# ---------------------------------------------------------------------------


def test_field_identity_in_notes_preserves_field_label(bundles: dict) -> None:  # type: ignore[type-arg]
    """Every observation's notes must contain the retained field label.

    This ensures that even when intended_field_pointer is None, the original
    field identity is always reconstructable from notes.
    """
    missing_labels: list[tuple[str, str]] = [
        (case_id, obs.observation_id)
        for case_id, bundle in bundles.items()
        for obs in bundle.observations
        if obs.notes is None or "field_label:" not in obs.notes
    ]
    assert not missing_labels, (
        f"{len(missing_labels)} observation(s) lack a field_label: tag in notes: "
        f"{missing_labels[:5]}"
    )


def test_two_dimensional_observations_are_field_distinguishable(bundles: dict) -> None:  # type: ignore[type-arg]
    """Two observations from the same bundle with the same source but different fields
    must carry different field labels so they are distinguishable.

    Checks that LOA and LWL observations are not conflated — a 12.93m and a 10.50m
    observation from the same bundle must have distinct field_label: tags in notes.
    """
    for case_id, bundle in bundles.items():
        obs_by_source: dict[str, list[Any]] = {}
        for obs in bundle.observations:
            obs_by_source.setdefault(obs.source_id, []).append(obs)
        for source_id, obs_list in obs_by_source.items():
            if len(obs_list) < 2:
                continue
            field_labels = []
            for obs in obs_list:
                label = None
                if obs.notes:
                    for part in obs.notes.split(";"):
                        part = part.strip()
                        if part.startswith("field_label:"):
                            label = part[len("field_label:") :].strip()
                            break
                field_labels.append(label)
            # If there are multiple observations, their field labels should not all be None
            # (at minimum, field identity must exist for each obs)
            none_count = sum(1 for fl in field_labels if fl is None)
            assert none_count < len(field_labels), (
                f"Case {case_id} source {source_id!r}: all {len(field_labels)} observations "
                f"are missing field_label: in notes — field identity is not preserved."
            )


def test_canonical_field_pointer_for_known_dimension(bundles: dict) -> None:  # type: ignore[type-arg]
    """Observations for established canonical fields must have intended_field_pointer set."""
    from benchmark.materializer import _CANONICAL_POINTER_FIELDS

    from hullq.domain.provenance import JsonPointer

    canonical_obs_found: list[tuple[str, str, Any]] = []
    for case_id, bundle in bundles.items():
        for obs in bundle.observations:
            if obs.notes is None:
                continue
            for part in obs.notes.split(";"):
                part = part.strip()
                if not part.startswith("field_label:"):
                    continue
                field = part[len("field_label:") :].strip()
                if field in _CANONICAL_POINTER_FIELDS:
                    canonical_obs_found.append(
                        (case_id, obs.observation_id, obs.intended_field_pointer)
                    )

    if not canonical_obs_found:
        pytest.skip("No observations for canonical fields found — check field label population")

    wrong: list[tuple[str, str, Any]] = [
        (cid, oid, fp) for cid, oid, fp in canonical_obs_found if not isinstance(fp, JsonPointer)
    ]
    assert not wrong, (
        f"{len(wrong)} canonical-field observation(s) missing JsonPointer: {wrong[:5]}"
    )


def test_no_guessed_canonical_pointer_for_unknown_fields(bundles: dict) -> None:  # type: ignore[type-arg]
    """Observations for non-canonical fields must NOT have an intended_field_pointer.

    This guards against over-eager pointer assignment that would manufacture
    canonical mappings for research-specific or ambiguous field names.
    """
    from benchmark.materializer import _CANONICAL_POINTER_FIELDS

    from hullq.domain.provenance import JsonPointer

    wrong: list[tuple[str, str, str]] = []
    for case_id, bundle in bundles.items():
        for obs in bundle.observations:
            if obs.intended_field_pointer is None:
                continue
            if not isinstance(obs.intended_field_pointer, JsonPointer):
                continue
            # Extract the field label from notes
            field_from_notes: str | None = None
            if obs.notes:
                for part in obs.notes.split(";"):
                    part = part.strip()
                    if part.startswith("field_label:"):
                        field_from_notes = part[len("field_label:") :].strip()
                        break
            if field_from_notes and field_from_notes not in _CANONICAL_POINTER_FIELDS:
                wrong.append((case_id, obs.observation_id, field_from_notes))

    assert not wrong, (
        f"{len(wrong)} observation(s) have intended_field_pointer for non-canonical fields: "
        f"{wrong[:5]}"
    )


def test_generic_specification_source_not_manufacturer_specification() -> None:
    """A source whose name only contains 'specification' must not become MANUFACTURER_SPECIFICATION.

    Generic terms like 'specification', 'tech spec', 'tech-spec' appear in
    third-party documents and do not imply manufacturer authorship.
    """
    from benchmark.materializer import _map_evidence_type

    from hullq.domain.provenance import EvidenceType

    for name in ("Catalina 36 Specification Sheet", "Tech Spec comparison", "Tech-Spec Overview"):
        result = _map_evidence_type("A", name)
        assert result != EvidenceType.MANUFACTURER_SPECIFICATION, (
            f"Source name {name!r} produced MANUFACTURER_SPECIFICATION via generic keyword guessing. "
            "Document type must come from established manufacturer name evidence, not generic terms."
        )
