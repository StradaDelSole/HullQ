"""PostgreSQL tests for `hullq.search.hull_design_bridge` — SLICE-0086.

Covers the identical-v0.5/v0.6-pointer `hull_configuration` mapping, the
`hull_count` cross-field consistency check (agreement, conflict, and
missing-count non-blocking), the `other`/`unknown` fail-closed rule, and
`compatible_boat_design_ids_for_hull_configuration` -- mirroring
`tests/persistence/test_rudder_design_bridge.py`'s structure.
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
from hullq.search.hull_design_bridge import (
    HULL_CONFIGURATION_PROJECTION_FIELD,
    SEARCH_HULL_CONFIGURATION_VALUES,
    build_boat_design_hull_configuration_set,
    compatible_boat_design_ids_for_hull_configuration,
    lookup_hull_configuration_canonical_value,
)
from hullq.search.types import ValueQualification

from ._field_resolution_support import (
    admit_canonical_boat_design,
    admit_resolved_categorical_field,
    admit_resolved_draft_max,
)

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
    schema_name = f"hullq_s0086hdb_{uuid.uuid4().hex[:16]}"
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
    design_id: str, *, hull_configuration: str | None, hull_count: int | None = None
) -> dict[str, object]:
    return {
        "id": design_id,
        "baseline": {
            "configuration": {
                "hull_configuration": hull_configuration,
                "hull_count": hull_count,
            }
        },
        "named_variants": [],
    }


def _admit(conn: Any, design: dict[str, object]) -> None:
    admit_canonical_boat_design(
        conn,
        design["id"],  # type: ignore[arg-type]
        baseline=design["baseline"],  # type: ignore[arg-type]
        named_variants=design["named_variants"],  # type: ignore[arg-type]
    )


def _admit_hull_configuration(conn: Any, design_id: str, value: str) -> None:
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/configuration/hull_configuration",
        value=value,
        resolution_id=f"FR-{design_id}-HULLCFG",
        fetch_canonical_value=lookup_hull_configuration_canonical_value,
    )


def _admit_hull_count(conn: Any, design_id: str, value: int) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/configuration/hull_count",
        value=Decimal(value),
        resolution_id=f"FR-{design_id}-HULLCOUNT",
        fetch_canonical_value=lookup_hull_configuration_canonical_value,
    )


def _hull_value(conn: Any, design: dict[str, object]) -> tuple[ValueQualification, str | None]:
    config_set = build_boat_design_hull_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_categorical(
        HULL_CONFIGURATION_PROJECTION_FIELD
    )
    return qualified.qualification, qualified.value


# ---------------------------------------------------------------------------
# Public v0.1 vocabulary
# ---------------------------------------------------------------------------


def test_accepted_search_hull_configuration_values() -> None:
    assert frozenset({"MONOHULL", "CATAMARAN", "TRIMARAN"}) == SEARCH_HULL_CONFIGURATION_VALUES


# ---------------------------------------------------------------------------
# Mapping, no hull_count supplied (must not be fabricated as mandatory)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_hull_configuration", "expected_value"),
    [
        ("monohull", "MONOHULL"),
        ("catamaran", "CATAMARAN"),
        ("trimaran", "TRIMARAN"),
    ],
)
def test_mapping_without_hull_count_still_confirms(
    conn: Any, raw_hull_configuration: str, expected_value: str
) -> None:
    design_id = f"BD-HDB-NOCOUNT-{raw_hull_configuration}"
    design = _design(design_id, hull_configuration=raw_hull_configuration)
    _admit(conn, design)
    _admit_hull_configuration(conn, design_id, raw_hull_configuration)
    qualification, value = _hull_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == expected_value


@pytest.mark.parametrize("unsupported", ["other", "unknown"])
def test_unsupported_hull_configuration_fails_closed(conn: Any, unsupported: str) -> None:
    design_id = f"BD-HDB-UNSUP-{unsupported}"
    design = _design(design_id, hull_configuration=unsupported)
    _admit(conn, design)
    _admit_hull_configuration(conn, design_id, unsupported)
    qualification, value = _hull_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


# ---------------------------------------------------------------------------
# hull_count cross-field consistency check
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_hull_configuration", "expected_value", "agreeing_count"),
    [
        ("monohull", "MONOHULL", 1),
        ("catamaran", "CATAMARAN", 2),
        ("trimaran", "TRIMARAN", 3),
    ],
)
def test_hull_count_agreement_still_confirms(
    conn: Any, raw_hull_configuration: str, expected_value: str, agreeing_count: int
) -> None:
    design_id = f"BD-HDB-AGREE-{raw_hull_configuration}"
    design = _design(
        design_id, hull_configuration=raw_hull_configuration, hull_count=agreeing_count
    )
    _admit(conn, design)
    _admit_hull_configuration(conn, design_id, raw_hull_configuration)
    _admit_hull_count(conn, design_id, agreeing_count)
    qualification, value = _hull_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == expected_value


def test_hull_count_conflict_fails_closed(conn: Any) -> None:
    """`hull_configuration=catamaran` with a confirmed `hull_count` other
    than 2 is an internally inconsistent payload -- never silently resolved
    by picking one side."""
    design_id = "BD-HDB-CONFLICT"
    design = _design(design_id, hull_configuration="catamaran", hull_count=3)
    _admit(conn, design)
    _admit_hull_configuration(conn, design_id, "catamaran")
    _admit_hull_count(conn, design_id, 3)
    qualification, value = _hull_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


def test_hull_count_missing_never_blocks_qualified_hull_configuration(conn: Any) -> None:
    """A design confirmed only on `hull_configuration`, with `hull_count`
    itself unqualified, must not be penalized -- `hull_count` is never
    fabricated as mandatory evidence."""
    design_id = "BD-HDB-NOCOUNT-UNQUALIFIED"
    design = _design(design_id, hull_configuration="trimaran", hull_count=3)
    _admit(conn, design)
    _admit_hull_configuration(conn, design_id, "trimaran")
    # Deliberately no _admit_hull_count call: hull_count stays unresolved.
    qualification, value = _hull_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == "TRIMARAN"


# ---------------------------------------------------------------------------
# compatible_boat_design_ids_for_hull_configuration
# ---------------------------------------------------------------------------


def test_compatible_boat_design_ids_for_hull_configuration_admits_matching_design(
    conn: Any,
) -> None:
    design_id = "BD-HDB-COMPAT-1"
    design = _design(design_id, hull_configuration="catamaran", hull_count=2)
    _admit(conn, design)
    _admit_hull_configuration(conn, design_id, "catamaran")
    _admit_hull_count(conn, design_id, 2)
    compatible = compatible_boat_design_ids_for_hull_configuration(conn, "CATAMARAN", [design])
    assert compatible == frozenset({design_id})


def test_compatible_boat_design_ids_for_hull_configuration_rejects_non_v0_1_value(
    conn: Any,
) -> None:
    design = _design("BD-HDB-COMPAT-2", hull_configuration="catamaran")
    with pytest.raises(ValueError):
        compatible_boat_design_ids_for_hull_configuration(conn, "OTHER", [design])
