"""PostgreSQL tests for `hullq.search.loa_design_bridge` — SLICE-0085.

Mirrors `tests/persistence/test_keel_design_bridge.py`'s structure for the
third criterion adapter: FieldResolution qualification of the design-side
`dimensions.loa_m` field, NamedVariant own-override/inheritance, and
`compatible_boat_design_ids_for_loa`'s min/max/range eligibility.
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
from hullq.search.loa_design_bridge import (
    LOA_FIELD_POINTER,
    LOA_OVERRIDE_FIELD_POINTER,
    build_boat_design_loa_configuration_set,
    compatible_boat_design_ids_for_loa,
    lookup_loa_canonical_value,
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
    schema_name = f"hullq_s0085loa_{uuid.uuid4().hex[:16]}"
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
    baseline_loa_m: str | None,
    named_variants: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "id": design_id,
        "baseline": {"dimensions": {"loa_m": baseline_loa_m}},
        "named_variants": named_variants or [],
    }


def _admit(conn: Any, design: dict[str, object]) -> None:
    admit_canonical_boat_design(
        conn,
        design["id"],  # type: ignore[arg-type]
        baseline=design["baseline"],  # type: ignore[arg-type]
        named_variants=design["named_variants"],  # type: ignore[arg-type]
    )


def _admit_resolved_loa(
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
        fetch_canonical_value=lookup_loa_canonical_value,
    )


# ---------------------------------------------------------------------------
# FieldResolution qualification
# ---------------------------------------------------------------------------


def test_no_active_resolution_is_missing(conn: Any) -> None:
    design = _design("BD-LOA-1", baseline_loa_m="10.50")
    config_set = build_boat_design_loa_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_numeric("loa_m")
    assert qualified.qualification is ValueQualification.MISSING


def test_resolved_matching_snapshot_is_confirmed(conn: Any) -> None:
    _admit(conn, _design("BD-LOA-2", baseline_loa_m="10.50"))
    _admit_resolved_loa(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-LOA-2",
        field_pointer=LOA_FIELD_POINTER,
        value=Decimal("10.50"),
        resolution_id="FR-LOA-2",
    )
    design = _design("BD-LOA-2", baseline_loa_m="10.50")
    config_set = build_boat_design_loa_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_numeric("loa_m")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == Decimal("10.50")


# ---------------------------------------------------------------------------
# NamedVariant own override / inheritance
# ---------------------------------------------------------------------------


def test_named_variant_own_override_qualification(conn: Any) -> None:
    design = _design(
        "BD-LOA-VAR-1",
        baseline_loa_m="10.50",
        named_variants=[{"id": "VAR-LOA-1", "overrides": {"dimensions": {"loa_m": "11.00"}}}],
    )
    admit_canonical_boat_design(
        conn, design["id"], baseline=design["baseline"], named_variants=design["named_variants"]
    )
    _admit_resolved_loa(
        conn,
        subject_kind=SubjectKind.NAMED_VARIANT,
        subject_id="VAR-LOA-1",
        field_pointer=LOA_OVERRIDE_FIELD_POINTER,
        value=Decimal("11.00"),
        resolution_id="FR-VAR-LOA-1",
    )
    config_set = build_boat_design_loa_configuration_set(conn, design)
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == "BD-LOA-VAR-1::VAR-LOA-1"
    )
    qualified = variant_config.projection.get_numeric("loa_m")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == Decimal("11.00")


def test_named_variant_without_own_override_inherits_baseline(conn: Any) -> None:
    design = _design(
        "BD-LOA-INHERIT-1",
        baseline_loa_m="10.50",
        named_variants=[{"id": "VAR-INHERIT-1", "overrides": {"dimensions": {}}}],
    )
    admit_canonical_boat_design(
        conn, design["id"], baseline=design["baseline"], named_variants=design["named_variants"]
    )
    _admit_resolved_loa(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-LOA-INHERIT-1",
        field_pointer=LOA_FIELD_POINTER,
        value=Decimal("10.50"),
        resolution_id="FR-LOA-INHERIT-1",
    )
    config_set = build_boat_design_loa_configuration_set(conn, design)
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == "BD-LOA-INHERIT-1::VAR-INHERIT-1"
    )
    qualified = variant_config.projection.get_numeric("loa_m")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == Decimal("10.50")


# ---------------------------------------------------------------------------
# compatible_boat_design_ids_for_loa: min / max / range eligibility
# ---------------------------------------------------------------------------


def test_compatible_boat_design_ids_for_loa_minimum_only(conn: Any) -> None:
    design = _design("BD-LOA-MIN-1", baseline_loa_m="12.00")
    _admit(conn, design)
    _admit_resolved_loa(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-LOA-MIN-1",
        field_pointer=LOA_FIELD_POINTER,
        value=Decimal("12.00"),
        resolution_id="FR-LOA-MIN-1",
    )
    assert compatible_boat_design_ids_for_loa(
        conn, loa_min=Decimal("10"), loa_max=None, boat_designs=[design]
    ) == frozenset({"BD-LOA-MIN-1"})
    assert (
        compatible_boat_design_ids_for_loa(
            conn, loa_min=Decimal("13"), loa_max=None, boat_designs=[design]
        )
        == frozenset()
    )


def test_compatible_boat_design_ids_for_loa_maximum_only(conn: Any) -> None:
    design = _design("BD-LOA-MAX-1", baseline_loa_m="12.00")
    _admit(conn, design)
    _admit_resolved_loa(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-LOA-MAX-1",
        field_pointer=LOA_FIELD_POINTER,
        value=Decimal("12.00"),
        resolution_id="FR-LOA-MAX-1",
    )
    assert compatible_boat_design_ids_for_loa(
        conn, loa_min=None, loa_max=Decimal("15"), boat_designs=[design]
    ) == frozenset({"BD-LOA-MAX-1"})
    assert (
        compatible_boat_design_ids_for_loa(
            conn, loa_min=None, loa_max=Decimal("11"), boat_designs=[design]
        )
        == frozenset()
    )


def test_compatible_boat_design_ids_for_loa_inclusive_range_including_boundaries(
    conn: Any,
) -> None:
    design = _design("BD-LOA-RANGE-1", baseline_loa_m="12.00")
    _admit(conn, design)
    _admit_resolved_loa(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-LOA-RANGE-1",
        field_pointer=LOA_FIELD_POINTER,
        value=Decimal("12.00"),
        resolution_id="FR-LOA-RANGE-1",
    )
    # Exact equality at both boundaries is inclusive (SEARCH_QUERY_SEMANTICS §6).
    assert compatible_boat_design_ids_for_loa(
        conn, loa_min=Decimal("12.00"), loa_max=Decimal("12.00"), boat_designs=[design]
    ) == frozenset({"BD-LOA-RANGE-1"})
    assert compatible_boat_design_ids_for_loa(
        conn, loa_min=Decimal("10"), loa_max=Decimal("15"), boat_designs=[design]
    ) == frozenset({"BD-LOA-RANGE-1"})
    assert (
        compatible_boat_design_ids_for_loa(
            conn, loa_min=Decimal("13"), loa_max=Decimal("15"), boat_designs=[design]
        )
        == frozenset()
    )


def test_compatible_boat_design_ids_for_loa_requires_at_least_one_bound(conn: Any) -> None:
    design = _design("BD-LOA-NONE-1", baseline_loa_m="12.00")
    with pytest.raises(ValueError):
        compatible_boat_design_ids_for_loa(conn, loa_min=None, loa_max=None, boat_designs=[design])
