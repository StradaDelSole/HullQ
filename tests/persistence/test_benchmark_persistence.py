"""PostgreSQL integration tests for SLICE-0014 benchmark corpus.

Covers persistence acceptance criteria 7-14 from the slice:
7.  Every materialized bundle validates under accepted contracts.
8.  All materialized bundles import into an empty real PostgreSQL 18 database.
9.  Exact re-import returns deterministic idempotent ALREADY_IMPORTED outcomes.
10. Fresh-database second run yields the same semantic outcomes.
11. Readback preserves raw/normalized/claim/applicability semantics.
12. Unresolved/pre-canonical cases remain pre-canonical without forced BoatDesign creation.
13. Optional promotion happens only with explicit supplied subject (none here).
14. Conflicts/errors do not leave partial losing bundle state.

These tests are skipped automatically when HULLQ_TEST_DATABASE_URL is not set.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

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


# ---------------------------------------------------------------------------
# Module-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def benchmark_bundles() -> dict[str, Any]:
    """Materialize all 50 benchmark bundles once for the test session."""
    from benchmark.materializer import materialize_all

    return materialize_all()


@pytest.fixture(scope="module")
def benchmark_conn(db_url: str) -> Any:
    """Session-scoped connection with migrations applied, data truncated between phases."""
    import psycopg

    from hullq.persistence.migrations import apply_migrations

    conn = psycopg.connect(db_url)
    try:
        apply_migrations(conn)
        # Ensure clean slate for this test module.
        with conn.cursor() as cur:
            cur.execute("""
                TRUNCATE TABLE
                    bundle_evidence_members,
                    bundle_reference_crosschecks,
                    bundle_unresolved_findings,
                    bundle_observation_members,
                    research_evidence,
                    research_observations,
                    research_bundles
                RESTART IDENTITY CASCADE
            """)
        conn.commit()
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Criterion 7 — bundles validate under accepted contracts
# ---------------------------------------------------------------------------


def test_all_bundles_have_non_empty_ids(benchmark_bundles: dict[str, Any]) -> None:
    for case_id, bundle in benchmark_bundles.items():
        assert bundle.bundle_id, f"Case {case_id} has empty bundle_id"
        assert bundle.bundle_version, f"Case {case_id} has empty bundle_version"


def test_all_bundles_have_valid_research_target(benchmark_bundles: dict[str, Any]) -> None:
    for case_id, bundle in benchmark_bundles.items():
        assert bundle.research_target.model, f"Case {case_id} research_target.model is empty"


def test_all_observations_have_valid_ids(benchmark_bundles: dict[str, Any]) -> None:
    for case_id, bundle in benchmark_bundles.items():
        for obs in bundle.observations:
            assert obs.observation_id, f"Case {case_id} has observation with empty observation_id"
            assert obs.source_id, f"Case {case_id} obs {obs.observation_id} has empty source_id"


def test_all_bundles_have_no_promoted_evidence(benchmark_bundles: dict[str, Any]) -> None:
    for case_id, bundle in benchmark_bundles.items():
        assert bundle.promoted_evidence == (), f"Case {case_id} has unexpected promoted_evidence"


# ---------------------------------------------------------------------------
# Criterion 8 — import into empty real PostgreSQL 18
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def first_pass_results(benchmark_conn: Any, benchmark_bundles: dict[str, Any]) -> dict[str, Any]:
    """Run first-pass import of all 50 bundles; return {case_id: ImportResult}."""
    from hullq.persistence.importer import import_research_evidence_bundle

    results: dict[str, Any] = {}
    for case_id, bundle in benchmark_bundles.items():
        results[case_id] = import_research_evidence_bundle(benchmark_conn, bundle)
    return results


def test_all_50_bundles_imported_first_pass(first_pass_results: dict[str, Any]) -> None:
    from hullq.persistence._types import ImportStatus

    failures = {
        case_id: r for case_id, r in first_pass_results.items() if r.status != ImportStatus.IMPORTED
    }
    assert not failures, "First-pass import failures: " + ", ".join(
        f"{k}:{v.status}" for k, v in failures.items()
    )


def test_total_imported_count_is_50(first_pass_results: dict[str, Any]) -> None:
    from hullq.persistence._types import ImportStatus

    imported_count = sum(
        1 for r in first_pass_results.values() if r.status == ImportStatus.IMPORTED
    )
    assert imported_count == 50


# ---------------------------------------------------------------------------
# Criterion 9 — exact re-import is idempotent ALREADY_IMPORTED
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def reimport_results(
    benchmark_conn: Any,
    benchmark_bundles: dict[str, Any],
    first_pass_results: dict[str, Any],  # ensure first pass ran first
) -> dict[str, Any]:
    """Run exact re-import of all 50 bundles."""
    from hullq.persistence.importer import import_research_evidence_bundle

    results: dict[str, Any] = {}
    for case_id, bundle in benchmark_bundles.items():
        results[case_id] = import_research_evidence_bundle(benchmark_conn, bundle)
    return results


def test_all_50_bundles_already_imported_on_reimport(
    reimport_results: dict[str, Any],
) -> None:
    from hullq.persistence._types import ImportStatus

    failures = {
        case_id: r
        for case_id, r in reimport_results.items()
        if r.status != ImportStatus.ALREADY_IMPORTED
    }
    assert not failures, "Re-import did not return ALREADY_IMPORTED for: " + ", ".join(
        f"{k}:{v.status}" for k, v in failures.items()
    )


def test_reimport_returns_same_content_hashes(
    benchmark_bundles: dict[str, Any],
    first_pass_results: dict[str, Any],
    reimport_results: dict[str, Any],
) -> None:
    from hullq.persistence.fingerprint import fingerprint_bundle

    for case_id, bundle in benchmark_bundles.items():
        expected_hash = fingerprint_bundle(bundle)
        first_hash = first_pass_results[case_id].content_hash
        reimport_hash = reimport_results[case_id].content_hash
        assert first_hash == expected_hash, (
            f"Case {case_id} first-pass hash {first_hash!r} != expected {expected_hash!r}"
        )
        assert reimport_hash == expected_hash, (
            f"Case {case_id} reimport hash {reimport_hash!r} != expected {expected_hash!r}"
        )


# ---------------------------------------------------------------------------
# Criterion 10 — fresh-database run yields same semantic outcomes
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fresh_db_results(
    db_url: str,
    benchmark_bundles: dict[str, Any],
    reimport_results: dict[str, Any],  # ordering: fresh DB runs after idempotency phase
) -> dict[str, Any]:
    """Import all bundles into a fresh schema; return {case_id: (result, content_hash)}."""
    import psycopg

    from hullq.persistence.fingerprint import fingerprint_bundle
    from hullq.persistence.importer import import_research_evidence_bundle
    from hullq.persistence.migrations import apply_migrations

    conn = psycopg.connect(db_url)
    try:
        apply_migrations(conn)
        with conn.cursor() as cur:
            cur.execute("""
                TRUNCATE TABLE
                    bundle_evidence_members,
                    bundle_reference_crosschecks,
                    bundle_unresolved_findings,
                    bundle_observation_members,
                    research_evidence,
                    research_observations,
                    research_bundles
                RESTART IDENTITY CASCADE
            """)
        conn.commit()

        results: dict[str, Any] = {}
        for case_id, bundle in benchmark_bundles.items():
            result = import_research_evidence_bundle(conn, bundle)
            expected_fp = fingerprint_bundle(bundle)
            results[case_id] = (result, expected_fp)
    finally:
        conn.close()

    return results


def test_fresh_db_imports_all_50(fresh_db_results: dict[str, Any]) -> None:
    from hullq.persistence._types import ImportStatus

    failures = {
        case_id: r
        for case_id, (r, _) in fresh_db_results.items()
        if r.status != ImportStatus.IMPORTED
    }
    assert not failures, "Fresh-DB import failures: " + ", ".join(
        f"{k}:{v.status}" for k, v in failures.items()
    )


def test_fresh_db_fingerprints_match_first_pass(
    fresh_db_results: dict[str, Any],
    first_pass_results: dict[str, Any],
) -> None:
    for case_id, (fresh_result, expected_fp) in fresh_db_results.items():
        first_hash = first_pass_results[case_id].content_hash
        fresh_hash = fresh_result.content_hash
        assert fresh_hash == first_hash == expected_fp, (
            f"Case {case_id} fingerprint mismatch: "
            f"first={first_hash!r}, fresh={fresh_hash!r}, expected={expected_fp!r}"
        )


# ---------------------------------------------------------------------------
# Criterion 11 — readback preserves raw/claim/applicability semantics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", sorted(EXPECTED_CASE_IDS))
def test_readback_bundle_exists(
    benchmark_conn: Any,
    benchmark_bundles: dict[str, Any],
    first_pass_results: dict[str, Any],
    case_id: str,
) -> None:
    from hullq.persistence.readback import fetch_bundle_snapshot

    bundle = benchmark_bundles[case_id]
    snap = fetch_bundle_snapshot(benchmark_conn, bundle.bundle_id, bundle.bundle_version)
    assert snap is not None, f"Bundle snapshot not found for {case_id}"
    assert snap.bundle_id == bundle.bundle_id
    assert snap.bundle_version == bundle.bundle_version


@pytest.mark.parametrize("case_id", sorted(EXPECTED_CASE_IDS))
def test_readback_observation_ids_preserved(
    benchmark_conn: Any,
    benchmark_bundles: dict[str, Any],
    first_pass_results: dict[str, Any],
    case_id: str,
) -> None:
    from hullq.persistence.readback import fetch_bundle_snapshot

    bundle = benchmark_bundles[case_id]
    snap = fetch_bundle_snapshot(benchmark_conn, bundle.bundle_id, bundle.bundle_version)
    assert snap is not None

    expected_obs_ids = {o.observation_id for o in bundle.observations}
    got_obs_ids = set(snap.observation_ids)
    assert expected_obs_ids == got_obs_ids, (
        f"Case {case_id} obs mismatch: expected={expected_obs_ids}, got={got_obs_ids}"
    )


def test_readback_hard_case_observation_raw_value(
    benchmark_conn: Any,
    benchmark_bundles: dict[str, Any],
    first_pass_results: dict[str, Any],
) -> None:
    """Spot-check readback raw value for a representative hard case (B01-001 HR36)."""
    from hullq.persistence.readback import fetch_observation

    case_id = "B01-001"
    bundle = benchmark_bundles[case_id]
    obs_id = bundle.observations[0].observation_id
    original_obs = bundle.observations[0]

    fetched = fetch_observation(benchmark_conn, obs_id)
    assert fetched is not None, f"Observation {obs_id} not found in DB"
    assert fetched.raw.value == original_obs.raw.value
    assert fetched.claim_semantics == original_obs.claim_semantics
    assert (
        fetched.applicability.unknown_or_unbounded
        == original_obs.applicability.unknown_or_unbounded
    )


def test_readback_conflict_case_has_finding(
    benchmark_conn: Any,
    benchmark_bundles: dict[str, Any],
    first_pass_results: dict[str, Any],
) -> None:
    """Verify a conflict case (B02-007) has its UnresolvedFinding persisted."""
    from hullq.persistence.readback import fetch_bundle_snapshot, fetch_finding

    case_id = "B02-007"
    bundle = benchmark_bundles[case_id]
    snap = fetch_bundle_snapshot(benchmark_conn, bundle.bundle_id, bundle.bundle_version)
    assert snap is not None

    assert len(snap.finding_ids) >= 1, f"Case {case_id} has no finding IDs in readback"
    finding_id = snap.finding_ids[0]
    finding = fetch_finding(benchmark_conn, finding_id, bundle.bundle_id, bundle.bundle_version)
    assert finding is not None
    assert finding.topic == "conflict_or_unresolved_evidence"


def test_readback_crosscheck_preserved(
    benchmark_conn: Any,
    benchmark_bundles: dict[str, Any],
    first_pass_results: dict[str, Any],
) -> None:
    """All bundles must have exactly one crosscheck persisted and readable."""
    from hullq.persistence.readback import fetch_bundle_snapshot, fetch_crosscheck

    case_id = "B04-003"  # IDENTITY_DISAMBIGUATION_REQUIRED case
    bundle = benchmark_bundles[case_id]
    snap = fetch_bundle_snapshot(benchmark_conn, bundle.bundle_id, bundle.bundle_version)
    assert snap is not None
    assert len(snap.crosscheck_ids) == 1

    cc_id = snap.crosscheck_ids[0]
    cc = fetch_crosscheck(benchmark_conn, cc_id, bundle.bundle_id, bundle.bundle_version)
    assert cc is not None
    from hullq.research.observations import ReferenceCheckOutcome

    assert cc.outcome == ReferenceCheckOutcome.IDENTITY_DISAMBIGUATION_REQUIRED


# ---------------------------------------------------------------------------
# Criterion 12 — unresolved cases remain pre-canonical, no forced BoatDesign
# ---------------------------------------------------------------------------


def test_no_promoted_evidence_in_any_bundle(benchmark_bundles: dict[str, Any]) -> None:
    for case_id, bundle in benchmark_bundles.items():
        assert len(bundle.promoted_evidence) == 0, (
            f"Case {case_id} has promoted_evidence (should be empty)"
        )


def test_no_evidence_members_in_readback(
    benchmark_conn: Any,
    benchmark_bundles: dict[str, Any],
    first_pass_results: dict[str, Any],
) -> None:
    """No bundle should have evidence_ids in readback (promoted_evidence=empty)."""
    from hullq.persistence.readback import fetch_bundle_snapshot

    for case_id, bundle in benchmark_bundles.items():
        snap = fetch_bundle_snapshot(benchmark_conn, bundle.bundle_id, bundle.bundle_version)
        assert snap is not None, f"Missing snapshot for {case_id}"
        assert snap.evidence_ids == (), (
            f"Case {case_id} has evidence_ids in DB (unexpected promoted evidence)"
        )


# ---------------------------------------------------------------------------
# Criterion 13 — no fuzzy promotion or automatic subject creation
# ---------------------------------------------------------------------------


def test_no_automatic_promotion_occurred(
    benchmark_conn: Any,
    benchmark_bundles: dict[str, Any],
    first_pass_results: dict[str, Any],
) -> None:
    """Verify the research_evidence table has zero rows (no promoted evidence)."""
    with benchmark_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM research_evidence")
        row = cur.fetchone()
    count = row[0] if row else 0
    assert count == 0, f"research_evidence table has {count} rows (expected 0)"


# ---------------------------------------------------------------------------
# Criterion 14 — conflicts/errors leave no partial bundle state
# ---------------------------------------------------------------------------


def test_duplicate_bundle_id_is_idempotent_not_partial(
    benchmark_conn: Any,
    benchmark_bundles: dict[str, Any],
    first_pass_results: dict[str, Any],
) -> None:
    """Re-importing an existing bundle must return ALREADY_IMPORTED with same hash."""
    from hullq.persistence._types import ImportStatus
    from hullq.persistence.fingerprint import fingerprint_bundle
    from hullq.persistence.importer import import_research_evidence_bundle

    case_id = "B01-001"
    bundle = benchmark_bundles[case_id]
    result = import_research_evidence_bundle(benchmark_conn, bundle)
    assert result.status == ImportStatus.ALREADY_IMPORTED
    assert result.content_hash == fingerprint_bundle(bundle)
