"""PostgreSQL tests for `hullq.search.keel_design_bridge` — SLICE-0055.

Mirrors `tests/persistence/test_field_resolution_design_bridge.py`'s coverage
for the new `keel_configuration` criterion #2 adapter: FieldResolution
qualification of the design-side `appendages.keel_type` field, NamedVariant
own-override/inheritance, the amendment-review Finding-4-style required-option
exclusion (reused unchanged from the shared bridge), and the SLICE-0055
normative v0.1 taxonomy mapping -- including the "fails closed" rule for a
BoatDesign `keel_type` with no authorized v0.1 mapping (contract §4,
acceptance criterion #6).
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
from hullq.search.keel_design_bridge import (
    KEEL_TYPE_FIELD_POINTER,
    KEEL_TYPE_OVERRIDE_FIELD_POINTER,
    SEARCH_KEEL_CONFIGURATION_VALUES,
    build_boat_design_keel_configuration_set,
    compatible_boat_design_ids_for_keel,
    lookup_keel_canonical_value,
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
    schema_name = f"hullq_s0055kdb_{uuid.uuid4().hex[:16]}"
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
    baseline_keel_type: str | None,
    named_variants: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "id": design_id,
        "baseline": {"appendages": {"keel_type": baseline_keel_type}},
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


def test_accepted_search_keel_configuration_values_are_exactly_v0_1() -> None:
    assert (
        frozenset({"FIN", "FIN_WITH_BULB", "WING", "CENTERBOARD", "LIFTING_KEEL", "TWIN_KEEL"})
        == SEARCH_KEEL_CONFIGURATION_VALUES
    )


# ---------------------------------------------------------------------------
# FieldResolution qualification of the design-side baseline
# ---------------------------------------------------------------------------


def test_no_active_resolution_is_missing(conn: Any) -> None:
    design = _design("BD-KDB-1", baseline_keel_type="fin")
    config_set = build_boat_design_keel_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_categorical("keel_configuration")
    assert qualified.qualification is ValueQualification.MISSING


def test_resolved_matching_snapshot_maps_to_search_vocabulary(conn: Any) -> None:
    _admit(conn, _design("BD-KDB-2", baseline_keel_type="fin"))
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-KDB-2",
        field_pointer=KEEL_TYPE_FIELD_POINTER,
        value="fin",
        resolution_id="FR-KDB-2",
        fetch_canonical_value=lookup_keel_canonical_value,
    )
    design = _design("BD-KDB-2", baseline_keel_type="fin")
    config_set = build_boat_design_keel_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_categorical("keel_configuration")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == "FIN"


@pytest.mark.parametrize(
    ("boat_design_keel_type", "expected_search_value"),
    [
        ("fin", "FIN"),
        ("wing", "WING"),
        ("bulb", "FIN_WITH_BULB"),
        ("centerboard", "CENTERBOARD"),
        ("lifting", "LIFTING_KEEL"),
        ("twin", "TWIN_KEEL"),
    ],
)
def test_every_v0_1_mapping_is_applied(
    conn: Any, boat_design_keel_type: str, expected_search_value: str
) -> None:
    design_id = f"BD-KDB-MAP-{boat_design_keel_type}"
    _admit(conn, _design(design_id, baseline_keel_type=boat_design_keel_type))
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=KEEL_TYPE_FIELD_POINTER,
        value=boat_design_keel_type,
        resolution_id=f"FR-{design_id}",
        fetch_canonical_value=lookup_keel_canonical_value,
    )
    design = _design(design_id, baseline_keel_type=boat_design_keel_type)
    config_set = build_boat_design_keel_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_categorical("keel_configuration")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == expected_search_value


@pytest.mark.parametrize(
    "unsupported_keel_type",
    [
        "full",
        "modified_full",
        "long_fin",
        "bilge",
        "daggerboard",
        "swing",
        "shoal",
        "other",
        "unknown",
    ],
)
def test_unsupported_boat_design_keel_type_fails_closed_to_missing(
    conn: Any, unsupported_keel_type: str
) -> None:
    """Acceptance criterion #6: an unsupported BoatDesign keel mapping fails
    closed -- even though the design's own keel_type is confirmed via a real
    resolved FieldResolution, it must never be coerced into any Search
    vocabulary value (contract §4: never LONG_KEEL/TWIN_KEEL by inference)."""
    design_id = f"BD-KDB-UNSUP-{unsupported_keel_type}"
    _admit(conn, _design(design_id, baseline_keel_type=unsupported_keel_type))
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=KEEL_TYPE_FIELD_POINTER,
        value=unsupported_keel_type,
        resolution_id=f"FR-{design_id}",
        fetch_canonical_value=lookup_keel_canonical_value,
    )
    design = _design(design_id, baseline_keel_type=unsupported_keel_type)
    config_set = build_boat_design_keel_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_categorical("keel_configuration")
    assert qualified.qualification is ValueQualification.MISSING
    assert qualified.value is None


# ---------------------------------------------------------------------------
# NamedVariant own override / inheritance
# ---------------------------------------------------------------------------


def test_named_variant_own_override_qualification(conn: Any) -> None:
    design = _design(
        "BD-KDB-VAR-1",
        baseline_keel_type="fin",
        named_variants=[{"id": "VAR-KDB-1", "overrides": {"appendages": {"keel_type": "wing"}}}],
    )
    admit_canonical_boat_design(
        conn, design["id"], baseline=design["baseline"], named_variants=design["named_variants"]
    )
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.NAMED_VARIANT,
        subject_id="VAR-KDB-1",
        field_pointer=KEEL_TYPE_OVERRIDE_FIELD_POINTER,
        value="wing",
        resolution_id="FR-VAR-KDB-1",
        fetch_canonical_value=lookup_keel_canonical_value,
    )
    config_set = build_boat_design_keel_configuration_set(conn, design)
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == "BD-KDB-VAR-1::VAR-KDB-1"
    )
    qualified = variant_config.projection.get_categorical("keel_configuration")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == "WING"


def test_named_variant_without_own_override_inherits_baseline(conn: Any) -> None:
    design = _design(
        "BD-KDB-INHERIT-1",
        baseline_keel_type="fin",
        named_variants=[{"id": "VAR-INHERIT-1", "overrides": {"appendages": {}}}],
    )
    admit_canonical_boat_design(
        conn, design["id"], baseline=design["baseline"], named_variants=design["named_variants"]
    )
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-KDB-INHERIT-1",
        field_pointer=KEEL_TYPE_FIELD_POINTER,
        value="fin",
        resolution_id="FR-KDB-INHERIT-1",
        fetch_canonical_value=lookup_keel_canonical_value,
    )
    config_set = build_boat_design_keel_configuration_set(conn, design)
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == "BD-KDB-INHERIT-1::VAR-INHERIT-1"
    )
    qualified = variant_config.projection.get_categorical("keel_configuration")
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == "FIN"


# ---------------------------------------------------------------------------
# Required-option exclusion (shared bridge behavior, reused unchanged)
# ---------------------------------------------------------------------------


def test_variant_with_requires_option_ids_still_excluded(conn: Any) -> None:
    design = _design(
        "BD-KDB-REQOPT-1",
        baseline_keel_type="fin",
        named_variants=[
            {
                "id": "VAR-NEEDS-OPTION",
                "overrides": {"appendages": {"keel_type": "wing"}},
                "requires_option_ids": ["OPT-X"],
            }
        ],
    )
    config_set = build_boat_design_keel_configuration_set(conn, design)
    configuration_ids = {c.identity.configuration_id for c in config_set.configurations}
    assert "BD-KDB-REQOPT-1::VAR-NEEDS-OPTION" not in configuration_ids
    assert "BD-KDB-REQOPT-1::baseline" in configuration_ids


# ---------------------------------------------------------------------------
# compatible_boat_design_ids_for_keel: design-level eligibility
# ---------------------------------------------------------------------------


def test_compatible_boat_design_ids_for_keel_admits_matching_design(conn: Any) -> None:
    design = _design("BD-KDB-COMPAT-1", baseline_keel_type="fin")
    _admit(conn, design)
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-KDB-COMPAT-1",
        field_pointer=KEEL_TYPE_FIELD_POINTER,
        value="fin",
        resolution_id="FR-KDB-COMPAT-1",
        fetch_canonical_value=lookup_keel_canonical_value,
    )
    compatible = compatible_boat_design_ids_for_keel(conn, "FIN", [design])
    assert compatible == frozenset({"BD-KDB-COMPAT-1"})


def test_compatible_boat_design_ids_for_keel_excludes_non_matching_design(conn: Any) -> None:
    design = _design("BD-KDB-COMPAT-2", baseline_keel_type="wing")
    _admit(conn, design)
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-KDB-COMPAT-2",
        field_pointer=KEEL_TYPE_FIELD_POINTER,
        value="wing",
        resolution_id="FR-KDB-COMPAT-2",
        fetch_canonical_value=lookup_keel_canonical_value,
    )
    compatible = compatible_boat_design_ids_for_keel(conn, "FIN", [design])
    assert compatible == frozenset()


def test_compatible_boat_design_ids_for_keel_excludes_unsupported_taxonomy_design(
    conn: Any,
) -> None:
    """Acceptance criterion #6, design-eligibility level: a design whose
    resolved keel_type has no v0.1 mapping is never design-eligible for any
    query value -- it fails closed to UNKNOWN, not a guessed match/non-match."""
    design = _design("BD-KDB-COMPAT-UNSUP", baseline_keel_type="full")
    _admit(conn, design)
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-KDB-COMPAT-UNSUP",
        field_pointer=KEEL_TYPE_FIELD_POINTER,
        value="full",
        resolution_id="FR-KDB-COMPAT-UNSUP",
        fetch_canonical_value=lookup_keel_canonical_value,
    )
    for value in SEARCH_KEEL_CONFIGURATION_VALUES:
        compatible = compatible_boat_design_ids_for_keel(conn, value, [design])
        assert compatible == frozenset()


def test_compatible_boat_design_ids_for_keel_rejects_non_v0_1_value(conn: Any) -> None:
    design = _design("BD-KDB-TYPE-1", baseline_keel_type="fin")
    with pytest.raises(ValueError):
        compatible_boat_design_ids_for_keel(conn, "LONG_KEEL", [design])
