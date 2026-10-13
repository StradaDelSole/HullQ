"""PostgreSQL tests for `hullq.search.rudder_design_bridge` — SLICE-0085.

Covers the generation-aware conservative v0.5/v0.6 `rudder_configuration`
derivation: every v0.5 `rudder_type` mapping (including the `twin`/
`rudder_count` conflict guard), every v0.6 single-signal mapping, the
`rudder_support=free` non-proof of `SPADE`, ambiguous-overlap fail-closed
behavior, and NamedVariant override/inheritance -- mirroring
`tests/persistence/test_keel_design_bridge.py`'s structure.
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
from hullq.search.rudder_design_bridge import (
    RUDDER_CONFIGURATION_PROJECTION_FIELD,
    SEARCH_RUDDER_CONFIGURATION_VALUES,
    build_boat_design_rudder_configuration_set,
    compatible_boat_design_ids_for_rudder,
    lookup_rudder_canonical_value,
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
    schema_name = f"hullq_s0085rdb_{uuid.uuid4().hex[:16]}"
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


def _v05_design(
    design_id: str, *, rudder_type: str | None, rudder_count: int | None = None
) -> dict[str, object]:
    return {
        "id": design_id,
        "baseline": {"configuration": {"rudder_type": rudder_type, "rudder_count": rudder_count}},
        "named_variants": [],
    }


def _v06_design(
    design_id: str,
    *,
    rudder_support: str | None = None,
    rudder_position: str | None = None,
    rudder_count: int | None = None,
) -> dict[str, object]:
    return {
        "id": design_id,
        "baseline": {
            "appendages": {
                "rudder_support": rudder_support,
                "rudder_position": rudder_position,
                "rudder_count": rudder_count,
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


def _admit_v05_type(conn: Any, design_id: str, value: str) -> None:
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/configuration/rudder_type",
        value=value,
        resolution_id=f"FR-{design_id}-TYPE",
        fetch_canonical_value=lookup_rudder_canonical_value,
    )


def _admit_v05_count(conn: Any, design_id: str, value: int) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/configuration/rudder_count",
        value=Decimal(value),
        resolution_id=f"FR-{design_id}-COUNT",
        fetch_canonical_value=lookup_rudder_canonical_value,
    )


def _admit_v06_support(conn: Any, design_id: str, value: str) -> None:
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/appendages/rudder_support",
        value=value,
        resolution_id=f"FR-{design_id}-SUPPORT",
        fetch_canonical_value=lookup_rudder_canonical_value,
    )


def _admit_v06_position(conn: Any, design_id: str, value: str) -> None:
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/appendages/rudder_position",
        value=value,
        resolution_id=f"FR-{design_id}-POSITION",
        fetch_canonical_value=lookup_rudder_canonical_value,
    )


def _admit_v06_count(conn: Any, design_id: str, value: int) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/appendages/rudder_count",
        value=Decimal(value),
        resolution_id=f"FR-{design_id}-COUNT",
        fetch_canonical_value=lookup_rudder_canonical_value,
    )


def _rudder_value(conn: Any, design: dict[str, object]) -> tuple[ValueQualification, str | None]:
    config_set = build_boat_design_rudder_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_categorical(
        RUDDER_CONFIGURATION_PROJECTION_FIELD
    )
    return qualified.qualification, qualified.value


# ---------------------------------------------------------------------------
# Public v0.1 vocabulary
# ---------------------------------------------------------------------------


def test_accepted_search_rudder_configuration_values() -> None:
    assert (
        frozenset({"SKEG_HUNG", "TRANSOM_HUNG", "SPADE", "TWIN"})
        == SEARCH_RUDDER_CONFIGURATION_VALUES
    )


# ---------------------------------------------------------------------------
# v0.5 mapping table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("v05_rudder_type", "expected_value"),
    [
        ("skeg_hung", "SKEG_HUNG"),
        ("partial_skeg", "SKEG_HUNG"),
        ("transom_hung", "TRANSOM_HUNG"),
        ("spade", "SPADE"),
        ("twin", "TWIN"),
    ],
)
def test_v05_unconditional_and_twin_mapping(
    conn: Any, v05_rudder_type: str, expected_value: str
) -> None:
    design_id = f"BD-RDB-V05-{v05_rudder_type}"
    design = _v05_design(design_id, rudder_type=v05_rudder_type)
    _admit(conn, design)
    _admit_v05_type(conn, design_id, v05_rudder_type)
    qualification, value = _rudder_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == expected_value


@pytest.mark.parametrize("unsupported", ["keel_hung", "other", "unknown"])
def test_v05_unsupported_rudder_type_fails_closed(conn: Any, unsupported: str) -> None:
    design_id = f"BD-RDB-V05-UNSUP-{unsupported}"
    design = _v05_design(design_id, rudder_type=unsupported)
    _admit(conn, design)
    _admit_v05_type(conn, design_id, unsupported)
    qualification, value = _rudder_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


def test_v05_twin_with_confirmed_count_of_two_still_confirms_twin(conn: Any) -> None:
    design_id = "BD-RDB-V05-TWIN-AGREE"
    design = _v05_design(design_id, rudder_type="twin", rudder_count=2)
    _admit(conn, design)
    _admit_v05_type(conn, design_id, "twin")
    _admit_v05_count(conn, design_id, 2)
    qualification, value = _rudder_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == "TWIN"


def test_v05_twin_with_conflicting_count_fails_closed(conn: Any) -> None:
    """`rudder_type=twin` with a confirmed count other than 2 is an
    internally inconsistent v0.5 payload -- never silently resolved."""
    design_id = "BD-RDB-V05-TWIN-CONFLICT"
    design = _v05_design(design_id, rudder_type="twin", rudder_count=1)
    _admit(conn, design)
    _admit_v05_type(conn, design_id, "twin")
    _admit_v05_count(conn, design_id, 1)
    qualification, value = _rudder_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


# ---------------------------------------------------------------------------
# v0.6 mapping
# ---------------------------------------------------------------------------


def test_v06_skeg_support_maps_to_skeg_hung(conn: Any) -> None:
    design_id = "BD-RDB-V06-SKEG"
    design = _v06_design(design_id, rudder_support="skeg")
    _admit(conn, design)
    _admit_v06_support(conn, design_id, "skeg")
    qualification, value = _rudder_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == "SKEG_HUNG"


def test_v06_transom_position_and_support_maps_to_transom_hung(conn: Any) -> None:
    design_id = "BD-RDB-V06-TRANSOM"
    design = _v06_design(design_id, rudder_support="transom", rudder_position="transom")
    _admit(conn, design)
    _admit_v06_support(conn, design_id, "transom")
    _admit_v06_position(conn, design_id, "transom")
    qualification, value = _rudder_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == "TRANSOM_HUNG"


def test_v06_transom_position_without_transom_support_is_missing(conn: Any) -> None:
    """Position and support are independent (contract): a transom-positioned
    skeg-supported rudder must not be coerced into TRANSOM_HUNG."""
    design_id = "BD-RDB-V06-TRANSOM-POS-ONLY"
    design = _v06_design(design_id, rudder_support="skeg", rudder_position="transom")
    _admit(conn, design)
    _admit_v06_support(conn, design_id, "skeg")
    _admit_v06_position(conn, design_id, "transom")
    # This is actually SKEG_HUNG (support=skeg alone suffices) -- but
    # TRANSOM_HUNG must NOT also be produced ambiguously.
    qualification, value = _rudder_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == "SKEG_HUNG"


def test_v06_count_two_maps_to_twin(conn: Any) -> None:
    design_id = "BD-RDB-V06-TWIN"
    design = _v06_design(design_id, rudder_count=2)
    _admit(conn, design)
    _admit_v06_count(conn, design_id, 2)
    qualification, value = _rudder_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == "TWIN"


def test_v06_free_support_never_proves_spade(conn: Any) -> None:
    """Slice normative rudder semantics: `rudder_support=free` does NOT
    prove SPADE -- v0.6 never derives SPADE at all."""
    design_id = "BD-RDB-V06-FREE"
    design = _v06_design(design_id, rudder_support="free")
    _admit(conn, design)
    _admit_v06_support(conn, design_id, "free")
    qualification, value = _rudder_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


def test_v06_ambiguous_overlap_fails_closed(conn: Any) -> None:
    """Skeg support AND a confirmed count of 2 simultaneously both support a
    candidate category -- genuinely ambiguous, never guessed."""
    design_id = "BD-RDB-V06-AMBIGUOUS"
    design = _v06_design(design_id, rudder_support="skeg", rudder_count=2)
    _admit(conn, design)
    _admit_v06_support(conn, design_id, "skeg")
    _admit_v06_count(conn, design_id, 2)
    qualification, value = _rudder_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


# ---------------------------------------------------------------------------
# compatible_boat_design_ids_for_rudder
# ---------------------------------------------------------------------------


def test_compatible_boat_design_ids_for_rudder_admits_matching_design(conn: Any) -> None:
    design_id = "BD-RDB-COMPAT-1"
    design = _v06_design(design_id, rudder_support="skeg")
    _admit(conn, design)
    _admit_v06_support(conn, design_id, "skeg")
    compatible = compatible_boat_design_ids_for_rudder(conn, "SKEG_HUNG", [design])
    assert compatible == frozenset({design_id})


def test_compatible_boat_design_ids_for_rudder_rejects_non_v0_1_value(conn: Any) -> None:
    design = _v06_design("BD-RDB-COMPAT-2", rudder_support="skeg")
    with pytest.raises(ValueError):
        compatible_boat_design_ids_for_rudder(conn, "OTHER", [design])
