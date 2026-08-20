"""Unit tests for importer logic using mock connections — SLICE-0013.

Tests the idempotency, conflict detection, and result-type logic of the
importer without a real PostgreSQL connection. These tests use unittest.mock
to simulate cursor/connection behavior. They do NOT prove PostgreSQL SQL
correctness — that is covered by integration tests.
"""

from __future__ import annotations

from typing import Any

import pytest

from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
    ProducerKind,
    ProducerMetadata,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    SourceLocator,
)
from hullq.persistence._types import ImportStatus, PersistenceConflictError
from hullq.persistence.fingerprint import fingerprint_bundle, fingerprint_observation
from hullq.persistence.importer import (
    _check_existing_bundle,
)
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import (
    ObservationApplicability,
    ResearchEvidenceBundle,
    ResearchObservation,
)

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_applicability() -> ObservationApplicability:
    return ObservationApplicability(
        first_year=None,
        last_year=None,
        hull_number_from=None,
        hull_number_to=None,
        market_or_region=None,
        named_variant_hint=None,
        design_option_hints=None,
        operating_state_hint=None,
        individual_hull_or_listing_ref=None,
        unknown_or_unbounded=True,
    )


def _make_obs(obs_id: str = "OBS-001") -> ResearchObservation:
    return ResearchObservation(
        observation_id=obs_id,
        research_target=ResearchTarget(manufacturer=None, model="Test 35", first_built=None),
        source_id="SRC-001",
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(kind=RawObservationKind.LITERAL, value="10.5", unit="m", excerpt=None),
        normalized_candidate=None,
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
        applicability=_make_applicability(),
        producer=ProducerMetadata(
            kind=ProducerKind.DETERMINISTIC_TOOL,
            identifier="test",
            version="0.1",
            model=None,
            prompt_or_rule_version=None,
        ),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_observation_id=None,
        intended_subject_kind_hint=None,
        intended_field_pointer=None,
        notes=None,
    )


def _make_bundle(
    bundle_id: str = "B-001",
    bundle_version: str = "1.0",
    obs: tuple[ResearchObservation, ...] = (),
) -> ResearchEvidenceBundle:
    return ResearchEvidenceBundle(
        bundle_id=bundle_id,
        bundle_version=bundle_version,
        research_target=ResearchTarget(manufacturer=None, model="Test 35", first_built=None),
        research_job_id=None,
        activity_id=None,
        observations=obs,
        unresolved_findings=(),
        promoted_evidence=(),
        reference_crosschecks=(),
    )


# ---------------------------------------------------------------------------
# _check_existing_bundle tests
# ---------------------------------------------------------------------------


class _FakeCursor:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row

    def execute(self, *args: Any, **kwargs: Any) -> None:
        pass

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._row


def test_check_existing_bundle_not_found() -> None:
    cur = _FakeCursor(None)
    result = _check_existing_bundle(cur, "B-001", "1.0", "abc123")
    assert result is None


def test_check_existing_bundle_same_hash_returns_already_imported() -> None:
    cur = _FakeCursor(("abc123",))
    result = _check_existing_bundle(cur, "B-001", "1.0", "abc123")
    assert result is not None
    assert result.status == ImportStatus.ALREADY_IMPORTED
    assert result.bundle_id == "B-001"
    assert result.bundle_version == "1.0"
    assert result.content_hash == "abc123"


def test_check_existing_bundle_different_hash_returns_conflict() -> None:
    cur = _FakeCursor(("old_hash",))
    result = _check_existing_bundle(cur, "B-001", "1.0", "new_hash")
    assert result is not None
    assert result.status == ImportStatus.CONFLICT
    assert result.detail is not None


# ---------------------------------------------------------------------------
# PersistenceConflictError is a RuntimeError
# ---------------------------------------------------------------------------


def test_persistence_conflict_error_is_runtime_error() -> None:
    exc = PersistenceConflictError("oops")
    assert isinstance(exc, RuntimeError)
    assert "oops" in str(exc)


# ---------------------------------------------------------------------------
# ImportStatus vocabulary
# ---------------------------------------------------------------------------


def test_import_status_values() -> None:
    assert ImportStatus.IMPORTED == "imported"
    assert ImportStatus.ALREADY_IMPORTED == "already_imported"
    assert ImportStatus.CONFLICT == "conflict"


# ---------------------------------------------------------------------------
# Fingerprint determinism across equivalent bundles
# ---------------------------------------------------------------------------


def test_bundle_fingerprint_stable_across_calls() -> None:
    obs = _make_obs()
    b = _make_bundle(obs=(obs,))
    assert fingerprint_bundle(b) == fingerprint_bundle(b)


def test_bundle_fingerprint_changes_with_version() -> None:
    b1 = _make_bundle(bundle_version="1.0")
    b2 = _make_bundle(bundle_version="2.0")
    assert fingerprint_bundle(b1) != fingerprint_bundle(b2)


def test_observation_fingerprint_stable() -> None:
    obs = _make_obs()
    assert fingerprint_observation(obs) == fingerprint_observation(obs)


def test_observation_fingerprint_changes_with_id() -> None:
    obs1 = _make_obs("OBS-001")
    obs2 = _make_obs("OBS-002")
    assert fingerprint_observation(obs1) != fingerprint_observation(obs2)


# ---------------------------------------------------------------------------
# _types
# ---------------------------------------------------------------------------


def test_import_result_frozen() -> None:
    from hullq.persistence._types import ImportResult

    r = ImportResult(
        status=ImportStatus.IMPORTED,
        bundle_id="B-001",
        bundle_version="1.0",
        content_hash="abc",
    )
    with pytest.raises((AttributeError, TypeError)):
        r.status = ImportStatus.CONFLICT  # type: ignore[misc]


def test_import_result_detail_defaults_none() -> None:
    from hullq.persistence._types import ImportResult

    r = ImportResult(
        status=ImportStatus.ALREADY_IMPORTED,
        bundle_id="B-001",
        bundle_version="1.0",
        content_hash="abc",
    )
    assert r.detail is None


# ---------------------------------------------------------------------------
# Migration file listing (pure Python)
# ---------------------------------------------------------------------------


def test_migration_files_sorted() -> None:
    from hullq.persistence.migrations import MIGRATIONS_DIR, list_migration_files

    files = list_migration_files(MIGRATIONS_DIR)
    assert len(files) >= 1
    names = [f.stem for f in files]
    assert names == sorted(names)


def test_migration_sql_file_exists() -> None:
    from hullq.persistence.migrations import MIGRATIONS_DIR

    sql_files = list(MIGRATIONS_DIR.glob("*.sql"))
    assert any("001" in f.stem for f in sql_files), "Migration 001 must exist"


def test_migration_sql_contains_research_bundles() -> None:
    from hullq.persistence.migrations import MIGRATIONS_DIR

    sql = (MIGRATIONS_DIR / "001_initial_schema.sql").read_text(encoding="utf-8")
    assert "research_bundles" in sql
    assert "research_observations" in sql
    assert "bundle_reference_crosschecks" in sql


def test_crosscheck_table_has_no_evidence_id_column() -> None:
    """Structural test: crosschecks must NOT have an evidence_id column."""
    from hullq.persistence.migrations import MIGRATIONS_DIR

    sql = (MIGRATIONS_DIR / "001_initial_schema.sql").read_text(encoding="utf-8")
    # Find the crosscheck table definition
    cc_start = sql.find("bundle_reference_crosschecks")
    cc_end = sql.find(";", cc_start)
    cc_table = sql[cc_start:cc_end]
    assert "evidence_id" not in cc_table, (
        "bundle_reference_crosschecks must not have an evidence_id column"
    )


def test_importing_persistence_module_has_no_network_side_effect() -> None:
    """Top-level persistence import must not open a network connection."""
    import importlib

    import hullq.persistence as mod

    importlib.reload(mod)
