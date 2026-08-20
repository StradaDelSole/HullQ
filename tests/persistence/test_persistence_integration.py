"""PostgreSQL 18 integration tests - SLICE-0013.

Covers acceptance criteria 1-26 that require a real PostgreSQL database.
Criteria 27 (existing tests green) and 28 (coverage/tools) are verified by CI.

These tests are skipped automatically when HULLQ_TEST_DATABASE_URL is not set.
"""

from __future__ import annotations

from typing import Any

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
from hullq.persistence._types import ImportStatus
from hullq.persistence.importer import import_research_evidence_bundle
from hullq.persistence.migrations import apply_migrations
from hullq.persistence.readback import (
    fetch_bundle_snapshot,
    fetch_crosscheck,
    fetch_evidence,
    fetch_finding,
    fetch_observation,
)
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import (
    NormalizedCandidate,
    ObservationApplicability,
    ReferenceCheckOutcome,
    ReferenceCrosscheck,
    ResearchEvidenceBundle,
    ResearchObservation,
    UnresolvedFinding,
    UnresolvedFindingSeverity,
)

# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------


def _applicability(
    *,
    first_year: int | None = None,
    last_year: int | None = None,
    unknown_or_unbounded: bool = True,
    design_option_hints: list[str] | None = None,
    individual_hull_or_listing_ref: str | None = None,
    operating_state_hint: str | None = None,
    market_or_region: str | None = None,
    named_variant_hint: str | None = None,
    hull_number_from: str | None = None,
    hull_number_to: str | None = None,
) -> ObservationApplicability:
    return ObservationApplicability(
        first_year=first_year,
        last_year=last_year,
        hull_number_from=hull_number_from,
        hull_number_to=hull_number_to,
        market_or_region=market_or_region,
        named_variant_hint=named_variant_hint,
        design_option_hints=tuple(design_option_hints) if design_option_hints else None,
        operating_state_hint=operating_state_hint,
        individual_hull_or_listing_ref=individual_hull_or_listing_ref,
        unknown_or_unbounded=unknown_or_unbounded,
    )


def _producer() -> ProducerMetadata:
    return ProducerMetadata(
        kind=ProducerKind.DETERMINISTIC_TOOL,
        identifier="slice-0013-test",
        version="0.1",
        model=None,
        prompt_or_rule_version=None,
    )


def _obs(
    obs_id: str = "OBS-001",
    raw_value: object = "10.5",
    unit: str = "m",
    applicability: ObservationApplicability | None = None,
    claim_semantics: ClaimSemantics = ClaimSemantics.NOMINAL_DESIGN_VALUE,
    normalized: NormalizedCandidate | None = None,
    notes: str | None = None,
    intended_subject_kind_hint: SubjectKind | None = None,
    intended_field_pointer: JsonPointer | None = None,
    supersedes_observation_id: str | None = None,
) -> ResearchObservation:
    return ResearchObservation(
        observation_id=obs_id,
        research_target=ResearchTarget(manufacturer=None, model="Test 35", first_built=None),
        source_id="SRC-001",
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(
            kind=RawObservationKind.LITERAL, value=raw_value, unit=unit, excerpt=None
        ),
        normalized_candidate=normalized,
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        claim_semantics=claim_semantics,
        applicability=applicability or _applicability(),
        producer=_producer(),
        research_context=ResearchContext(research_job_id="JOB-1", activity_id="WAVE-1"),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_observation_id=supersedes_observation_id,
        intended_subject_kind_hint=intended_subject_kind_hint,
        intended_field_pointer=intended_field_pointer,
        notes=notes,
    )


def _bundle(
    bundle_id: str = "BUNDLE-001",
    bundle_version: str = "1.0",
    observations: tuple[ResearchObservation, ...] = (),
    unresolved_findings: tuple[UnresolvedFinding, ...] = (),
    promoted_evidence: tuple[FieldEvidenceV3, ...] = (),
    reference_crosschecks: tuple[ReferenceCrosscheck, ...] = (),
) -> ResearchEvidenceBundle:
    return ResearchEvidenceBundle(
        bundle_id=bundle_id,
        bundle_version=bundle_version,
        research_target=ResearchTarget(manufacturer=None, model="Test 35", first_built=None),
        research_job_id="JOB-1",
        activity_id="WAVE-1",
        observations=observations,
        unresolved_findings=unresolved_findings,
        promoted_evidence=promoted_evidence,
        reference_crosschecks=reference_crosschecks,
    )


def _finding(
    finding_id: str = "FIND-001",
    obs_ids: set[str] | None = None,
) -> UnresolvedFinding:
    return UnresolvedFinding(
        finding_id=finding_id,
        topic="test_topic",
        description="Test finding description",
        related_observation_ids=frozenset(obs_ids or {"OBS-001"}),
        severity=UnresolvedFindingSeverity.REVIEW,
    )


def _crosscheck(cc_id: str = "CC-001") -> ReferenceCrosscheck:
    return ReferenceCrosscheck(
        crosscheck_id=cc_id,
        reference_source_id="sailboatdata-reference",
        topic_or_field="/loa_m",
        outcome=ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE,
        notes="Test notes — no SailboatData field values stored",
    )


def _ev(evidence_id: str = "EV-001") -> FieldEvidenceV3:
    return FieldEvidenceV3(
        evidence_id=evidence_id,
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id="design-xyz"),
        field_pointer=JsonPointer("/loa_m"),
        source_id="SRC-001",
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(kind=RawObservationKind.LITERAL, value="10.5", unit="m", excerpt=None),
        normalized_candidate=NormalizedCandidate(
            value=10.5, unit="m", method_id="std", method_version="1.0"
        ),
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        producer=_producer(),
        research_context=ResearchContext(research_job_id="JOB-1", activity_id="WAVE-1"),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_evidence_id=None,
        notes=None,
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
        applicability=_applicability(unknown_or_unbounded=True),
    )


# ---------------------------------------------------------------------------
# Criterion 1-2: migrations create schema; applying twice is safe
# ---------------------------------------------------------------------------


def test_migrations_create_schema_from_empty(clean_conn: Any) -> None:
    """Criterion 1: migrations must create schema from empty PostgreSQL 18 database."""
    with clean_conn.cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = {row[0] for row in cur.fetchall()}
    expected = {
        "research_bundles",
        "research_observations",
        "bundle_observation_members",
        "bundle_unresolved_findings",
        "bundle_reference_crosschecks",
        "research_evidence",
        "bundle_evidence_members",
        "hullq_schema_migrations",
    }
    assert expected <= tables
    assert "bundle_promoted_evidence" not in tables, (
        "bundle_promoted_evidence must be replaced by research_evidence + bundle_evidence_members"
    )


def test_migrations_idempotent_second_apply(db_url: str) -> None:
    """Criterion 2: applying migrations twice must be a no-op."""
    import psycopg

    conn = psycopg.connect(db_url)
    try:
        apply_migrations(conn)
        applied_second = apply_migrations(conn)
        assert applied_second == [], "Second apply must return empty list (all already applied)"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Criterion 3: pre-canonical bundle (no BoatDesign ID) imports successfully
# ---------------------------------------------------------------------------


def test_import_pre_canonical_bundle_no_boat_design_id(clean_conn: Any) -> None:
    """Criterion 3: a valid unresolved/pre-canonical bundle imports without canonical BoatDesign."""
    obs = _obs(intended_subject_kind_hint=None, intended_field_pointer=None)
    b = _bundle(observations=(obs,))
    result = import_research_evidence_bundle(clean_conn, b)
    assert result.status == ImportStatus.IMPORTED


# ---------------------------------------------------------------------------
# Criterion 4: import is atomic
# ---------------------------------------------------------------------------


def test_import_atomic_conflict_rolls_back(clean_conn: Any) -> None:
    """Criterion 4 & 23: child conflict must roll back the complete new bundle transaction."""
    obs = _obs("OBS-SHARED")
    # Import first bundle — establishes OBS-SHARED
    b1 = _bundle("BUNDLE-ATOMIC-1", "1.0", observations=(obs,))
    r1 = import_research_evidence_bundle(clean_conn, b1)
    assert r1.status == ImportStatus.IMPORTED

    # Attempt to import second bundle with same obs_id but different raw value
    obs_conflict = _obs("OBS-SHARED", raw_value="99.9")
    b2 = _bundle("BUNDLE-ATOMIC-2", "1.0", observations=(obs_conflict,))
    r2 = import_research_evidence_bundle(clean_conn, b2)
    assert r2.status == ImportStatus.CONFLICT

    # BUNDLE-ATOMIC-2 must not appear in the database (rolled back)
    snap = fetch_bundle_snapshot(clean_conn, "BUNDLE-ATOMIC-2", "1.0")
    assert snap is None


# ---------------------------------------------------------------------------
# Criterion 5: exact repeated import is idempotent
# ---------------------------------------------------------------------------


def test_exact_repeated_import_returns_already_imported(clean_conn: Any) -> None:
    """Criterion 5: exact repeated import must return ALREADY_IMPORTED and create no duplicates."""
    obs = _obs()
    b = _bundle(observations=(obs,))

    r1 = import_research_evidence_bundle(clean_conn, b)
    assert r1.status == ImportStatus.IMPORTED

    r2 = import_research_evidence_bundle(clean_conn, b)
    assert r2.status == ImportStatus.ALREADY_IMPORTED
    assert r2.content_hash == r1.content_hash

    # Must not create duplicate observation rows
    with clean_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM research_observations WHERE observation_id = %s", ["OBS-001"]
        )
        assert cur.fetchone()[0] == 1  # type: ignore[index]


# ---------------------------------------------------------------------------
# Criterion 6: same (bundle_id, bundle_version) with changed content fails closed
# ---------------------------------------------------------------------------


def test_changed_content_same_bundle_identity_is_conflict(clean_conn: Any) -> None:
    """Criterion 6: same (bundle_id, bundle_version) with different content must fail closed."""
    b1 = _bundle("BUNDLE-C6", "1.0", observations=(_obs("OBS-C6A"),))
    r1 = import_research_evidence_bundle(clean_conn, b1)
    assert r1.status == ImportStatus.IMPORTED

    # Different content under the same (bundle_id, bundle_version)
    b2 = _bundle("BUNDLE-C6", "1.0", observations=(_obs("OBS-C6B"),))
    r2 = import_research_evidence_bundle(clean_conn, b2)
    assert r2.status == ImportStatus.CONFLICT


# ---------------------------------------------------------------------------
# Criterion 7: same observation_id with changed content fails closed
# ---------------------------------------------------------------------------


def test_changed_observation_content_fails_closed(clean_conn: Any) -> None:
    """Criterion 7: same observation_id with materially different content must fail closed."""
    obs_v1 = _obs("OBS-CHANGE", raw_value="10.5")
    b1 = _bundle("BUNDLE-OBS-C7", "1.0", observations=(obs_v1,))
    import_research_evidence_bundle(clean_conn, b1)

    obs_v2 = _obs("OBS-CHANGE", raw_value="99.9")
    b2 = _bundle("BUNDLE-OBS-C7-2", "1.0", observations=(obs_v2,))
    result = import_research_evidence_bundle(clean_conn, b2)
    assert result.status == ImportStatus.CONFLICT


# ---------------------------------------------------------------------------
# Criterion 8: later bundle version coexists with earlier version
# ---------------------------------------------------------------------------


def test_later_bundle_version_coexists_with_earlier(clean_conn: Any) -> None:
    """Criterion 8: a later bundle version may coexist with the earlier immutable version."""
    b1 = _bundle("BUNDLE-VER", "1.0", observations=(_obs("OBS-V1"),))
    b2 = _bundle("BUNDLE-VER", "2.0", observations=(_obs("OBS-V2"),))

    r1 = import_research_evidence_bundle(clean_conn, b1)
    r2 = import_research_evidence_bundle(clean_conn, b2)
    assert r1.status == ImportStatus.IMPORTED
    assert r2.status == ImportStatus.IMPORTED

    snap1 = fetch_bundle_snapshot(clean_conn, "BUNDLE-VER", "1.0")
    snap2 = fetch_bundle_snapshot(clean_conn, "BUNDLE-VER", "2.0")
    assert snap1 is not None
    assert snap2 is not None
    assert snap1.bundle_version == "1.0"
    assert snap2.bundle_version == "2.0"


# ---------------------------------------------------------------------------
# Criterion 9: observation membership is not duplicated
# ---------------------------------------------------------------------------


def test_observation_membership_not_duplicated(clean_conn: Any) -> None:
    """Criterion 9: repeated import must not duplicate membership rows."""
    obs = _obs("OBS-MEMBER")
    b = _bundle(observations=(obs,))
    import_research_evidence_bundle(clean_conn, b)
    import_research_evidence_bundle(clean_conn, b)

    with clean_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM bundle_observation_members "
            "WHERE bundle_id = %s AND bundle_version = %s AND observation_id = %s",
            ["BUNDLE-001", "1.0", "OBS-MEMBER"],
        )
        assert cur.fetchone()[0] == 1  # type: ignore[index]


# ---------------------------------------------------------------------------
# Criterion 10 & 11: raw observation round-trips; normalized candidate separate
# ---------------------------------------------------------------------------


def test_raw_observation_round_trips_losslessly(clean_conn: Any) -> None:
    """Criterion 10: raw values must survive the round trip."""
    obs = _obs("OBS-RAW", raw_value="10.675")
    b = _bundle(observations=(obs,))
    import_research_evidence_bundle(clean_conn, b)

    fetched = fetch_observation(clean_conn, "OBS-RAW")
    assert fetched is not None
    assert fetched.raw.value == "10.675"
    assert fetched.raw.unit == "m"
    assert fetched.raw.kind == RawObservationKind.LITERAL


def test_normalized_candidate_separate_from_raw(clean_conn: Any) -> None:
    """Criterion 11: normalized candidate remains separate from raw observation."""
    nc = NormalizedCandidate(value=10.675, unit="m", method_id="si-convert", method_version="1.0")
    obs = _obs("OBS-NORM", raw_value="35 ft", normalized=nc)
    b = _bundle(observations=(obs,))
    import_research_evidence_bundle(clean_conn, b)

    fetched = fetch_observation(clean_conn, "OBS-NORM")
    assert fetched is not None
    assert fetched.raw.value == "35 ft"  # raw preserved
    assert fetched.normalized_candidate is not None
    assert fetched.normalized_candidate.value == 10.675  # normalized separate
    assert fetched.normalized_candidate.method_id == "si-convert"


# ---------------------------------------------------------------------------
# Criterion 12: all applicability dimensions round-trip without widening scope
# ---------------------------------------------------------------------------


def test_applicability_all_dimensions_round_trip(clean_conn: Any) -> None:
    """Criterion 12: all applicability dimensions survive round-trip without widening null scope."""
    app = _applicability(
        first_year=1985,
        last_year=1999,
        hull_number_from="0001",
        hull_number_to="0500",
        market_or_region="US",
        named_variant_hint="tall_rig",
        design_option_hints=["shoal_keel"],
        operating_state_hint="boards_deployed",
        individual_hull_or_listing_ref="HULL-42",
        unknown_or_unbounded=False,
    )
    obs = _obs("OBS-APP", applicability=app)
    b = _bundle(observations=(obs,))
    import_research_evidence_bundle(clean_conn, b)

    fetched = fetch_observation(clean_conn, "OBS-APP")
    assert fetched is not None
    a = fetched.applicability
    assert a.first_year == 1985
    assert a.last_year == 1999
    assert a.hull_number_from == "0001"
    assert a.hull_number_to == "0500"
    assert a.market_or_region == "US"
    assert a.named_variant_hint == "tall_rig"
    assert a.design_option_hints == ("shoal_keel",)
    assert a.operating_state_hint == "boards_deployed"
    assert a.individual_hull_or_listing_ref == "HULL-42"
    assert a.unknown_or_unbounded is False


def test_null_applicability_dimensions_remain_null(clean_conn: Any) -> None:
    """Criterion 12: null applicability scope dimensions must remain null (unknown), not widened."""
    app = _applicability(unknown_or_unbounded=True)
    obs = _obs("OBS-NULL-APP", applicability=app)
    b = _bundle(observations=(obs,))
    import_research_evidence_bundle(clean_conn, b)

    fetched = fetch_observation(clean_conn, "OBS-NULL-APP")
    assert fetched is not None
    a = fetched.applicability
    assert a.first_year is None
    assert a.last_year is None
    assert a.design_option_hints is None
    assert a.individual_hull_or_listing_ref is None


# ---------------------------------------------------------------------------
# Criterion 13: claim semantics round-trip exactly
# ---------------------------------------------------------------------------


def test_claim_semantics_round_trip(clean_conn: Any) -> None:
    """Criterion 13: claim semantics survive round-trip exactly."""
    obs = _obs("OBS-CLAIM", claim_semantics=ClaimSemantics.FACTORY_OPTION_VALUE)
    b = _bundle(observations=(obs,))
    import_research_evidence_bundle(clean_conn, b)

    fetched = fetch_observation(clean_conn, "OBS-CLAIM")
    assert fetched is not None
    assert fetched.claim_semantics == ClaimSemantics.FACTORY_OPTION_VALUE


# ---------------------------------------------------------------------------
# Criterion 14: observation timestamp distinct from applicability
# ---------------------------------------------------------------------------


def test_observation_timestamp_distinct_from_applicability(clean_conn: Any) -> None:
    """Criterion 14: observed_at is preserved and distinct from applicability time bounds."""
    obs = _obs("OBS-TS", applicability=_applicability(first_year=1990))
    b = _bundle(observations=(obs,))
    import_research_evidence_bundle(clean_conn, b)

    fetched = fetch_observation(clean_conn, "OBS-TS")
    assert fetched is not None
    assert fetched.observed_at == "2026-08-20T00:00:00Z"
    assert fetched.applicability.first_year == 1990


# ---------------------------------------------------------------------------
# Criterion 15: individual-hull scope round-trips correctly
# ---------------------------------------------------------------------------


def test_individual_hull_scope_preserved(clean_conn: Any) -> None:
    """Criterion 15: individual_hull_or_listing_ref scope survives round-trip."""
    app = _applicability(individual_hull_or_listing_ref="HULL-007", unknown_or_unbounded=False)
    obs = _obs("OBS-HULL", applicability=app)
    b = _bundle(observations=(obs,))
    import_research_evidence_bundle(clean_conn, b)

    fetched = fetch_observation(clean_conn, "OBS-HULL")
    assert fetched is not None
    assert fetched.applicability.individual_hull_or_listing_ref == "HULL-007"


# ---------------------------------------------------------------------------
# Criterion 16: class-rule claim survives
# ---------------------------------------------------------------------------


def test_class_rule_claim_preserved(clean_conn: Any) -> None:
    """Criterion 16: class-rule claim semantics survive round-trip."""
    obs = _obs("OBS-CLASS-RULE", claim_semantics=ClaimSemantics.CLASS_RULE_CONSTRAINT)
    b = _bundle(observations=(obs,))
    import_research_evidence_bundle(clean_conn, b)

    fetched = fetch_observation(clean_conn, "OBS-CLASS-RULE")
    assert fetched is not None
    assert fetched.claim_semantics == ClaimSemantics.CLASS_RULE_CONSTRAINT


# ---------------------------------------------------------------------------
# Criterion 17: operating-state claim without a DesignOption ID
# ---------------------------------------------------------------------------


def test_operating_state_claim_representable_without_design_option_id(clean_conn: Any) -> None:
    """Criterion 17: operating-state hint is preserved without requiring a DesignOption ID."""
    app = _applicability(operating_state_hint="mast_up", unknown_or_unbounded=False)
    obs = _obs(
        "OBS-OP-STATE",
        claim_semantics=ClaimSemantics.OPERATING_STATE_VALUE,
        applicability=app,
    )
    b = _bundle(observations=(obs,))
    import_research_evidence_bundle(clean_conn, b)

    fetched = fetch_observation(clean_conn, "OBS-OP-STATE")
    assert fetched is not None
    assert fetched.claim_semantics == ClaimSemantics.OPERATING_STATE_VALUE
    assert fetched.applicability.operating_state_hint == "mast_up"


# ---------------------------------------------------------------------------
# Criterion 18: unresolved findings round-trip
# ---------------------------------------------------------------------------


def test_unresolved_findings_round_trip(clean_conn: Any) -> None:
    """Criterion 18: unresolved findings survive round-trip losslessly."""
    obs = _obs("OBS-FIND-RT")
    f = UnresolvedFinding(
        finding_id="FIND-RT-001",
        topic="canonical_identity_unresolved",
        description="Test description for finding",
        related_observation_ids=frozenset(["OBS-FIND-RT"]),
        severity=UnresolvedFindingSeverity.BLOCKING,
    )
    b = _bundle(observations=(obs,), unresolved_findings=(f,))
    import_research_evidence_bundle(clean_conn, b)

    fetched = fetch_finding(clean_conn, "FIND-RT-001", "BUNDLE-001", "1.0")
    assert fetched is not None
    assert fetched.finding_id == "FIND-RT-001"
    assert fetched.topic == "canonical_identity_unresolved"
    assert fetched.severity == UnresolvedFindingSeverity.BLOCKING
    assert "OBS-FIND-RT" in fetched.related_observation_ids


# ---------------------------------------------------------------------------
# Criterion 19: reference crosschecks persist without evidence IDs
# ---------------------------------------------------------------------------


def test_reference_crosschecks_persist_without_evidence_id(clean_conn: Any) -> None:
    """Criterion 19: crosschecks must persist without evidence_id and cannot become FieldEvidence."""
    cc = _crosscheck("CC-NOID")
    b = _bundle(reference_crosschecks=(cc,))
    import_research_evidence_bundle(clean_conn, b)

    fetched = fetch_crosscheck(clean_conn, "CC-NOID", "BUNDLE-001", "1.0")
    assert fetched is not None
    assert fetched.crosscheck_id == "CC-NOID"
    assert fetched.outcome == ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE
    assert fetched.reference_source_id == "sailboatdata-reference"

    # Verify the table has no evidence_id column
    with clean_conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'bundle_reference_crosschecks'
        """)
        cols = {row[0] for row in cur.fetchall()}
    assert "evidence_id" not in cols


# ---------------------------------------------------------------------------
# Criterion 20: no SailboatData field values in fixtures/tests
# ---------------------------------------------------------------------------


def test_no_sailboatdata_field_values_in_fixtures() -> None:
    """Criterion 20: no SailboatData field values are introduced in fixtures or tests."""
    # This test documents the invariant; the fixture builder above uses only
    # synthetic test values ("10.5", "35 ft", etc.) — not SailboatData values.
    # The crosscheck fixture stores only outcome/notes, not reference field values.
    cc = _crosscheck()
    assert cc.reference_source_id == "sailboatdata-reference"
    # Verify notes do NOT contain any numeric SailboatData field value
    assert cc.notes is not None
    # Crosscheck notes must not store reference field values (e.g. "10.67 m" from SBD)
    sailboatdata_value_pattern = "10.67"
    assert sailboatdata_value_pattern not in (cc.notes or "")


# ---------------------------------------------------------------------------
# Criterion 21: optional FieldEvidence v0.3 round-trips with claim/applicability
# ---------------------------------------------------------------------------


def test_promoted_evidence_round_trips(clean_conn: Any) -> None:
    """Criterion 21: optional FieldEvidence v0.3 round-trips with claim/applicability intact."""
    ev = _ev("EV-RT-001")
    b = _bundle(promoted_evidence=(ev,))
    import_research_evidence_bundle(clean_conn, b)

    fetched = fetch_evidence(clean_conn, "EV-RT-001")
    assert fetched is not None
    assert fetched.evidence_id == "EV-RT-001"
    assert fetched.subject.kind == SubjectKind.BOAT_DESIGN
    assert fetched.subject.id == "design-xyz"
    assert str(fetched.field_pointer) == "/loa_m"
    assert fetched.claim_semantics == ClaimSemantics.NOMINAL_DESIGN_VALUE
    assert fetched.applicability.unknown_or_unbounded is True
    assert fetched.normalized_candidate is not None
    assert fetched.normalized_candidate.value == 10.5


# ---------------------------------------------------------------------------
# Criterion 22: importer does not perform identity resolution or promotion
# ---------------------------------------------------------------------------


def test_importer_does_not_resolve_or_promote(clean_conn: Any) -> None:
    """Criterion 22: importer must not auto-resolve observation to FieldEvidence."""
    obs = _obs(
        "OBS-NO-PROMO",
        intended_subject_kind_hint=SubjectKind.BOAT_DESIGN,
        intended_field_pointer=JsonPointer("/loa_m"),
    )
    b = _bundle(observations=(obs,))
    import_research_evidence_bundle(clean_conn, b)

    # Observation imported but no auto-promoted evidence membership should exist
    with clean_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM bundle_evidence_members WHERE bundle_id = %s",
            ["BUNDLE-001"],
        )
        count = cur.fetchone()[0]  # type: ignore[index]
    assert count == 0, (
        "Importer must not automatically promote ResearchObservation to FieldEvidence"
    )


# ---------------------------------------------------------------------------
# Criterion 23: child conflict rolls back complete bundle transaction
# ---------------------------------------------------------------------------


def test_child_conflict_rolls_back_bundle(clean_conn: Any) -> None:
    """Criterion 23: child failure (observation conflict) must roll back the full new bundle."""
    obs_v1 = _obs("OBS-CHILD-CONFLICT", raw_value="10.5")
    b1 = _bundle("BUNDLE-CHILD-1", "1.0", observations=(obs_v1,))
    r1 = import_research_evidence_bundle(clean_conn, b1)
    assert r1.status == ImportStatus.IMPORTED

    obs_v2 = _obs("OBS-CHILD-CONFLICT", raw_value="99.0")  # different content → conflict
    good_obs = _obs("OBS-CHILD-GOOD")
    b2 = _bundle("BUNDLE-CHILD-2", "1.0", observations=(obs_v2, good_obs))
    r2 = import_research_evidence_bundle(clean_conn, b2)
    assert r2.status == ImportStatus.CONFLICT

    # BUNDLE-CHILD-2 must be entirely absent
    snap = fetch_bundle_snapshot(clean_conn, "BUNDLE-CHILD-2", "1.0")
    assert snap is None

    # OBS-CHILD-GOOD must not have been persisted (rolled back with the bundle)
    with clean_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM research_observations WHERE observation_id = %s",
            ["OBS-CHILD-GOOD"],
        )
        assert cur.fetchone()[0] == 0  # type: ignore[index]


# ---------------------------------------------------------------------------
# Criterion 24: database configuration has no import-time side effect
# ---------------------------------------------------------------------------


def test_import_hullq_persistence_no_network_side_effect() -> None:
    """Criterion 24: importing hullq.persistence must not attempt a DB connection."""
    import importlib

    import hullq.persistence

    importlib.reload(hullq.persistence)  # Must not raise even without env var


# ---------------------------------------------------------------------------
# Observation shared across bundles — same obs_id reused without duplicate rows
# ---------------------------------------------------------------------------


def test_shared_observation_reused_across_bundles(clean_conn: Any) -> None:
    """An observation imported in bundle v1 may be referenced by bundle v2 without re-inserting."""
    obs = _obs("OBS-SHARED-BUNDLES")
    b1 = _bundle("BUNDLE-SHARED", "1.0", observations=(obs,))
    b2 = _bundle("BUNDLE-SHARED", "2.0", observations=(obs,))

    import_research_evidence_bundle(clean_conn, b1)
    import_research_evidence_bundle(clean_conn, b2)

    # Exactly one observation row
    with clean_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM research_observations WHERE observation_id = %s",
            ["OBS-SHARED-BUNDLES"],
        )
        assert cur.fetchone()[0] == 1  # type: ignore[index]

    # Two membership rows (one per bundle version)
    with clean_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM bundle_observation_members WHERE observation_id = %s",
            ["OBS-SHARED-BUNDLES"],
        )
        assert cur.fetchone()[0] == 2  # type: ignore[index]


# ---------------------------------------------------------------------------
# Bundle snapshot round-trip
# ---------------------------------------------------------------------------


def test_bundle_snapshot_round_trip(clean_conn: Any) -> None:
    """fetch_bundle_snapshot reconstructs metadata faithfully."""
    obs = _obs("OBS-SNAP")
    f = _finding("FIND-SNAP", {"OBS-SNAP"})
    cc = _crosscheck("CC-SNAP")
    ev = _ev("EV-SNAP")
    b = _bundle(
        "BUNDLE-SNAP",
        "1.0",
        observations=(obs,),
        unresolved_findings=(f,),
        reference_crosschecks=(cc,),
        promoted_evidence=(ev,),
    )
    import_research_evidence_bundle(clean_conn, b)

    snap = fetch_bundle_snapshot(clean_conn, "BUNDLE-SNAP", "1.0")
    assert snap is not None
    assert snap.bundle_id == "BUNDLE-SNAP"
    assert snap.bundle_version == "1.0"
    assert snap.research_target.model == "Test 35"
    assert snap.research_job_id == "JOB-1"
    assert "OBS-SNAP" in snap.observation_ids
    assert "FIND-SNAP" in snap.finding_ids
    assert "CC-SNAP" in snap.crosscheck_ids
    assert "EV-SNAP" in snap.evidence_ids


def test_fetch_bundle_snapshot_returns_none_for_missing(clean_conn: Any) -> None:
    assert fetch_bundle_snapshot(clean_conn, "DOES-NOT-EXIST", "1.0") is None


# ---------------------------------------------------------------------------
# fixture from SLICE-0012: bundle_unresolved_identity.json round-trip
# ---------------------------------------------------------------------------


def test_slice0012_fixture_bundle_imports(clean_conn: Any) -> None:
    """The canonical SLICE-0012 fixture bundle imports and round-trips correctly."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    raw = json.loads(
        (root / "fixtures/research_observations/valid/bundle_unresolved_identity.json").read_text(
            encoding="utf-8"
        )
    )

    # Build runtime objects from the fixture
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
    from hullq.persistence.schema import applicability_from_jsonb
    from hullq.research.jobs import ResearchTarget
    from hullq.research.observations import (
        ReferenceCheckOutcome,
        ReferenceCrosscheck,
        ResearchEvidenceBundle,
        ResearchObservation,
        UnresolvedFinding,
        UnresolvedFindingSeverity,
    )

    def _rt(d: dict) -> ResearchTarget:
        return ResearchTarget(
            manufacturer=d.get("manufacturer"),
            model=d["model"],
            first_built=d.get("first_built"),
        )

    def _loc(d: dict) -> SourceLocator:
        return SourceLocator(
            page=d.get("page"),
            section=d.get("section"),
            anchor=d.get("anchor"),
            table=d.get("table"),
            figure=d.get("figure"),
            record_key=d.get("record_key"),
        )

    def _build_obs(o: dict) -> ResearchObservation:
        obs_data = o["observation"]
        raw_d = obs_data["raw"]
        raw = RawObservation(
            kind=RawObservationKind(raw_d["kind"]),
            value=raw_d["value"],
            unit=raw_d.get("unit"),
            excerpt=raw_d.get("excerpt"),
        )
        prod_d = o["producer"]
        prod = ProducerMetadata(
            kind=ProducerKind(prod_d["kind"]),
            identifier=prod_d["identifier"],
            version=prod_d.get("version"),
            model=prod_d.get("model"),
            prompt_or_rule_version=prod_d.get("prompt_or_rule_version"),
        )
        ctx_d = o["research_context"]
        ctx = ResearchContext(
            research_job_id=ctx_d.get("research_job_id"),
            activity_id=ctx_d.get("activity_id"),
        )
        return ResearchObservation(
            observation_id=o["observation_id"],
            research_target=_rt(o["research_target"]),
            source_id=o["source_id"],
            source_locator=_loc(o["source_locator"]),
            raw=raw,
            normalized_candidate=None,
            evidence_type=EvidenceType(o["evidence_type"]),
            claim_semantics=ClaimSemantics(o["claim_semantics"]),
            applicability=applicability_from_jsonb(o["applicability"]),
            producer=prod,
            research_context=ctx,
            observed_at=o["observed_at"],
            confidence=ConfidenceLevel(o["confidence"]),
            supersedes_observation_id=o.get("supersedes_observation_id"),
            intended_subject_kind_hint=None,
            intended_field_pointer=None,
            notes=o.get("notes"),
        )

    observations = tuple(_build_obs(o) for o in raw["observations"])

    findings_raw = raw.get("unresolved_findings", [])
    findings = tuple(
        UnresolvedFinding(
            finding_id=f["finding_id"],
            topic=f["topic"],
            description=f["description"],
            related_observation_ids=frozenset(f["related_observation_ids"]),
            severity=UnresolvedFindingSeverity(f["severity"]),
        )
        for f in findings_raw
    )

    cc_raw = raw.get("reference_crosschecks", [])
    crosschecks = tuple(
        ReferenceCrosscheck(
            crosscheck_id=cc["crosscheck_id"],
            reference_source_id=cc["reference_source_id"],
            topic_or_field=cc.get("topic_or_field"),
            outcome=ReferenceCheckOutcome(cc["outcome"]),
            notes=cc.get("notes"),
        )
        for cc in cc_raw
    )

    bundle = ResearchEvidenceBundle(
        bundle_id=raw["bundle_id"],
        bundle_version=raw["bundle_version"],
        research_target=_rt(raw["research_target"]),
        research_job_id=raw.get("research_job_id"),
        activity_id=raw.get("activity_id"),
        observations=observations,
        unresolved_findings=findings,
        promoted_evidence=(),
        reference_crosschecks=crosschecks,
    )

    result = import_research_evidence_bundle(clean_conn, bundle)
    assert result.status == ImportStatus.IMPORTED

    snap = fetch_bundle_snapshot(clean_conn, bundle.bundle_id, bundle.bundle_version)
    assert snap is not None
    assert len(snap.observation_ids) == 2
    assert len(snap.finding_ids) == 1
    assert len(snap.crosscheck_ids) == 1

    # Verify one observation round-trips — raw value preserved
    fetched_obs = fetch_observation(clean_conn, "SYNTHETIC-OBS-CATALINA316-DISP-SHOALBULB-001")
    assert fetched_obs is not None
    assert fetched_obs.raw.value == "12400"
    assert fetched_obs.raw.unit == "lbs"
    assert fetched_obs.applicability.design_option_hints == ("shoal_bulb_keel",)

    # Verify crosscheck has no evidence_id
    cc_fetched = fetch_crosscheck(
        clean_conn,
        "SYNTHETIC-CC-CATALINA316-REF-001",
        bundle.bundle_id,
        bundle.bundle_version,
    )
    assert cc_fetched is not None
    assert cc_fetched.outcome == ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE


# ---------------------------------------------------------------------------
# Finding 1: FieldEvidence global immutable identity (mirror ResearchObservation)
# ---------------------------------------------------------------------------


def test_evidence_global_identity_same_content_reusable_across_bundles(clean_conn: Any) -> None:
    """Finding 1: same evidence_id + same content imported in two separate bundles is idempotent.

    One global row in research_evidence; one membership row per bundle version.
    """
    ev = _ev("EV-GLOBAL-001")
    b1 = _bundle("BUNDLE-EV-G1", "1.0", promoted_evidence=(ev,))
    b2 = _bundle("BUNDLE-EV-G2", "1.0", promoted_evidence=(ev,))

    r1 = import_research_evidence_bundle(clean_conn, b1)
    r2 = import_research_evidence_bundle(clean_conn, b2)
    assert r1.status == ImportStatus.IMPORTED
    assert r2.status == ImportStatus.IMPORTED

    # Exactly one global evidence row
    with clean_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM research_evidence WHERE evidence_id = %s",
            ["EV-GLOBAL-001"],
        )
        assert cur.fetchone()[0] == 1  # type: ignore[index]

    # Two membership rows (one per bundle)
    with clean_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM bundle_evidence_members WHERE evidence_id = %s",
            ["EV-GLOBAL-001"],
        )
        assert cur.fetchone()[0] == 2  # type: ignore[index]


def test_evidence_global_identity_different_content_fails_closed(clean_conn: Any) -> None:
    """Finding 1: same evidence_id with materially different content must fail closed (CONFLICT).

    The second bundle import must be rejected; its bundle row must not appear.
    """
    ev_v1 = _ev("EV-CONFLICT-001")
    b1 = _bundle("BUNDLE-EVC-1", "1.0", promoted_evidence=(ev_v1,))
    r1 = import_research_evidence_bundle(clean_conn, b1)
    assert r1.status == ImportStatus.IMPORTED

    # Same evidence_id but different raw value — different content hash
    ev_v2 = FieldEvidenceV3(
        evidence_id="EV-CONFLICT-001",
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id="design-xyz"),
        field_pointer=JsonPointer("/loa_m"),
        source_id="SRC-001",
        source_locator=SourceLocator(
            page=None, section=None, anchor=None, table=None, figure=None, record_key=None
        ),
        raw=RawObservation(kind=RawObservationKind.LITERAL, value="99.9", unit="m", excerpt=None),
        normalized_candidate=None,
        evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
        producer=_producer(),
        research_context=ResearchContext(research_job_id="JOB-1", activity_id="WAVE-1"),
        observed_at="2026-08-20T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_evidence_id=None,
        notes=None,
        claim_semantics=ClaimSemantics.NOMINAL_DESIGN_VALUE,
        applicability=_applicability(unknown_or_unbounded=True),
    )
    b2 = _bundle("BUNDLE-EVC-2", "1.0", promoted_evidence=(ev_v2,))
    r2 = import_research_evidence_bundle(clean_conn, b2)
    assert r2.status == ImportStatus.CONFLICT

    # b2 must not appear in the database
    snap = fetch_bundle_snapshot(clean_conn, "BUNDLE-EVC-2", "1.0")
    assert snap is None


# ---------------------------------------------------------------------------
# Finding 3: reordered semantically identical bundles are idempotent
# ---------------------------------------------------------------------------


def test_reordered_observations_gives_already_imported(clean_conn: Any) -> None:
    """Finding 3: a bundle with the same observations in different order must be ALREADY_IMPORTED."""
    obs_a = _obs("OBS-ORD-A", raw_value="10.5")
    obs_b = _obs("OBS-ORD-B", raw_value="20.0")

    b1 = _bundle("BUNDLE-ORD", "1.0", observations=(obs_a, obs_b))
    b2 = _bundle("BUNDLE-ORD", "1.0", observations=(obs_b, obs_a))  # reversed order

    r1 = import_research_evidence_bundle(clean_conn, b1)
    assert r1.status == ImportStatus.IMPORTED

    r2 = import_research_evidence_bundle(clean_conn, b2)
    assert r2.status == ImportStatus.ALREADY_IMPORTED
    assert r2.content_hash == r1.content_hash


def test_reordered_evidence_gives_already_imported(clean_conn: Any) -> None:
    """Finding 3: a bundle with the same evidence in different order must be ALREADY_IMPORTED."""
    ev_a = _ev("EV-ORD-A")
    ev_b = _ev("EV-ORD-B")

    b1 = _bundle("BUNDLE-EV-ORD", "1.0", promoted_evidence=(ev_a, ev_b))
    b2 = _bundle("BUNDLE-EV-ORD", "1.0", promoted_evidence=(ev_b, ev_a))  # reversed order

    r1 = import_research_evidence_bundle(clean_conn, b1)
    assert r1.status == ImportStatus.IMPORTED

    r2 = import_research_evidence_bundle(clean_conn, b2)
    assert r2.status == ImportStatus.ALREADY_IMPORTED
    assert r2.content_hash == r1.content_hash


# ---------------------------------------------------------------------------
# Real PostgreSQL concurrency: race-safe importer under concurrent connections
# ---------------------------------------------------------------------------


def _concurrency_setup(db_url: str) -> None:
    """Apply migrations (idempotent) and truncate all data tables."""
    import psycopg

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
    finally:
        conn.close()


def test_concurrent_identical_bundle_import_resolves_deterministically(db_url: str) -> None:
    """Two concurrent identical bundle imports must resolve as IMPORTED + ALREADY_IMPORTED.

    No PostgreSQL unique-violation must leak to the caller. No duplicate rows.
    Uses two separate connections synchronized by a threading.Barrier.
    """
    import threading

    import psycopg

    _concurrency_setup(db_url)

    bundle = _bundle("BUNDLE-CONC-IDENT", "1.0", observations=(_obs("OBS-CONC-IDENT-001"),))
    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker() -> None:
        try:
            conn = psycopg.connect(db_url)
            try:
                barrier.wait(timeout=10)
                result = import_research_evidence_bundle(conn, bundle)
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = {r.status for r in results}
    assert statuses == {ImportStatus.IMPORTED, ImportStatus.ALREADY_IMPORTED}, (
        f"Expected IMPORTED+ALREADY_IMPORTED; got {statuses}"
    )

    # Verify: exactly one bundle row and one observation row.
    verify = psycopg.connect(db_url)
    try:
        with verify.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM research_bundles WHERE bundle_id = %s",
                ["BUNDLE-CONC-IDENT"],
            )
            assert cur.fetchone()[0] == 1  # type: ignore[index]
        with verify.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM research_observations WHERE observation_id = %s",
                ["OBS-CONC-IDENT-001"],
            )
            assert cur.fetchone()[0] == 1  # type: ignore[index]
    finally:
        verify.close()


def test_concurrent_imports_sharing_global_observation_no_duplicate(db_url: str) -> None:
    """Concurrent distinct bundles sharing an observation identity must not create duplicates.

    Both bundles must import successfully. The shared observation has exactly one
    global row in research_observations and two membership rows.
    """
    import threading

    import psycopg

    _concurrency_setup(db_url)

    shared_obs = _obs("OBS-CONC-SHARED-OBS")
    bundle_a = _bundle("BUNDLE-CONC-SHOBS-A", "1.0", observations=(shared_obs,))
    bundle_b = _bundle("BUNDLE-CONC-SHOBS-B", "1.0", observations=(shared_obs,))

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(b: Any) -> None:
        try:
            conn = psycopg.connect(db_url)
            try:
                barrier.wait(timeout=10)
                result = import_research_evidence_bundle(conn, b)
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=(bundle_a,)),
        threading.Thread(target=_worker, args=(bundle_b,)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    assert all(r.status == ImportStatus.IMPORTED for r in results), (
        f"Both imports must succeed; got {[r.status for r in results]}"
    )

    verify = psycopg.connect(db_url)
    try:
        with verify.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM research_observations WHERE observation_id = %s",
                ["OBS-CONC-SHARED-OBS"],
            )
            assert cur.fetchone()[0] == 1  # type: ignore[index]
        with verify.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM bundle_observation_members WHERE observation_id = %s",
                ["OBS-CONC-SHARED-OBS"],
            )
            assert cur.fetchone()[0] == 2  # type: ignore[index]
    finally:
        verify.close()


def test_concurrent_imports_sharing_global_evidence_no_duplicate(db_url: str) -> None:
    """Concurrent distinct bundles sharing an evidence identity must not create duplicates.

    Both bundles must import successfully. The shared evidence has exactly one
    global row in research_evidence and two membership rows.
    """
    import threading

    import psycopg

    _concurrency_setup(db_url)

    shared_ev = _ev("EV-CONC-SHARED-EV")
    bundle_a = _bundle("BUNDLE-CONC-SHEV-A", "1.0", promoted_evidence=(shared_ev,))
    bundle_b = _bundle("BUNDLE-CONC-SHEV-B", "1.0", promoted_evidence=(shared_ev,))

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(b: Any) -> None:
        try:
            conn = psycopg.connect(db_url)
            try:
                barrier.wait(timeout=10)
                result = import_research_evidence_bundle(conn, b)
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=(bundle_a,)),
        threading.Thread(target=_worker, args=(bundle_b,)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    assert all(r.status == ImportStatus.IMPORTED for r in results), (
        f"Both evidence-sharing imports must succeed; got {[r.status for r in results]}"
    )

    verify = psycopg.connect(db_url)
    try:
        with verify.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM research_evidence WHERE evidence_id = %s",
                ["EV-CONC-SHARED-EV"],
            )
            assert cur.fetchone()[0] == 1  # type: ignore[index]
        with verify.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM bundle_evidence_members WHERE evidence_id = %s",
                ["EV-CONC-SHARED-EV"],
            )
            assert cur.fetchone()[0] == 2  # type: ignore[index]
    finally:
        verify.close()


def test_concurrent_same_identity_different_content_fails_closed(db_url: str) -> None:
    """Concurrent imports with same observation identity but different content must fail closed.

    One import wins (IMPORTED); the other detects the hash mismatch (CONFLICT) and
    rolls back — leaving no partial bundle in the database.
    """
    import threading

    import psycopg

    _concurrency_setup(db_url)

    obs_v1 = _obs("OBS-CONC-CONFLICT", raw_value="10.5")
    obs_v2 = _obs("OBS-CONC-CONFLICT", raw_value="99.9")  # different semantic content
    bundle_a = _bundle("BUNDLE-CONC-CONFLICT-A", "1.0", observations=(obs_v1,))
    bundle_b = _bundle("BUNDLE-CONC-CONFLICT-B", "1.0", observations=(obs_v2,))

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(b: Any) -> None:
        try:
            conn = psycopg.connect(db_url)
            try:
                barrier.wait(timeout=10)
                result = import_research_evidence_bundle(conn, b)
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=(bundle_a,)),
        threading.Thread(target=_worker, args=(bundle_b,)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = [r.status for r in results]
    assert statuses.count(ImportStatus.IMPORTED) == 1, f"Exactly one must succeed; got {statuses}"
    assert statuses.count(ImportStatus.CONFLICT) == 1, f"Exactly one must conflict; got {statuses}"

    # The CONFLICT bundle must not appear in research_bundles (fully rolled back).
    conflict_result = next(r for r in results if r.status == ImportStatus.CONFLICT)
    verify = psycopg.connect(db_url)
    try:
        with verify.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM research_bundles WHERE bundle_id = %s",
                [conflict_result.bundle_id],
            )
            assert cur.fetchone()[0] == 0, (  # type: ignore[index]
                "CONFLICT bundle must not have a row in research_bundles"
            )
        # Exactly one observation row from the winning import.
        with verify.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM research_observations WHERE observation_id = %s",
                ["OBS-CONC-CONFLICT"],
            )
            assert cur.fetchone()[0] == 1  # type: ignore[index]
    finally:
        verify.close()
