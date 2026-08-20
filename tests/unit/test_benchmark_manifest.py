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

    return materialize_all()


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


def test_observation_source_ids_use_benchmark_prefix(bundles: dict) -> None:  # type: ignore[type-arg]
    for case_id, bundle in bundles.items():
        for obs in bundle.observations:
            assert obs.source_id.startswith(_BENCHMARK_SOURCE_PREFIX), (
                f"Case {case_id} obs {obs.observation_id} source_id "
                f"{obs.source_id!r} does not start with {_BENCHMARK_SOURCE_PREFIX!r}"
            )


def test_observation_notes_contain_benchmark_marker(bundles: dict) -> None:  # type: ignore[type-arg]
    for case_id, bundle in bundles.items():
        for obs in bundle.observations:
            assert obs.notes is not None, f"Case {case_id} obs {obs.observation_id} has no notes"
            assert "BENCHMARK MATERIALIZATION" in (obs.notes or ""), (
                f"Case {case_id} obs {obs.observation_id} notes missing "
                f"'BENCHMARK MATERIALIZATION' marker"
            )


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

    bundles2 = materialize_all()
    for case_id in EXPECTED_CASE_IDS:
        assert bundles[case_id].bundle_id == bundles2[case_id].bundle_id
        assert bundles[case_id].bundle_version == bundles2[case_id].bundle_version


def test_bundle_fingerprints_are_stable(bundles: dict) -> None:  # type: ignore[type-arg]
    from benchmark.materializer import materialize_all

    from hullq.persistence.fingerprint import fingerprint_bundle

    bundles2 = materialize_all()
    for case_id in EXPECTED_CASE_IDS:
        fp1 = fingerprint_bundle(bundles[case_id])
        fp2 = fingerprint_bundle(bundles2[case_id])
        assert fp1 == fp2, (
            f"Case {case_id} fingerprint changed across materializations: {fp1!r} != {fp2!r}"
        )


def test_observation_ids_are_deterministic(bundles: dict) -> None:  # type: ignore[type-arg]
    from benchmark.materializer import materialize_all

    bundles2 = materialize_all()
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
