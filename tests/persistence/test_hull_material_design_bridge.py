"""PostgreSQL tests for `hullq.search.hull_material_design_bridge` — SLICE-0087.

Mirrors `tests/persistence/test_keel_design_bridge.py`'s coverage for the
ninth criterion adapter: FieldResolution qualification of the design-side
`construction.hull_material` field, NamedVariant own-override/inheritance,
and the normative v0.1 taxonomy mapping -- including the "fails closed" rule
for a BoatDesign `hull_material` with no authorized v0.1 mapping
(`wood_composite`/`carbon`/`other`/`unknown`).
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.domain.provenance import SubjectKind
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.search.hull_material_design_bridge import (
    HULL_MATERIAL_FIELD_POINTER,
    HULL_MATERIAL_OVERRIDE_FIELD_POINTER,
    SEARCH_HULL_MATERIAL_VALUES,
    build_boat_design_hull_material_configuration_set,
    compatible_boat_design_ids_for_hull_material,
    lookup_hull_material_canonical_value,
)
from hullq.search.types import ValueQualification

from ._field_resolution_support import admit_canonical_boat_design, admit_resolved_categorical_field

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
    schema_name = f"hullq_s0087hmdb_{uuid.uuid4().hex[:16]}"
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
    baseline_hull_material: str | None,
    named_variants: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "id": design_id,
        "baseline": {"construction": {"hull_material": baseline_hull_material}},
        "named_variants": named_variants or [],
    }


def _admit(conn: Any, design: dict[str, object]) -> None:
    admit_canonical_boat_design(
        conn,
        design["id"],  # type: ignore[arg-type]
        baseline=design["baseline"],  # type: ignore[arg-type]
        named_variants=design["named_variants"],  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Public v0.1 vocabulary
# ---------------------------------------------------------------------------


def test_accepted_search_hull_material_values_are_exactly_v0_1() -> None:
    assert frozenset({"GRP_FIBERGLASS", "STEEL", "ALUMINUM", "WOOD"}) == SEARCH_HULL_MATERIAL_VALUES


# ---------------------------------------------------------------------------
# FieldResolution qualification of the design-side baseline
# ---------------------------------------------------------------------------


def test_no_active_resolution_is_missing(conn: Any) -> None:
    design = _design("BD-HMDB-1", baseline_hull_material="grp_fiberglass")
    config_set = build_boat_design_hull_material_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_categorical("hull_material")
    assert qualified.qualification is ValueQualification.MISSING


def test_resolved_matching_snapshot_maps_to_search_vocabulary(conn: Any) -> None:
    _admit(conn, _design("BD-HMDB-2", baseline_hull_material="grp_fiberglass"))
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-HMDB-2",
        field_pointer=HULL_MATERIAL_FIELD_POINTER,
        value="grp_fiberglass",
        resolution_id="FR-HMDB-2",
        fetch_canonical_value=lookup_hull_material_canonical_value,
    )
    design = _design("BD-HMDB-2", baseline_hull_material="grp_fiberglass")
    config_set = build_boat_design_hull_material_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_categorical("hull_material")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == "GRP_FIBERGLASS"


@pytest.mark.parametrize(
    ("boat_design_hull_material", "expected_search_value"),
    [
        ("grp_fiberglass", "GRP_FIBERGLASS"),
        ("steel", "STEEL"),
        ("aluminium", "ALUMINUM"),
        ("wood", "WOOD"),
    ],
)
def test_every_v0_1_mapping_is_applied(
    conn: Any, boat_design_hull_material: str, expected_search_value: str
) -> None:
    design_id = f"BD-HMDB-MAP-{boat_design_hull_material}"
    _admit(conn, _design(design_id, baseline_hull_material=boat_design_hull_material))
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=HULL_MATERIAL_FIELD_POINTER,
        value=boat_design_hull_material,
        resolution_id=f"FR-{design_id}",
        fetch_canonical_value=lookup_hull_material_canonical_value,
    )
    design = _design(design_id, baseline_hull_material=boat_design_hull_material)
    config_set = build_boat_design_hull_material_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_categorical("hull_material")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == expected_search_value


@pytest.mark.parametrize(
    "unsupported_hull_material",
    ["wood_composite", "carbon", "other", "unknown"],
)
def test_unsupported_boat_design_hull_material_fails_closed_to_missing(
    conn: Any, unsupported_hull_material: str
) -> None:
    """An unsupported BoatDesign hull_material mapping fails closed -- even
    though the design's own hull_material is confirmed via a real resolved
    FieldResolution, it must never be coerced into any Search vocabulary
    value. In particular `wood_composite` must never collapse to `WOOD` and
    `carbon` must never collapse to `CARBON_COMPOSITE`."""
    design_id = f"BD-HMDB-UNSUP-{unsupported_hull_material}"
    _admit(conn, _design(design_id, baseline_hull_material=unsupported_hull_material))
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=HULL_MATERIAL_FIELD_POINTER,
        value=unsupported_hull_material,
        resolution_id=f"FR-{design_id}",
        fetch_canonical_value=lookup_hull_material_canonical_value,
    )
    design = _design(design_id, baseline_hull_material=unsupported_hull_material)
    config_set = build_boat_design_hull_material_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_categorical("hull_material")
    assert qualified.qualification is ValueQualification.MISSING
    assert qualified.value is None


# ---------------------------------------------------------------------------
# NamedVariant own override / inheritance
# ---------------------------------------------------------------------------


def test_named_variant_own_override_qualification(conn: Any) -> None:
    design = _design(
        "BD-HMDB-VAR-1",
        baseline_hull_material="grp_fiberglass",
        named_variants=[
            {"id": "VAR-HMDB-1", "overrides": {"construction": {"hull_material": "aluminium"}}}
        ],
    )
    admit_canonical_boat_design(
        conn, design["id"], baseline=design["baseline"], named_variants=design["named_variants"]
    )
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.NAMED_VARIANT,
        subject_id="VAR-HMDB-1",
        field_pointer=HULL_MATERIAL_OVERRIDE_FIELD_POINTER,
        value="aluminium",
        resolution_id="FR-VAR-HMDB-1",
        fetch_canonical_value=lookup_hull_material_canonical_value,
    )
    config_set = build_boat_design_hull_material_configuration_set(conn, design)
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == "BD-HMDB-VAR-1::VAR-HMDB-1"
    )
    qualified = variant_config.projection.get_categorical("hull_material")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == "ALUMINUM"


def test_named_variant_without_own_override_inherits_baseline(conn: Any) -> None:
    design = _design(
        "BD-HMDB-INHERIT-1",
        baseline_hull_material="steel",
        named_variants=[{"id": "VAR-INHERIT-1", "overrides": {"construction": {}}}],
    )
    admit_canonical_boat_design(
        conn, design["id"], baseline=design["baseline"], named_variants=design["named_variants"]
    )
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-HMDB-INHERIT-1",
        field_pointer=HULL_MATERIAL_FIELD_POINTER,
        value="steel",
        resolution_id="FR-HMDB-INHERIT-1",
        fetch_canonical_value=lookup_hull_material_canonical_value,
    )
    config_set = build_boat_design_hull_material_configuration_set(conn, design)
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == "BD-HMDB-INHERIT-1::VAR-INHERIT-1"
    )
    qualified = variant_config.projection.get_categorical("hull_material")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == "STEEL"


# ---------------------------------------------------------------------------
# compatible_boat_design_ids_for_hull_material: design-level eligibility
# ---------------------------------------------------------------------------


def test_compatible_boat_design_ids_for_hull_material_admits_matching_design(conn: Any) -> None:
    design = _design("BD-HMDB-COMPAT-1", baseline_hull_material="wood")
    _admit(conn, design)
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-HMDB-COMPAT-1",
        field_pointer=HULL_MATERIAL_FIELD_POINTER,
        value="wood",
        resolution_id="FR-HMDB-COMPAT-1",
        fetch_canonical_value=lookup_hull_material_canonical_value,
    )
    compatible = compatible_boat_design_ids_for_hull_material(conn, "WOOD", [design])
    assert compatible == frozenset({"BD-HMDB-COMPAT-1"})


def test_compatible_boat_design_ids_for_hull_material_excludes_non_matching_design(
    conn: Any,
) -> None:
    design = _design("BD-HMDB-COMPAT-2", baseline_hull_material="steel")
    _admit(conn, design)
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-HMDB-COMPAT-2",
        field_pointer=HULL_MATERIAL_FIELD_POINTER,
        value="steel",
        resolution_id="FR-HMDB-COMPAT-2",
        fetch_canonical_value=lookup_hull_material_canonical_value,
    )
    compatible = compatible_boat_design_ids_for_hull_material(conn, "WOOD", [design])
    assert compatible == frozenset()


def test_compatible_boat_design_ids_for_hull_material_excludes_unsupported_taxonomy_design(
    conn: Any,
) -> None:
    design = _design("BD-HMDB-COMPAT-UNSUP", baseline_hull_material="wood_composite")
    _admit(conn, design)
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-HMDB-COMPAT-UNSUP",
        field_pointer=HULL_MATERIAL_FIELD_POINTER,
        value="wood_composite",
        resolution_id="FR-HMDB-COMPAT-UNSUP",
        fetch_canonical_value=lookup_hull_material_canonical_value,
    )
    for value in SEARCH_HULL_MATERIAL_VALUES:
        compatible = compatible_boat_design_ids_for_hull_material(conn, value, [design])
        assert compatible == frozenset()


def test_compatible_boat_design_ids_for_hull_material_rejects_non_v0_1_value(conn: Any) -> None:
    design = _design("BD-HMDB-TYPE-1", baseline_hull_material="grp_fiberglass")
    with pytest.raises(ValueError):
        compatible_boat_design_ids_for_hull_material(conn, "FERROCEMENT", [design])
