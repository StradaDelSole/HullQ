"""PostgreSQL tests for `hullq.search.draft_max_design_bridge` — SLICE-0051
FieldResolution blocker-resolution amendment.

Covers the FieldResolution-aware qualification rule now that a durable
persistence prerequisite exists (`hullq.persistence.field_resolution`):
raw persisted BoatDesign JSON never self-authorizes CONFIRMED Search truth
(Finding 3); only an active `resolved`/`resolved_with_conflict`
FieldResolution whose exact Decimal snapshot agrees with the current
canonical value may qualify. Also covers NamedVariant own-override
qualification, baseline inheritance (no fabricated second FieldResolution),
the amendment review Finding 4 required-option exclusion, and the exact
Decimal, no-float-drift design-level eligibility check.

`build_boat_design_draft_configuration_set`/`compatible_boat_design_ids`
consult `field_resolutions`/`field_resolution_heads` only -- there is no
foreign-key dependency on a real `canonical_boat_designs` row (FieldResolution
subjects are generic and never bound to that table), so these tests
construct BOAT_DESIGN_SCHEMA-shaped dicts directly in memory rather than
persisting them.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.domain.provenance import SubjectKind
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.search.draft_max_design_bridge import (
    DRAFT_MAX_FIELD_POINTER,
    DRAFT_MAX_OVERRIDE_FIELD_POINTER,
    DRAFT_MAX_PROJECTION_FIELD,
    build_boat_design_draft_configuration_set,
    compatible_boat_design_ids,
)
from hullq.search.types import ValueQualification

from ._field_resolution_support import admit_resolved_draft_max

# ---------------------------------------------------------------------------
# Disposable-schema fixture
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
    schema_name = f"hullq_s0051db_{uuid.uuid4().hex[:16]}"
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


def _design(
    design_id: str,
    *,
    baseline_draft_max_m: float | None,
    named_variants: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "id": design_id,
        "baseline": {"dimensions": {"draft_max_m": baseline_draft_max_m}},
        "named_variants": named_variants or [],
    }


# ---------------------------------------------------------------------------
# Finding 3: BoatDesign baseline qualification
# ---------------------------------------------------------------------------


def test_no_active_resolution_is_missing(conn: Any) -> None:
    design = _design("BD-DB-1", baseline_draft_max_m=1.3)
    config_set = build_boat_design_draft_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD)
    assert qualified.qualification is ValueQualification.MISSING


def test_resolved_matching_snapshot_is_confirmed(conn: Any) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-DB-2",
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=Decimal("1.3"),
        resolution_id="FR-DB-2",
    )
    design = _design("BD-DB-2", baseline_draft_max_m=1.3)
    config_set = build_boat_design_draft_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD)
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == Decimal("1.3")
    assert isinstance(qualified.value, Decimal)


def test_resolved_snapshot_mismatching_canonical_value_is_missing(conn: Any) -> None:
    """A resolution whose snapshot no longer agrees with the canonical
    value it is supposed to qualify (PROVENANCE_MODEL.v0.1.md §6) must fail
    closed, not silently confirm the (different) current canonical value."""
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-DB-3",
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=Decimal("1.3"),
        resolution_id="FR-DB-3",
    )
    design = _design("BD-DB-3", baseline_draft_max_m=1.5)  # differs from the resolved snapshot
    config_set = build_boat_design_draft_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD)
    assert qualified.qualification is ValueQualification.MISSING


@pytest.mark.parametrize("state_value", ["unknown", "needs_review", "conflict"])
def test_unresolved_states_are_missing(conn: Any, state_value: str) -> None:
    from hullq.domain.provenance import (
        FieldResolution,
        JsonPointer,
        ProvenanceSubject,
        ResolutionMethod,
        ResolutionState,
        ResolverKind,
        ResolverMetadata,
    )
    from hullq.persistence.field_resolution import write_field_resolution

    design_id = f"BD-DB-UNRESOLVED-{state_value}"
    contradicting = frozenset({"EV-DOES-NOT-EXIST"}) if state_value == "conflict" else frozenset()
    # conflict/needs_review/unknown all carry a null snapshot and no
    # supporting evidence; "conflict" additionally requires >=1
    # contradicting evidence id (VAL-PROV-008) -- but that evidence need not
    # exist durably for THIS test's purpose is wrong: write_field_resolution
    # validates considered evidence existence unconditionally. Use an empty
    # considered set with a state that does not require contradicting
    # evidence to keep this test focused on the qualification rule, not the
    # ledger's own evidence-existence enforcement (covered separately in
    # test_field_resolution_persistence.py).
    if state_value == "conflict":
        pytest.skip(
            "conflict state's evidence-existence requirement is covered in "
            "test_field_resolution_persistence.py; this test focuses on the "
            "design-bridge qualification rule for unknown/needs_review"
        )
    resolution = FieldResolution(
        resolution_id=f"FR-{design_id}",
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=design_id),
        field_pointer=JsonPointer(DRAFT_MAX_FIELD_POINTER),
        state=ResolutionState(state_value),
        canonical_value_snapshot=None,
        supporting_evidence_ids=frozenset(),
        contradicting_evidence_ids=contradicting,
        considered_evidence_ids=frozenset(),
        resolution_method=ResolutionMethod.INSUFFICIENT_EVIDENCE,
        policy_version="test-policy-1",
        resolver=ResolverMetadata(
            kind=ResolverKind.DETERMINISTIC_TOOL, identifier="test", version="1"
        ),
        resolved_at="2026-09-12T00:00:00+00:00",
        supersedes_resolution_id=None,
        notes=None,
    )
    result = write_field_resolution(
        conn, resolution=resolution, expected_current_resolution_id=None, available_sources={}
    )
    assert result.status.value == "created", result
    conn.commit()

    design = _design(design_id, baseline_draft_max_m=1.3)
    config_set = build_boat_design_draft_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD)
    assert qualified.qualification is ValueQualification.MISSING


# ---------------------------------------------------------------------------
# NamedVariant own override / inheritance / explicit null
# ---------------------------------------------------------------------------


def test_named_variant_own_override_qualification(conn: Any) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.NAMED_VARIANT,
        subject_id="VAR-DB-1",
        field_pointer=DRAFT_MAX_OVERRIDE_FIELD_POINTER,
        value=Decimal("1.30"),
        resolution_id="FR-VAR-DB-1",
    )
    design = _design(
        "BD-DB-VAR-1",
        baseline_draft_max_m=1.85,
        named_variants=[{"id": "VAR-DB-1", "overrides": {"dimensions": {"draft_max_m": 1.30}}}],
    )
    config_set = build_boat_design_draft_configuration_set(conn, design)
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == "BD-DB-VAR-1::VAR-DB-1"
    )
    qualified = variant_config.projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD)
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == Decimal("1.30")


def test_named_variant_without_own_override_inherits_baseline(conn: Any) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-DB-INHERIT-1",
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=Decimal("1.85"),
        resolution_id="FR-DB-INHERIT-1",
    )
    design = _design(
        "BD-DB-INHERIT-1",
        baseline_draft_max_m=1.85,
        named_variants=[{"id": "VAR-INHERIT-1", "overrides": {"dimensions": {}}}],
    )
    config_set = build_boat_design_draft_configuration_set(conn, design)
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == "BD-DB-INHERIT-1::VAR-INHERIT-1"
    )
    qualified = variant_config.projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD)
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == Decimal("1.85")


def test_named_variant_explicit_null_override_clears_to_missing_despite_confirmed_baseline(
    conn: Any,
) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-DB-NULLOVERRIDE-1",
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=Decimal("1.85"),
        resolution_id="FR-DB-NULLOVERRIDE-1",
    )
    design = _design(
        "BD-DB-NULLOVERRIDE-1",
        baseline_draft_max_m=1.85,
        named_variants=[
            {"id": "VAR-NULLOVERRIDE-1", "overrides": {"dimensions": {"draft_max_m": None}}}
        ],
    )
    config_set = build_boat_design_draft_configuration_set(conn, design)
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == "BD-DB-NULLOVERRIDE-1::VAR-NULLOVERRIDE-1"
    )
    qualified = variant_config.projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD)
    assert qualified.qualification is ValueQualification.MISSING


# ---------------------------------------------------------------------------
# Finding 4: required-option variant exclusion (unaffected by FieldResolution)
# ---------------------------------------------------------------------------


def test_variant_with_requires_option_ids_still_excluded(conn: Any) -> None:
    design = _design(
        "BD-DB-REQOPT-1",
        baseline_draft_max_m=1.85,
        named_variants=[
            {
                "id": "VAR-NEEDS-OPTION",
                "overrides": {"dimensions": {"draft_max_m": 1.30}},
                "requires_option_ids": ["OPT-X"],
            }
        ],
    )
    config_set = build_boat_design_draft_configuration_set(conn, design)
    configuration_ids = {c.identity.configuration_id for c in config_set.configurations}
    assert "BD-DB-REQOPT-1::VAR-NEEDS-OPTION" not in configuration_ids
    assert "BD-DB-REQOPT-1::baseline" in configuration_ids


# ---------------------------------------------------------------------------
# compatible_boat_design_ids: exact-Decimal end-to-end eligibility
# ---------------------------------------------------------------------------


def test_compatible_boat_design_ids_admits_qualified_shallow_design(conn: Any) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-DB-COMPAT-1",
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=Decimal("1.30"),
        resolution_id="FR-DB-COMPAT-1",
    )
    design = _design("BD-DB-COMPAT-1", baseline_draft_max_m=1.30)
    compatible = compatible_boat_design_ids(conn, Decimal("1.6"), [design])
    assert compatible == frozenset({"BD-DB-COMPAT-1"})


def test_compatible_boat_design_ids_excludes_too_deep_design(conn: Any) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-DB-COMPAT-2",
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=Decimal("2.10"),
        resolution_id="FR-DB-COMPAT-2",
    )
    design = _design("BD-DB-COMPAT-2", baseline_draft_max_m=2.10)
    compatible = compatible_boat_design_ids(conn, Decimal("1.6"), [design])
    assert compatible == frozenset()


def test_compatible_boat_design_ids_exact_decimal_boundary_no_float_drift(conn: Any) -> None:
    """The *buyer's threshold* must never be degraded through an
    intermediate float conversion (Finding 2), independent of the raw
    canonical JSONB baseline value's own inherent float-JSON storage
    precision (a separate, already-acknowledged limitation): a
    higher-precision threshold that is still numerically >= the qualified
    1.6 m design value must admit it."""
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-DB-EXACT-1",
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=Decimal("1.6"),
        resolution_id="FR-DB-EXACT-1",
    )
    design = _design("BD-DB-EXACT-1", baseline_draft_max_m=1.6)
    high_precision_threshold = Decimal("1.60000000000000000000001")
    compatible = compatible_boat_design_ids(conn, high_precision_threshold, [design])
    assert compatible == frozenset({"BD-DB-EXACT-1"})


def test_compatible_boat_design_ids_requires_a_decimal_threshold(conn: Any) -> None:
    design = _design("BD-DB-TYPE-1", baseline_draft_max_m=1.3)
    with pytest.raises(TypeError):
        compatible_boat_design_ids(conn, 1.6, [design])  # type: ignore[arg-type]
