"""PostgreSQL tests for `hullq.persistence.field_resolution` — SLICE-0051
FieldResolution blocker-resolution amendment.

Covers the accepted OQ-004 / ADR-0006 invariants
(`specs/PROVENANCE_MODEL.v0.1.md`, `specs/FIELD_RESOLUTION_SCHEMA.v0.1.json`)
mechanically enforced by the new durable persistence layer: immutable
versioned history, exactly one current resolution per logical subject
field, race-safe idempotent writes, stale-predecessor rejection, evidence
existence/compatibility checks (VAL-PROV-004), and source-rights admission
(`SOURCE_RIGHTS_POLICY.v0.1.md`, `SourceUse.PRODUCTION_VALUE`) for a
resolved production value.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Generator
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
    FieldEvidenceV3,
    FieldResolution,
    JsonPointer,
    NormalizedCandidate,
    ObservationApplicability,
    ProducerKind,
    ProducerMetadata,
    ProvenanceSubject,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    ResolutionMethod,
    ResolutionState,
    ResolverKind,
    ResolverMetadata,
    SourceLocator,
    SubjectKind,
)
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.field_resolution import (
    FieldResolutionWriteStatus,
    decode_canonical_decimal_snapshot,
    encode_canonical_decimal_snapshot,
    fetch_current_field_resolution,
    fetch_field_resolution,
    list_field_resolution_history,
    write_field_resolution,
)
from hullq.persistence.importer import import_research_evidence_bundle
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import ResearchEvidenceBundle

REPO_ROOT = Path(__file__).resolve().parents[2]
_WIKIDATA_SOURCE = json.loads(
    (REPO_ROOT / "fixtures" / "sources" / "wikidata_source.json").read_text(encoding="utf-8")
)
_WIKIDATA_SOURCE_ID = _WIKIDATA_SOURCE["source_id"]

# ---------------------------------------------------------------------------
# Disposable-schema fixture (mirrors other SLICE-0051 persistence tests)
# ---------------------------------------------------------------------------


def _with_search_path(base_url: str, schema_name: str) -> str:
    parts = urlsplit(base_url)
    option = quote(f"-c search_path={schema_name}", safe="")
    query = f"{parts.query}&options={option}" if parts.query else f"options={option}"
    return urlunsplit(parts._replace(query=query))


def _create_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
    finally:
        conn.close()


def _drop_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
    finally:
        conn.close()


@pytest.fixture()
def db_url_isolated(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0051fr_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


@pytest.fixture()
def conn(db_url_isolated: str) -> Generator[Any]:
    connection = psycopg.connect(db_url_isolated)
    try:
        yield connection
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _evidence(
    evidence_id: str,
    *,
    subject_kind: SubjectKind = SubjectKind.BOAT_DESIGN,
    subject_id: str = "BD-FR-TEST",
    field_pointer: str = "/baseline/dimensions/draft_max_m",
    source_id: str = _WIKIDATA_SOURCE_ID,
    value: str = "1.60",
) -> FieldEvidenceV3:
    return FieldEvidenceV3(
        evidence_id=evidence_id,
        subject=ProvenanceSubject(kind=subject_kind, id=subject_id),
        field_pointer=JsonPointer(field_pointer),
        source_id=source_id,
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(
            kind=RawObservationKind.STRUCTURED_RECORD, value=value, unit="m", excerpt=None
        ),
        normalized_candidate=NormalizedCandidate(
            value=value, unit="m", method_id="test-normalize", method_version="1"
        ),
        evidence_type=EvidenceType.STRUCTURED_DATASET,
        producer=ProducerMetadata(
            kind=ProducerKind.DETERMINISTIC_TOOL,
            identifier="test-harness",
            version="1",
            model=None,
            prompt_or_rule_version=None,
        ),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-09-12T00:00:00+00:00",
        confidence=ConfidenceLevel.HIGH,
        supersedes_evidence_id=None,
        notes=None,
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
        applicability=ObservationApplicability(
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
        ),
    )


def _import_evidence(conn: Any, *evidence: FieldEvidenceV3) -> None:
    bundle = ResearchEvidenceBundle(
        bundle_id=f"BUNDLE-{uuid.uuid4().hex[:8]}",
        bundle_version="1",
        research_target=ResearchTarget(manufacturer=None, model="test", first_built=None),
        research_job_id=None,
        activity_id=None,
        observations=(),
        unresolved_findings=(),
        promoted_evidence=tuple(evidence),
        reference_crosschecks=(),
    )
    result = import_research_evidence_bundle(conn, bundle)
    assert result.status.value in ("imported", "already_imported"), result
    conn.commit()


def _resolution(
    resolution_id: str,
    *,
    subject_kind: SubjectKind = SubjectKind.BOAT_DESIGN,
    subject_id: str = "BD-FR-TEST",
    field_pointer: str = "/baseline/dimensions/draft_max_m",
    state: ResolutionState = ResolutionState.RESOLVED,
    value: Decimal | None = Decimal("1.60"),
    supporting_evidence_ids: frozenset[str] = frozenset(),
    contradicting_evidence_ids: frozenset[str] = frozenset(),
    considered_evidence_ids: frozenset[str] | None = None,
    supersedes_resolution_id: str | None = None,
) -> FieldResolution:
    snapshot = encode_canonical_decimal_snapshot(value) if value is not None else None
    considered = (
        considered_evidence_ids
        if considered_evidence_ids is not None
        else supporting_evidence_ids | contradicting_evidence_ids
    )
    return FieldResolution(
        resolution_id=resolution_id,
        subject=ProvenanceSubject(kind=subject_kind, id=subject_id),
        field_pointer=JsonPointer(field_pointer),
        state=state,
        canonical_value_snapshot=snapshot,
        supporting_evidence_ids=supporting_evidence_ids,
        contradicting_evidence_ids=contradicting_evidence_ids,
        considered_evidence_ids=considered,
        resolution_method=ResolutionMethod.UNANIMOUS_EVIDENCE,
        policy_version="test-policy-1",
        resolver=ResolverMetadata(
            kind=ResolverKind.DETERMINISTIC_TOOL, identifier="test", version="1"
        ),
        resolved_at="2026-09-12T00:00:00+00:00",
        supersedes_resolution_id=supersedes_resolution_id,
        notes=None,
    )


# ---------------------------------------------------------------------------
# Canonical-value snapshot encoding
# ---------------------------------------------------------------------------


def test_encode_decode_decimal_snapshot_round_trips_exactly() -> None:
    value = Decimal("1.10000000000000000000001")
    encoded = encode_canonical_decimal_snapshot(value)
    assert isinstance(encoded, str)
    assert decode_canonical_decimal_snapshot(encoded) == value


def test_decode_rejects_non_string_payload() -> None:
    with pytest.raises(ValueError):
        decode_canonical_decimal_snapshot(1.6)


# ---------------------------------------------------------------------------
# Migration / clean upgrade
# ---------------------------------------------------------------------------


def test_clean_migration_creates_expected_tables(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = current_schema() AND table_name IN "
            "('field_resolutions', 'field_resolution_heads')"
        )
        tables = {row[0] for row in cur.fetchall()}
    assert tables == {"field_resolutions", "field_resolution_heads"}


# ---------------------------------------------------------------------------
# Write / read: create, immutable history, current-head readback
# ---------------------------------------------------------------------------


def test_create_first_resolution_and_readback(conn: Any) -> None:
    _import_evidence(conn, _evidence("EV-CREATE-1"))
    resolution = _resolution("FR-CREATE-1", supporting_evidence_ids=frozenset({"EV-CREATE-1"}))

    result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert result.status is FieldResolutionWriteStatus.CREATED
    assert result.current_resolution_id == "FR-CREATE-1"
    conn.commit()

    current = fetch_current_field_resolution(
        conn, SubjectKind.BOAT_DESIGN, "BD-FR-TEST", "/baseline/dimensions/draft_max_m"
    )
    assert current is not None
    assert current.resolution_id == "FR-CREATE-1"
    assert current.state is ResolutionState.RESOLVED
    assert decode_canonical_decimal_snapshot(current.canonical_value_snapshot) == Decimal("1.60")


def test_revision_preserves_old_and_advances_head(conn: Any) -> None:
    _import_evidence(conn, _evidence("EV-REV-1"), _evidence("EV-REV-2"))
    first = _resolution("FR-REV-1", supporting_evidence_ids=frozenset({"EV-REV-1"}))
    write_field_resolution(
        conn,
        resolution=first,
        expected_current_resolution_id=None,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    conn.commit()

    second = _resolution(
        "FR-REV-2",
        value=Decimal("1.70"),
        supporting_evidence_ids=frozenset({"EV-REV-2"}),
        supersedes_resolution_id="FR-REV-1",
    )
    result = write_field_resolution(
        conn,
        resolution=second,
        expected_current_resolution_id="FR-REV-1",
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert result.status is FieldResolutionWriteStatus.REVISED
    conn.commit()

    current = fetch_current_field_resolution(
        conn, SubjectKind.BOAT_DESIGN, "BD-FR-TEST", "/baseline/dimensions/draft_max_m"
    )
    assert current is not None and current.resolution_id == "FR-REV-2"

    old = fetch_field_resolution(conn, "FR-REV-1")
    assert old is not None
    assert decode_canonical_decimal_snapshot(old.canonical_value_snapshot) == Decimal("1.60")

    history = list_field_resolution_history(
        conn, SubjectKind.BOAT_DESIGN, "BD-FR-TEST", "/baseline/dimensions/draft_max_m"
    )
    assert {r.resolution_id for r in history} == {"FR-REV-1", "FR-REV-2"}


def test_exact_retry_is_idempotent(conn: Any) -> None:
    _import_evidence(conn, _evidence("EV-IDEMP-1"))
    resolution = _resolution("FR-IDEMP-1", supporting_evidence_ids=frozenset({"EV-IDEMP-1"}))
    sources = {_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE}

    first = write_field_resolution(
        conn, resolution=resolution, expected_current_resolution_id=None, available_sources=sources
    )
    assert first.status is FieldResolutionWriteStatus.CREATED
    conn.commit()

    retry = write_field_resolution(
        conn, resolution=resolution, expected_current_resolution_id=None, available_sources=sources
    )
    assert retry.status is FieldResolutionWriteStatus.ALREADY_EXISTS
    assert retry.current_resolution_id == "FR-IDEMP-1"
    conn.commit()

    history = list_field_resolution_history(
        conn, SubjectKind.BOAT_DESIGN, "BD-FR-TEST", "/baseline/dimensions/draft_max_m"
    )
    assert len(history) == 1


def test_stale_predecessor_conflict_leaves_head_unchanged(conn: Any) -> None:
    _import_evidence(conn, _evidence("EV-STALE-1"), _evidence("EV-STALE-2"))
    sources = {_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE}
    first = _resolution("FR-STALE-1", supporting_evidence_ids=frozenset({"EV-STALE-1"}))
    write_field_resolution(
        conn, resolution=first, expected_current_resolution_id=None, available_sources=sources
    )
    conn.commit()

    stale_attempt = _resolution(
        "FR-STALE-2",
        value=Decimal("1.70"),
        supporting_evidence_ids=frozenset({"EV-STALE-2"}),
        supersedes_resolution_id="FR-NEVER-EXISTED",
    )
    result = write_field_resolution(
        conn,
        resolution=stale_attempt,
        expected_current_resolution_id="FR-NEVER-EXISTED",  # stale/forged predecessor
        available_sources=sources,
    )
    assert result.status is FieldResolutionWriteStatus.CONFLICT
    assert result.current_resolution_id == "FR-STALE-1"
    conn.commit()

    current = fetch_current_field_resolution(
        conn, SubjectKind.BOAT_DESIGN, "BD-FR-TEST", "/baseline/dimensions/draft_max_m"
    )
    assert current is not None and current.resolution_id == "FR-STALE-1"
    history = list_field_resolution_history(
        conn, SubjectKind.BOAT_DESIGN, "BD-FR-TEST", "/baseline/dimensions/draft_max_m"
    )
    assert len(history) == 1  # the rejected attempt left no orphan revision


def test_first_write_with_nonnull_expected_fails_closed(conn: Any) -> None:
    """A caller claiming a current head exists when none does must fail
    CONFLICT, not silently succeed by creating a fresh first resolution."""
    _import_evidence(conn, _evidence("EV-FORGED-1"))
    forged_first = _resolution(
        "FR-FORGED-1",
        supporting_evidence_ids=frozenset({"EV-FORGED-1"}),
        supersedes_resolution_id="FR-DOES-NOT-EXIST",
    )
    result = write_field_resolution(
        conn,
        resolution=forged_first,
        expected_current_resolution_id="FR-DOES-NOT-EXIST",
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert result.status is FieldResolutionWriteStatus.CONFLICT
    conn.commit()

    current = fetch_current_field_resolution(
        conn, SubjectKind.BOAT_DESIGN, "BD-FR-TEST", "/baseline/dimensions/draft_max_m"
    )
    assert current is None


# ---------------------------------------------------------------------------
# Evidence existence / compatibility (VAL-PROV-004)
# ---------------------------------------------------------------------------


def test_missing_evidence_id_fails_closed(conn: Any) -> None:
    resolution = _resolution(
        "FR-MISSING-EV", supporting_evidence_ids=frozenset({"EV-NEVER-IMPORTED"})
    )
    result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert result.status is FieldResolutionWriteStatus.EVIDENCE_NOT_FOUND
    assert result.current_resolution_id is None

    current = fetch_current_field_resolution(
        conn, SubjectKind.BOAT_DESIGN, "BD-FR-TEST", "/baseline/dimensions/draft_max_m"
    )
    assert current is None


def test_evidence_subject_mismatch_fails_closed(conn: Any) -> None:
    """Evidence recorded for a different subject_id must not be usable to
    support a resolution for this subject."""
    _import_evidence(conn, _evidence("EV-WRONG-SUBJECT", subject_id="BD-SOME-OTHER-DESIGN"))
    resolution = _resolution(
        "FR-MISMATCH-1", supporting_evidence_ids=frozenset({"EV-WRONG-SUBJECT"})
    )
    result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert result.status is FieldResolutionWriteStatus.INVARIANTS_VIOLATED
    assert result.detail is not None and "subject" in result.detail.lower()


def test_evidence_field_pointer_mismatch_fails_closed(conn: Any) -> None:
    _import_evidence(conn, _evidence("EV-WRONG-FIELD", field_pointer="/baseline/dimensions/loa_m"))
    resolution = _resolution("FR-MISMATCH-2", supporting_evidence_ids=frozenset({"EV-WRONG-FIELD"}))
    result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert result.status is FieldResolutionWriteStatus.INVARIANTS_VIOLATED


def test_supporting_not_subset_of_considered_fails_closed(conn: Any) -> None:
    _import_evidence(conn, _evidence("EV-SUBSET-1"))
    resolution = _resolution(
        "FR-SUBSET-1",
        supporting_evidence_ids=frozenset({"EV-SUBSET-1"}),
        considered_evidence_ids=frozenset(),  # deliberately excludes the supporting id
    )
    result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert result.status is FieldResolutionWriteStatus.INVARIANTS_VIOLATED


# ---------------------------------------------------------------------------
# Source-rights admission
# ---------------------------------------------------------------------------


def test_source_not_in_available_sources_fails_closed(conn: Any) -> None:
    _import_evidence(conn, _evidence("EV-NOSRC-1", source_id="SRC-UNAVAILABLE"))
    resolution = _resolution("FR-NOSRC-1", supporting_evidence_ids=frozenset({"EV-NOSRC-1"}))
    result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={},  # the evidence's source is not supplied
    )
    assert result.status is FieldResolutionWriteStatus.SOURCE_NOT_AVAILABLE


def test_source_use_denied_fails_closed(conn: Any) -> None:
    prohibited_source = {
        **_WIKIDATA_SOURCE,
        "source_id": "SRC-PROHIBITED",
        "rights": {
            **_WIKIDATA_SOURCE["rights"],
            "clearance": {
                **_WIKIDATA_SOURCE["rights"]["clearance"],
                "production_value": "prohibited",
            },
        },
    }
    _import_evidence(conn, _evidence("EV-DENIED-1", source_id="SRC-PROHIBITED"))
    resolution = _resolution("FR-DENIED-1", supporting_evidence_ids=frozenset({"EV-DENIED-1"}))
    result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={"SRC-PROHIBITED": prohibited_source},
    )
    assert result.status is FieldResolutionWriteStatus.SOURCE_USE_DENIED


def test_allowed_source_production_value_clearance_succeeds(conn: Any) -> None:
    _import_evidence(conn, _evidence("EV-ALLOWED-1"))
    resolution = _resolution("FR-ALLOWED-1", supporting_evidence_ids=frozenset({"EV-ALLOWED-1"}))
    result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert result.status is FieldResolutionWriteStatus.CREATED


def test_unresolved_state_skips_source_rights_check_entirely(conn: Any) -> None:
    """An `unknown` resolution carries no supporting evidence to admit
    (VAL-PROV-005/007) -- it must succeed even when no source is supplied,
    since source-rights admission only applies to resolved production
    values."""
    resolution = _resolution(
        "FR-UNKNOWN-1",
        state=ResolutionState.UNKNOWN,
        value=None,
        supporting_evidence_ids=frozenset(),
        contradicting_evidence_ids=frozenset(),
        considered_evidence_ids=frozenset(),
    )
    result = write_field_resolution(
        conn, resolution=resolution, expected_current_resolution_id=None, available_sources={}
    )
    assert result.status is FieldResolutionWriteStatus.CREATED

    current = fetch_current_field_resolution(
        conn, SubjectKind.BOAT_DESIGN, "BD-FR-TEST", "/baseline/dimensions/draft_max_m"
    )
    assert current is not None
    assert current.state is ResolutionState.UNKNOWN
    assert current.canonical_value_snapshot is None


# ---------------------------------------------------------------------------
# resolved_with_conflict preserves contradicting evidence
# ---------------------------------------------------------------------------


def test_resolved_with_conflict_retains_contradicting_evidence(conn: Any) -> None:
    _import_evidence(
        conn,
        _evidence("EV-CONFLICT-SUPPORT", value="1.60"),
        _evidence("EV-CONFLICT-AGAINST", value="1.90"),
    )
    resolution = _resolution(
        "FR-CONFLICT-1",
        state=ResolutionState.RESOLVED_WITH_CONFLICT,
        value=Decimal("1.60"),
        supporting_evidence_ids=frozenset({"EV-CONFLICT-SUPPORT"}),
        contradicting_evidence_ids=frozenset({"EV-CONFLICT-AGAINST"}),
    )
    result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert result.status is FieldResolutionWriteStatus.CREATED
    conn.commit()

    current = fetch_current_field_resolution(
        conn, SubjectKind.BOAT_DESIGN, "BD-FR-TEST", "/baseline/dimensions/draft_max_m"
    )
    assert current is not None
    assert current.state is ResolutionState.RESOLVED_WITH_CONFLICT
    assert current.contradicting_evidence_ids == frozenset({"EV-CONFLICT-AGAINST"})
    assert decode_canonical_decimal_snapshot(current.canonical_value_snapshot) == Decimal("1.60")


# ---------------------------------------------------------------------------
# Rollback / failure injection: a rejected write leaves zero durable trace
# ---------------------------------------------------------------------------


def test_rejected_write_leaves_no_orphan_revision_or_head(conn: Any) -> None:
    _import_evidence(conn, _evidence("EV-ROLLBACK-1", source_id="SRC-WILL-BE-DENIED"))
    denied_source = {
        **_WIKIDATA_SOURCE,
        "source_id": "SRC-WILL-BE-DENIED",
        "rights": {
            **_WIKIDATA_SOURCE["rights"],
            "clearance": {**_WIKIDATA_SOURCE["rights"]["clearance"], "production_value": "unknown"},
        },
    }
    resolution = _resolution("FR-ROLLBACK-1", supporting_evidence_ids=frozenset({"EV-ROLLBACK-1"}))
    result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={"SRC-WILL-BE-DENIED": denied_source},
    )
    assert result.status is FieldResolutionWriteStatus.SOURCE_USE_DENIED

    assert fetch_field_resolution(conn, "FR-ROLLBACK-1") is None
    assert (
        fetch_current_field_resolution(
            conn, SubjectKind.BOAT_DESIGN, "BD-FR-TEST", "/baseline/dimensions/draft_max_m"
        )
        is None
    )


# ---------------------------------------------------------------------------
# Exact Decimal, adversarial precision
# ---------------------------------------------------------------------------


def test_extreme_precision_decimal_snapshot_round_trips_through_postgresql(conn: Any) -> None:
    exact = Decimal("1.10000000000000000000000000000001")
    _import_evidence(conn, _evidence("EV-PRECISE-1", value=str(exact)))
    resolution = _resolution(
        "FR-PRECISE-1", value=exact, supporting_evidence_ids=frozenset({"EV-PRECISE-1"})
    )
    result = write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    assert result.status is FieldResolutionWriteStatus.CREATED
    conn.commit()

    current = fetch_current_field_resolution(
        conn, SubjectKind.BOAT_DESIGN, "BD-FR-TEST", "/baseline/dimensions/draft_max_m"
    )
    assert current is not None
    assert decode_canonical_decimal_snapshot(current.canonical_value_snapshot) == exact


def test_small_precision_decimal_snapshot_round_trips_through_postgresql(conn: Any) -> None:
    exact = Decimal("0.0000000000000000000000000001")
    _import_evidence(conn, _evidence("EV-TINY-1", value=str(exact)))
    resolution = _resolution(
        "FR-TINY-1", value=exact, supporting_evidence_ids=frozenset({"EV-TINY-1"})
    )
    write_field_resolution(
        conn,
        resolution=resolution,
        expected_current_resolution_id=None,
        available_sources={_WIKIDATA_SOURCE_ID: _WIKIDATA_SOURCE},
    )
    conn.commit()

    current = fetch_current_field_resolution(
        conn, SubjectKind.BOAT_DESIGN, "BD-FR-TEST", "/baseline/dimensions/draft_max_m"
    )
    assert current is not None
    assert decode_canonical_decimal_snapshot(current.canonical_value_snapshot) == exact
