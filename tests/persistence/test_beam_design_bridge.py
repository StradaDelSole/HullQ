"""PostgreSQL tests for `hullq.search.beam_design_bridge` — SLICE-0087.

Mirrors `tests/persistence/test_loa_design_bridge.py`'s structure exactly for
the eighth criterion adapter: FieldResolution qualification of the design-side
`dimensions.beam_m` field, NamedVariant own-override/inheritance, and
`compatible_boat_design_ids_for_beam`'s min/max/range eligibility.
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
from hullq.search.beam_design_bridge import (
    BEAM_FIELD_POINTER,
    BEAM_OVERRIDE_FIELD_POINTER,
    build_boat_design_beam_configuration_set,
    compatible_boat_design_ids_for_beam,
    lookup_beam_canonical_value,
)
from hullq.search.types import ValueQualification

from ._field_resolution_support import admit_canonical_boat_design, admit_resolved_draft_max

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
    schema_name = f"hullq_s0087beam_{uuid.uuid4().hex[:16]}"
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
    baseline_beam_m: str | None,
    named_variants: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "id": design_id,
        "baseline": {"dimensions": {"beam_m": baseline_beam_m}},
        "named_variants": named_variants or [],
    }


def _admit(conn: Any, design: dict[str, object]) -> None:
    admit_canonical_boat_design(
        conn,
        design["id"],  # type: ignore[arg-type]
        baseline=design["baseline"],  # type: ignore[arg-type]
        named_variants=design["named_variants"],  # type: ignore[arg-type]
    )


def _admit_resolved_beam(
    conn: Any,
    *,
    subject_kind: SubjectKind,
    subject_id: str,
    field_pointer: str,
    value: Decimal,
    resolution_id: str,
) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=subject_kind,
        subject_id=subject_id,
        field_pointer=field_pointer,
        value=value,
        resolution_id=resolution_id,
        fetch_canonical_value=lookup_beam_canonical_value,
    )


# ---------------------------------------------------------------------------
# FieldResolution qualification
# ---------------------------------------------------------------------------


def test_no_active_resolution_is_missing(conn: Any) -> None:
    design = _design("BD-BEAM-1", baseline_beam_m="3.80")
    config_set = build_boat_design_beam_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_numeric("beam_m")
    assert qualified.qualification is ValueQualification.MISSING


def test_resolved_matching_snapshot_is_confirmed(conn: Any) -> None:
    _admit(conn, _design("BD-BEAM-2", baseline_beam_m="3.80"))
    _admit_resolved_beam(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-BEAM-2",
        field_pointer=BEAM_FIELD_POINTER,
        value=Decimal("3.80"),
        resolution_id="FR-BEAM-2",
    )
    design = _design("BD-BEAM-2", baseline_beam_m="3.80")
    config_set = build_boat_design_beam_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_numeric("beam_m")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == Decimal("3.80")


# ---------------------------------------------------------------------------
# NamedVariant own override / inheritance
# ---------------------------------------------------------------------------


def test_named_variant_own_override_qualification(conn: Any) -> None:
    design = _design(
        "BD-BEAM-VAR-1",
        baseline_beam_m="3.80",
        named_variants=[{"id": "VAR-BEAM-1", "overrides": {"dimensions": {"beam_m": "4.00"}}}],
    )
    admit_canonical_boat_design(
        conn, design["id"], baseline=design["baseline"], named_variants=design["named_variants"]
    )
    _admit_resolved_beam(
        conn,
        subject_kind=SubjectKind.NAMED_VARIANT,
        subject_id="VAR-BEAM-1",
        field_pointer=BEAM_OVERRIDE_FIELD_POINTER,
        value=Decimal("4.00"),
        resolution_id="FR-VAR-BEAM-1",
    )
    config_set = build_boat_design_beam_configuration_set(conn, design)
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == "BD-BEAM-VAR-1::VAR-BEAM-1"
    )
    qualified = variant_config.projection.get_numeric("beam_m")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == Decimal("4.00")


def test_named_variant_without_own_override_inherits_baseline(conn: Any) -> None:
    design = _design(
        "BD-BEAM-INHERIT-1",
        baseline_beam_m="3.80",
        named_variants=[{"id": "VAR-INHERIT-1", "overrides": {"dimensions": {}}}],
    )
    admit_canonical_boat_design(
        conn, design["id"], baseline=design["baseline"], named_variants=design["named_variants"]
    )
    _admit_resolved_beam(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-BEAM-INHERIT-1",
        field_pointer=BEAM_FIELD_POINTER,
        value=Decimal("3.80"),
        resolution_id="FR-BEAM-INHERIT-1",
    )
    config_set = build_boat_design_beam_configuration_set(conn, design)
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == "BD-BEAM-INHERIT-1::VAR-INHERIT-1"
    )
    qualified = variant_config.projection.get_numeric("beam_m")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == Decimal("3.80")


# ---------------------------------------------------------------------------
# compatible_boat_design_ids_for_beam: min / max / range eligibility
# ---------------------------------------------------------------------------


def test_compatible_boat_design_ids_for_beam_minimum_only(conn: Any) -> None:
    design = _design("BD-BEAM-MIN-1", baseline_beam_m="4.00")
    _admit(conn, design)
    _admit_resolved_beam(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-BEAM-MIN-1",
        field_pointer=BEAM_FIELD_POINTER,
        value=Decimal("4.00"),
        resolution_id="FR-BEAM-MIN-1",
    )
    assert compatible_boat_design_ids_for_beam(
        conn, beam_min=Decimal("3.5"), beam_max=None, boat_designs=[design]
    ) == frozenset({"BD-BEAM-MIN-1"})
    assert (
        compatible_boat_design_ids_for_beam(
            conn, beam_min=Decimal("4.5"), beam_max=None, boat_designs=[design]
        )
        == frozenset()
    )


def test_compatible_boat_design_ids_for_beam_maximum_only(conn: Any) -> None:
    design = _design("BD-BEAM-MAX-1", baseline_beam_m="4.00")
    _admit(conn, design)
    _admit_resolved_beam(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-BEAM-MAX-1",
        field_pointer=BEAM_FIELD_POINTER,
        value=Decimal("4.00"),
        resolution_id="FR-BEAM-MAX-1",
    )
    assert compatible_boat_design_ids_for_beam(
        conn, beam_min=None, beam_max=Decimal("4.5"), boat_designs=[design]
    ) == frozenset({"BD-BEAM-MAX-1"})
    assert (
        compatible_boat_design_ids_for_beam(
            conn, beam_min=None, beam_max=Decimal("3.5"), boat_designs=[design]
        )
        == frozenset()
    )


def test_compatible_boat_design_ids_for_beam_inclusive_range_including_boundaries(
    conn: Any,
) -> None:
    design = _design("BD-BEAM-RANGE-1", baseline_beam_m="4.00")
    _admit(conn, design)
    _admit_resolved_beam(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-BEAM-RANGE-1",
        field_pointer=BEAM_FIELD_POINTER,
        value=Decimal("4.00"),
        resolution_id="FR-BEAM-RANGE-1",
    )
    # Exact equality at both boundaries is inclusive (SEARCH_QUERY_SEMANTICS §6).
    assert compatible_boat_design_ids_for_beam(
        conn, beam_min=Decimal("4.00"), beam_max=Decimal("4.00"), boat_designs=[design]
    ) == frozenset({"BD-BEAM-RANGE-1"})
    assert compatible_boat_design_ids_for_beam(
        conn, beam_min=Decimal("3.2"), beam_max=Decimal("4.4"), boat_designs=[design]
    ) == frozenset({"BD-BEAM-RANGE-1"})
    assert (
        compatible_boat_design_ids_for_beam(
            conn, beam_min=Decimal("4.1"), beam_max=Decimal("4.4"), boat_designs=[design]
        )
        == frozenset()
    )


def test_compatible_boat_design_ids_for_beam_requires_at_least_one_bound(conn: Any) -> None:
    design = _design("BD-BEAM-NONE-1", baseline_beam_m="4.00")
    with pytest.raises(ValueError):
        compatible_boat_design_ids_for_beam(
            conn, beam_min=None, beam_max=None, boat_designs=[design]
        )
