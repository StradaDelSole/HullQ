"""Unit tests using mock connections for persistence code without PostgreSQL — SLICE-0013.

Covers: schema row-param helpers, fingerprint_evidence, apply_migrations (mocked),
import_research_evidence_bundle (mocked), readback _from_jsonb helpers, and
fetch_bundle_snapshot (mocked). These do NOT prove SQL correctness — that is the
integration test suite's job.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
    FieldEvidenceV3,
    JsonPointer,
    ProducerKind,
    ProducerMetadata,
    ProvenanceSubject,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    SourceLocator,
    SubjectKind,
)
from hullq.persistence._types import ImportStatus, PersistenceConflictError
from hullq.persistence.fingerprint import (
    fingerprint_bundle,
    fingerprint_evidence,
    fingerprint_observation,
)
from hullq.persistence.importer import _insert_observation, import_research_evidence_bundle
from hullq.persistence.schema import (
    crosscheck_row_params,
    evidence_row_params,
    finding_row_params,
    observation_row_params,
)
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import (
    ObservationApplicability,
    ReferenceCheckOutcome,
    ReferenceCrosscheck,
    ResearchEvidenceBundle,
    ResearchObservation,
    UnresolvedFinding,
    UnresolvedFindingSeverity,
)

# ---------------------------------------------------------------------------
# Shared domain-object builders
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


def _make_producer() -> ProducerMetadata:
    return ProducerMetadata(
        kind=ProducerKind.DETERMINISTIC_TOOL,
        identifier="test-tool",
        version="0.1",
        model=None,
        prompt_or_rule_version=None,
    )


def _make_locator() -> SourceLocator:
    return SourceLocator(
        page=None, section=None, anchor=None, table=None, figure=None, record_key=None
    )


def _make_raw() -> RawObservation:
    return RawObservation(kind=RawObservationKind.LITERAL, value="10.5", unit="m", excerpt=None)


def _make_obs(obs_id: str = "OBS-001") -> ResearchObservation:
    return ResearchObservation(
        observation_id=obs_id,
        research_target=ResearchTarget(manufacturer=None, model="Test 35", first_built=None),
        source_id="SRC-001",
        source_locator=_make_locator(),
        raw=_make_raw(),
        normalized_candidate=None,
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
        applicability=_make_applicability(),
        producer=_make_producer(),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_observation_id=None,
        intended_subject_kind_hint=None,
        intended_field_pointer=None,
        notes=None,
    )


def _make_evidence(ev_id: str = "EV-001") -> FieldEvidenceV3:
    return FieldEvidenceV3(
        evidence_id=ev_id,
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_MODEL, id="boat-1"),
        field_pointer=JsonPointer("/loa"),
        source_id="SRC-001",
        source_locator=_make_locator(),
        raw=_make_raw(),
        normalized_candidate=None,
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
        applicability=_make_applicability(),
        producer=_make_producer(),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_evidence_id=None,
        notes=None,
    )


def _make_bundle(
    bundle_id: str = "B-001",
    bundle_version: str = "1.0",
    obs: tuple[ResearchObservation, ...] = (),
    evidence: tuple[FieldEvidenceV3, ...] = (),
    findings: tuple[UnresolvedFinding, ...] = (),
    crosschecks: tuple[ReferenceCrosscheck, ...] = (),
) -> ResearchEvidenceBundle:
    return ResearchEvidenceBundle(
        bundle_id=bundle_id,
        bundle_version=bundle_version,
        research_target=ResearchTarget(manufacturer=None, model="Test 35", first_built=None),
        research_job_id=None,
        activity_id=None,
        observations=obs,
        unresolved_findings=findings,
        promoted_evidence=evidence,
        reference_crosschecks=crosschecks,
    )


def _make_finding(finding_id: str = "F-001") -> UnresolvedFinding:
    return UnresolvedFinding(
        finding_id=finding_id,
        topic="identity",
        description="Could not resolve identity.",
        related_observation_ids=frozenset(["OBS-001"]),
        severity=UnresolvedFindingSeverity.REVIEW,
    )


def _make_crosscheck(cc_id: str = "CC-001") -> ReferenceCrosscheck:
    return ReferenceCrosscheck(
        crosscheck_id=cc_id,
        reference_source_id="SRC-REF",
        topic_or_field="loa",
        outcome=ReferenceCheckOutcome.MATCH,
        notes=None,
    )


def _make_mock_conn(fetchone_return: Any = None, fetchall_return: Any = None) -> MagicMock:
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = fetchone_return
    mock_cursor.fetchall.return_value = fetchall_return if fetchall_return is not None else []
    return mock_conn


# ---------------------------------------------------------------------------
# schema.py — row param helpers (pure Python, no DB)
# ---------------------------------------------------------------------------


def test_observation_row_params_length() -> None:
    obs = _make_obs()
    obs_hash = fingerprint_observation(obs)
    params = observation_row_params(obs, obs_hash)
    assert isinstance(params, tuple)
    assert len(params) == 18  # matches INSERT column count


def test_observation_row_params_first_field_is_id() -> None:
    obs = _make_obs("OBS-XYZ")
    params = observation_row_params(obs, "h")
    assert params[0] == "OBS-XYZ"


def test_observation_row_params_second_field_is_hash() -> None:
    obs = _make_obs()
    params = observation_row_params(obs, "fixed-hash")
    assert params[1] == "fixed-hash"


def test_evidence_row_params_length() -> None:
    ev = _make_evidence()
    ev_hash = fingerprint_evidence(ev)
    params = evidence_row_params(ev, ev_hash)
    assert isinstance(params, tuple)
    assert len(params) == 18  # matches INSERT column count (no bundle_id/bundle_version)


def test_evidence_row_params_first_field_is_evidence_id() -> None:
    ev = _make_evidence("EV-ZZZ")
    params = evidence_row_params(ev, "h")
    assert params[0] == "EV-ZZZ"


def test_finding_row_params_length() -> None:
    finding = _make_finding()
    bundle = _make_bundle()
    params = finding_row_params(finding, bundle)
    assert isinstance(params, tuple)
    assert len(params) == 7  # matches INSERT column count


def test_finding_row_params_first_field_is_finding_id() -> None:
    finding = _make_finding("F-ABC")
    bundle = _make_bundle()
    params = finding_row_params(finding, bundle)
    assert params[0] == "F-ABC"


def test_finding_row_params_related_obs_ids_sorted() -> None:
    finding = _make_finding()
    bundle = _make_bundle()
    params = finding_row_params(finding, bundle)
    related: list[str] = params[6]
    assert related == sorted(related)


def test_crosscheck_row_params_length() -> None:
    cc = _make_crosscheck()
    bundle = _make_bundle()
    params = crosscheck_row_params(cc, bundle)
    assert isinstance(params, tuple)
    assert len(params) == 7  # matches INSERT column count


def test_crosscheck_row_params_first_field_is_crosscheck_id() -> None:
    cc = _make_crosscheck("CC-ZZZ")
    bundle = _make_bundle()
    params = crosscheck_row_params(cc, bundle)
    assert params[0] == "CC-ZZZ"


# ---------------------------------------------------------------------------
# fingerprint.py — fingerprint_evidence (pure Python)
# ---------------------------------------------------------------------------


def test_fingerprint_evidence_is_64_char_hex() -> None:
    ev = _make_evidence()
    h = fingerprint_evidence(ev)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_fingerprint_evidence_stable() -> None:
    ev = _make_evidence()
    assert fingerprint_evidence(ev) == fingerprint_evidence(ev)


def test_fingerprint_evidence_changes_with_id() -> None:
    ev1 = _make_evidence("EV-001")
    ev2 = _make_evidence("EV-002")
    assert fingerprint_evidence(ev1) != fingerprint_evidence(ev2)


def test_fingerprint_evidence_changes_with_field_pointer() -> None:
    ev1 = _make_evidence()
    ev2 = FieldEvidenceV3(
        evidence_id=ev1.evidence_id,
        subject=ev1.subject,
        field_pointer=JsonPointer("/beam"),
        source_id=ev1.source_id,
        source_locator=ev1.source_locator,
        raw=ev1.raw,
        normalized_candidate=ev1.normalized_candidate,
        evidence_type=ev1.evidence_type,
        claim_semantics=ev1.claim_semantics,
        applicability=ev1.applicability,
        producer=ev1.producer,
        research_context=ev1.research_context,
        observed_at=ev1.observed_at,
        confidence=ev1.confidence,
        supersedes_evidence_id=ev1.supersedes_evidence_id,
        notes=ev1.notes,
    )
    assert fingerprint_evidence(ev1) != fingerprint_evidence(ev2)


# ---------------------------------------------------------------------------
# migrations.py — apply_migrations with mock connection
# ---------------------------------------------------------------------------


def test_apply_migrations_skips_already_applied() -> None:
    from hullq.persistence.migrations import MIGRATIONS_DIR, apply_migrations

    mock_conn = _make_mock_conn(fetchone_return=("1",))  # already applied
    applied = apply_migrations(mock_conn, MIGRATIONS_DIR)
    assert applied == []


def test_apply_migrations_returns_list_of_applied() -> None:
    from hullq.persistence.migrations import MIGRATIONS_DIR, apply_migrations

    mock_conn = _make_mock_conn(fetchone_return=None)  # not yet applied
    applied = apply_migrations(mock_conn, MIGRATIONS_DIR)
    assert isinstance(applied, list)
    assert len(applied) >= 1
    assert applied[0] == "001_initial_schema"


def test_apply_migrations_calls_commit() -> None:
    from hullq.persistence.migrations import MIGRATIONS_DIR, apply_migrations

    mock_conn = _make_mock_conn(fetchone_return=None)
    apply_migrations(mock_conn, MIGRATIONS_DIR)
    assert mock_conn.commit.called


def test_apply_migrations_empty_dir(tmp_path: Any) -> None:
    from hullq.persistence.migrations import apply_migrations

    mock_conn = _make_mock_conn(fetchone_return=None)
    applied = apply_migrations(mock_conn, tmp_path)
    assert applied == []


# ---------------------------------------------------------------------------
# importer.py — _insert_observation with mock cursor
# ---------------------------------------------------------------------------


def test_insert_observation_new_calls_execute_once() -> None:
    """When obs INSERT succeeds (rowcount=1), only one execute call: INSERT."""
    cur = MagicMock()
    cur.rowcount = 1  # INSERT row created — no SELECT needed
    obs = _make_obs()
    obs_hash = fingerprint_observation(obs)
    _insert_observation(cur, obs, obs_hash)
    assert cur.execute.call_count == 1


def test_insert_observation_same_hash_calls_execute_twice() -> None:
    """When obs INSERT conflicts (rowcount=0) and hashes match, two execute calls: INSERT + SELECT."""
    obs = _make_obs()
    obs_hash = fingerprint_observation(obs)
    cur = MagicMock()
    cur.rowcount = 0  # INSERT did nothing — check existing hash
    cur.fetchone.return_value = (obs_hash,)
    _insert_observation(cur, obs, obs_hash)
    assert cur.execute.call_count == 2  # INSERT + SELECT


def test_insert_observation_hash_mismatch_raises() -> None:
    """When obs INSERT conflicts (rowcount=0) and hashes differ, PersistenceConflictError."""
    obs = _make_obs()
    obs_hash = fingerprint_observation(obs)
    cur = MagicMock()
    cur.rowcount = 0  # INSERT did nothing — check existing hash
    cur.fetchone.return_value = ("completely-different-hash",)
    with pytest.raises(PersistenceConflictError):
        _insert_observation(cur, obs, obs_hash)


# ---------------------------------------------------------------------------
# importer.py — import_research_evidence_bundle with mock connection
# ---------------------------------------------------------------------------


def test_import_empty_bundle_returns_imported() -> None:
    bundle = _make_bundle()
    mock_conn = _make_mock_conn(fetchone_return=None)
    result = import_research_evidence_bundle(mock_conn, bundle)
    assert result.status == ImportStatus.IMPORTED
    assert result.bundle_id == bundle.bundle_id
    assert result.bundle_version == bundle.bundle_version
    assert len(result.content_hash) == 64


def test_import_already_imported_returns_already_imported() -> None:
    bundle = _make_bundle()
    bundle_hash = fingerprint_bundle(bundle)
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.rowcount = 0  # bundle INSERT did nothing — check existing hash
    mock_cursor.fetchone.return_value = (bundle_hash,)
    result = import_research_evidence_bundle(mock_conn, bundle)
    assert result.status == ImportStatus.ALREADY_IMPORTED
    assert result.content_hash == bundle_hash


def test_import_conflict_at_bundle_level_returns_conflict() -> None:
    bundle = _make_bundle()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.rowcount = 0  # bundle INSERT did nothing — check existing hash
    mock_cursor.fetchone.return_value = ("old-hash-that-does-not-match",)
    result = import_research_evidence_bundle(mock_conn, bundle)
    assert result.status == ImportStatus.CONFLICT
    assert result.detail is not None


def test_import_bundle_with_observation_returns_imported() -> None:
    obs = _make_obs()
    bundle = _make_bundle(obs=(obs,))
    mock_conn = _make_mock_conn(fetchone_return=None)
    result = import_research_evidence_bundle(mock_conn, bundle)
    assert result.status == ImportStatus.IMPORTED


def test_import_bundle_with_finding_returns_imported() -> None:
    finding = _make_finding()
    bundle = _make_bundle(findings=(finding,))
    mock_conn = _make_mock_conn(fetchone_return=None)
    result = import_research_evidence_bundle(mock_conn, bundle)
    assert result.status == ImportStatus.IMPORTED


def test_import_bundle_with_crosscheck_returns_imported() -> None:
    cc = _make_crosscheck()
    bundle = _make_bundle(crosschecks=(cc,))
    mock_conn = _make_mock_conn(fetchone_return=None)
    result = import_research_evidence_bundle(mock_conn, bundle)
    assert result.status == ImportStatus.IMPORTED


def test_import_bundle_with_evidence_returns_imported() -> None:
    ev = _make_evidence()
    bundle = _make_bundle(evidence=(ev,))
    mock_conn = _make_mock_conn(fetchone_return=None)
    result = import_research_evidence_bundle(mock_conn, bundle)
    assert result.status == ImportStatus.IMPORTED


def test_import_bundle_observation_conflict_returns_conflict() -> None:
    """Observation INSERT conflicts (rowcount=0) and hash mismatches → CONFLICT."""
    obs = _make_obs()
    bundle = _make_bundle(obs=(obs,))
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    # Bundle INSERT succeeds (rowcount=1), observation INSERT conflicts (rowcount=0).
    rowcounts = iter([1, 0])

    def _on_execute(*args: Any, **kwargs: Any) -> None:
        mock_cursor.rowcount = next(rowcounts, 0)

    mock_cursor.execute.side_effect = _on_execute
    mock_cursor.fetchone.return_value = ("wrong-obs-hash",)
    result = import_research_evidence_bundle(mock_conn, bundle)
    assert result.status == ImportStatus.CONFLICT


# ---------------------------------------------------------------------------
# connection.py — open_connection with monkeypatch
# ---------------------------------------------------------------------------


def test_open_connection_calls_psycopg_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_connect = MagicMock(return_value=MagicMock())
    import psycopg

    monkeypatch.setattr(psycopg, "connect", mock_connect)
    from hullq.persistence.connection import open_connection

    conn = open_connection("postgresql://user:pass@localhost/db")
    mock_connect.assert_called_once_with("postgresql://user:pass@localhost/db")
    assert conn is mock_connect.return_value


def test_open_connection_uses_env_url_when_no_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HULLQ_DATABASE_URL", "postgresql://env-host/envdb")
    mock_connect = MagicMock(return_value=MagicMock())
    import psycopg

    monkeypatch.setattr(psycopg, "connect", mock_connect)
    from hullq.persistence.connection import open_connection

    open_connection()
    mock_connect.assert_called_once_with("postgresql://env-host/envdb")


# ---------------------------------------------------------------------------
# readback.py — pure _from_jsonb helpers
# ---------------------------------------------------------------------------


def test_target_from_jsonb_all_fields() -> None:
    from hullq.persistence.readback import _target_from_jsonb

    t = _target_from_jsonb({"manufacturer": "Catalina", "model": "316", "first_built": 1993})
    assert t.manufacturer == "Catalina"
    assert t.model == "316"
    assert t.first_built == 1993


def test_target_from_jsonb_nulls() -> None:
    from hullq.persistence.readback import _target_from_jsonb

    t = _target_from_jsonb({"manufacturer": None, "model": "X", "first_built": None})
    assert t.manufacturer is None
    assert t.first_built is None


def test_locator_from_jsonb_all_none() -> None:
    from hullq.persistence.readback import _locator_from_jsonb

    loc = _locator_from_jsonb(
        {
            "page": None,
            "section": None,
            "anchor": None,
            "table": None,
            "figure": None,
            "record_key": None,
        }
    )
    assert loc.page is None
    assert loc.section is None


def test_locator_from_jsonb_with_values() -> None:
    from hullq.persistence.readback import _locator_from_jsonb

    loc = _locator_from_jsonb(
        {
            "page": 42,
            "section": "A",
            "anchor": None,
            "table": None,
            "figure": None,
            "record_key": None,
        }
    )
    assert loc.page == 42
    assert loc.section == "A"


def test_raw_from_jsonb_literal() -> None:
    from hullq.persistence.readback import _raw_from_jsonb

    raw = _raw_from_jsonb({"kind": "literal", "value": "10.5", "unit": "m", "excerpt": None})
    assert str(raw.kind) == "literal"
    assert raw.value == "10.5"
    assert raw.unit == "m"


def test_normalized_from_jsonb_none() -> None:
    from hullq.persistence.readback import _normalized_from_jsonb

    assert _normalized_from_jsonb(None) is None


def test_normalized_from_jsonb_present() -> None:
    from hullq.persistence.readback import _normalized_from_jsonb
    from hullq.persistence.schema import (
        ENCODED_VALUE_PAYLOAD_KEY,
        ENCODED_VALUE_TYPE_KEY,
        ENCODED_VALUE_TYPE_RAW,
    )

    nc = _normalized_from_jsonb(
        {
            "value": {
                ENCODED_VALUE_TYPE_KEY: ENCODED_VALUE_TYPE_RAW,
                ENCODED_VALUE_PAYLOAD_KEY: 10.5,
            },
            "unit": "m",
            "method_id": "std",
            "method_version": "1.0",
        }
    )
    assert nc is not None
    assert nc.value == 10.5
    assert nc.unit == "m"


def test_producer_from_jsonb() -> None:
    from hullq.persistence.readback import _producer_from_jsonb

    p = _producer_from_jsonb(
        {
            "kind": "deterministic_tool",
            "identifier": "test",
            "version": "0.1",
            "model": None,
            "prompt_or_rule_version": None,
        }
    )
    assert p.identifier == "test"
    assert p.version == "0.1"


def test_context_from_jsonb() -> None:
    from hullq.persistence.readback import _context_from_jsonb

    ctx = _context_from_jsonb({"research_job_id": "JOB-1", "activity_id": "WAVE-1"})
    assert ctx.research_job_id == "JOB-1"
    assert ctx.activity_id == "WAVE-1"


# ---------------------------------------------------------------------------
# readback.py — fetch_bundle_snapshot with mock connection
# ---------------------------------------------------------------------------

_MOCK_TARGET_JSONB = {"manufacturer": None, "model": "Test 35", "first_built": None}

_MOCK_BUNDLE_ROW = {
    "bundle_id": "B-001",
    "bundle_version": "1.0",
    "content_hash": "abc123",
    "research_target": _MOCK_TARGET_JSONB,
    "research_job_id": None,
    "activity_id": None,
}


def test_fetch_bundle_snapshot_not_found_returns_none() -> None:
    from hullq.persistence.readback import fetch_bundle_snapshot

    mock_conn = _make_mock_conn(fetchone_return=None, fetchall_return=[])
    result = fetch_bundle_snapshot(mock_conn, "B-001", "1.0")
    assert result is None


def test_fetch_bundle_snapshot_found_returns_snapshot() -> None:
    from hullq.persistence.readback import BundleSnapshot, fetch_bundle_snapshot

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = _MOCK_BUNDLE_ROW
    mock_cursor.fetchall.return_value = []

    result = fetch_bundle_snapshot(mock_conn, "B-001", "1.0")
    assert isinstance(result, BundleSnapshot)
    assert result.bundle_id == "B-001"
    assert result.bundle_version == "1.0"
    assert result.content_hash == "abc123"
    assert result.research_target.model == "Test 35"
    assert result.observation_ids == ()
    assert result.finding_ids == ()
    assert result.crosscheck_ids == ()
    assert result.evidence_ids == ()


def test_fetch_bundle_snapshot_with_ids() -> None:
    from hullq.persistence.readback import BundleSnapshot, fetch_bundle_snapshot

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = _MOCK_BUNDLE_ROW
    # 4 fetchall calls: obs, findings, crosschecks, evidence
    mock_cursor.fetchall.side_effect = [
        [("OBS-001",), ("OBS-002",)],
        [("F-001",)],
        [],
        [("EV-001",)],
    ]

    result = fetch_bundle_snapshot(mock_conn, "B-001", "1.0")
    assert isinstance(result, BundleSnapshot)
    assert result.observation_ids == ("OBS-001", "OBS-002")
    assert result.finding_ids == ("F-001",)
    assert result.crosscheck_ids == ()
    assert result.evidence_ids == ("EV-001",)


# ---------------------------------------------------------------------------
# readback.py — fetch_observation / fetch_finding / fetch_crosscheck / fetch_evidence
#               (not-found path only — avoids complex full-reconstruction mocking)
# ---------------------------------------------------------------------------

_MOCK_OBS_ROW: dict[str, Any] = {
    "observation_id": "OBS-001",
    "content_hash": "hash1",
    "research_target": _MOCK_TARGET_JSONB,
    "source_id": "SRC-001",
    "source_locator": {
        "page": None,
        "section": None,
        "anchor": None,
        "table": None,
        "figure": None,
        "record_key": None,
    },
    "raw_observation": {"kind": "literal", "value": "10.5", "unit": "m", "excerpt": None},
    "normalized_candidate": None,
    "evidence_type": "manufacturer_specification",
    "claim_semantics": "nominal_design_value",
    "applicability": {
        "first_year": None,
        "last_year": None,
        "hull_number_from": None,
        "hull_number_to": None,
        "market_or_region": None,
        "named_variant_hint": None,
        "design_option_hints": None,
        "operating_state_hint": None,
        "individual_hull_or_listing_ref": None,
        "unknown_or_unbounded": True,
    },
    "producer": {
        "kind": "deterministic_tool",
        "identifier": "test",
        "version": "0.1",
        "model": None,
        "prompt_or_rule_version": None,
    },
    "research_context": {"research_job_id": None, "activity_id": None},
    "observed_at": "2026-08-20T00:00:00Z",
    "confidence": "high",
    "supersedes_observation_id": None,
    "intended_subject_kind_hint": None,
    "intended_field_pointer": None,
    "notes": None,
}


def test_fetch_observation_not_found_returns_none() -> None:
    from hullq.persistence.readback import fetch_observation

    mock_conn = _make_mock_conn(fetchone_return=None)
    assert fetch_observation(mock_conn, "OBS-999") is None


def test_fetch_observation_found_returns_observation() -> None:
    from hullq.persistence.readback import fetch_observation

    mock_conn = _make_mock_conn(fetchone_return=_MOCK_OBS_ROW)
    obs = fetch_observation(mock_conn, "OBS-001")
    assert obs is not None
    assert obs.observation_id == "OBS-001"
    assert obs.source_id == "SRC-001"


def test_fetch_finding_not_found_returns_none() -> None:
    from hullq.persistence.readback import fetch_finding

    mock_conn = _make_mock_conn(fetchone_return=None)
    assert fetch_finding(mock_conn, "F-999", "B-001", "1.0") is None


def test_fetch_crosscheck_not_found_returns_none() -> None:
    from hullq.persistence.readback import fetch_crosscheck

    mock_conn = _make_mock_conn(fetchone_return=None)
    assert fetch_crosscheck(mock_conn, "CC-999", "B-001", "1.0") is None


def test_fetch_evidence_not_found_returns_none() -> None:
    from hullq.persistence.readback import fetch_evidence

    mock_conn = _make_mock_conn(fetchone_return=None)
    assert fetch_evidence(mock_conn, "EV-999") is None
