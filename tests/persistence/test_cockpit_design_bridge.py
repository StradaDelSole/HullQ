"""PostgreSQL tests for `hullq.search.cockpit_design_bridge` — SLICE-0086.

Covers the v0.6-only `deck.cockpit_position` mapping (v0.5 has no `deck`
section at all, so a v0.5 design must stay MISSING with no version-
conditional logic), the `cockpit_count == 0` cross-field contradiction
check, the `other`/`unknown` fail-closed rule, and
`compatible_boat_design_ids_for_cockpit_position` -- mirroring
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
from hullq.search.cockpit_design_bridge import (
    COCKPIT_POSITION_PROJECTION_FIELD,
    SEARCH_COCKPIT_POSITION_VALUES,
    build_boat_design_cockpit_position_set,
    compatible_boat_design_ids_for_cockpit_position,
    lookup_cockpit_position_canonical_value,
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
    schema_name = f"hullq_s0086cdb_{uuid.uuid4().hex[:16]}"
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


def _v06_design(
    design_id: str, *, cockpit_position: str | None = None, cockpit_count: int | None = None
) -> dict[str, object]:
    return {
        "id": design_id,
        "baseline": {
            "deck": {"cockpit_position": cockpit_position, "cockpit_count": cockpit_count}
        },
        "named_variants": [],
    }


def _v05_design(design_id: str) -> dict[str, object]:
    """A v0.5 design has no `deck` section at all."""
    return {
        "id": design_id,
        "baseline": {"configuration": {"hull_configuration": "monohull", "hull_count": 1}},
        "named_variants": [],
    }


def _admit(conn: Any, design: dict[str, object]) -> None:
    admit_canonical_boat_design(
        conn,
        design["id"],  # type: ignore[arg-type]
        baseline=design["baseline"],  # type: ignore[arg-type]
        named_variants=design["named_variants"],  # type: ignore[arg-type]
    )


def _admit_cockpit_position(conn: Any, design_id: str, value: str) -> None:
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/deck/cockpit_position",
        value=value,
        resolution_id=f"FR-{design_id}-COCKPITPOS",
        fetch_canonical_value=lookup_cockpit_position_canonical_value,
    )


def _admit_cockpit_count(conn: Any, design_id: str, value: int) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/deck/cockpit_count",
        value=Decimal(value),
        resolution_id=f"FR-{design_id}-COCKPITCOUNT",
        fetch_canonical_value=lookup_cockpit_position_canonical_value,
    )


def _cockpit_value(conn: Any, design: dict[str, object]) -> tuple[ValueQualification, str | None]:
    config_set = build_boat_design_cockpit_position_set(conn, design)
    qualified = config_set.configurations[0].projection.get_categorical(
        COCKPIT_POSITION_PROJECTION_FIELD
    )
    return qualified.qualification, qualified.value


# ---------------------------------------------------------------------------
# Public v0.1 vocabulary
# ---------------------------------------------------------------------------


def test_accepted_search_cockpit_position_values() -> None:
    assert frozenset({"AFT", "CENTER", "FORWARD", "MULTIPLE"}) == SEARCH_COCKPIT_POSITION_VALUES


# ---------------------------------------------------------------------------
# v0.6 mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_cockpit_position", "expected_value"),
    [
        ("aft", "AFT"),
        ("center", "CENTER"),
        ("forward", "FORWARD"),
        ("multiple", "MULTIPLE"),
    ],
)
def test_v06_mapping(conn: Any, raw_cockpit_position: str, expected_value: str) -> None:
    design_id = f"BD-CDB-V06-{raw_cockpit_position}"
    design = _v06_design(design_id, cockpit_position=raw_cockpit_position)
    _admit(conn, design)
    _admit_cockpit_position(conn, design_id, raw_cockpit_position)
    qualification, value = _cockpit_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == expected_value


@pytest.mark.parametrize("unsupported", ["other", "unknown"])
def test_unsupported_cockpit_position_fails_closed(conn: Any, unsupported: str) -> None:
    design_id = f"BD-CDB-UNSUP-{unsupported}"
    design = _v06_design(design_id, cockpit_position=unsupported)
    _admit(conn, design)
    _admit_cockpit_position(conn, design_id, unsupported)
    qualification, value = _cockpit_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


def test_v05_design_with_no_deck_section_is_missing(conn: Any) -> None:
    """v0.5 has no `deck` section at all -- the shared bridge's ordinary
    section/field lookup already yields MISSING with no version-conditional
    logic in this bridge."""
    design_id = "BD-CDB-V05"
    design = _v05_design(design_id)
    _admit(conn, design)
    qualification, value = _cockpit_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


# ---------------------------------------------------------------------------
# cockpit_count cross-field contradiction check
# ---------------------------------------------------------------------------


def test_cockpit_count_zero_with_confirmed_position_fails_closed(conn: Any) -> None:
    """A confirmed non-unknown cockpit position together with a confirmed
    `cockpit_count == 0` is contradictory -- never a confirmed positive
    match, even though BOAT_DESIGN_SCHEMA.v0.6 itself requires
    `cockpit_count=0` to pair with `cockpit_position=unknown` (this bridge
    does not rely solely on schema validation of old persisted payloads)."""
    design_id = "BD-CDB-COUNT-ZERO-CONTRADICTION"
    design = _v06_design(design_id, cockpit_position="aft", cockpit_count=0)
    _admit(conn, design)
    _admit_cockpit_position(conn, design_id, "aft")
    _admit_cockpit_count(conn, design_id, 0)
    qualification, value = _cockpit_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


def test_cockpit_count_nonzero_agreement_still_confirms(conn: Any) -> None:
    design_id = "BD-CDB-COUNT-AGREE"
    design = _v06_design(design_id, cockpit_position="center", cockpit_count=1)
    _admit(conn, design)
    _admit_cockpit_position(conn, design_id, "center")
    _admit_cockpit_count(conn, design_id, 1)
    qualification, value = _cockpit_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == "CENTER"


def test_cockpit_count_missing_never_blocks_qualified_cockpit_position(conn: Any) -> None:
    design_id = "BD-CDB-COUNT-UNQUALIFIED"
    design = _v06_design(design_id, cockpit_position="forward", cockpit_count=1)
    _admit(conn, design)
    _admit_cockpit_position(conn, design_id, "forward")
    # Deliberately no _admit_cockpit_count call: cockpit_count stays unresolved.
    qualification, value = _cockpit_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == "FORWARD"


# ---------------------------------------------------------------------------
# PR #349 review Finding B: MULTIPLE + cockpit_count consistency
# ---------------------------------------------------------------------------


def test_multiple_with_count_one_fails_closed(conn: Any) -> None:
    """MULTIPLE requires corroborated distinct physical cockpits -- a
    confirmed `cockpit_count == 1` directly contradicts that and must never
    be a confirmed positive match (an impossible single-cockpit MULTIPLE
    must not falsely confirm)."""
    design_id = "BD-CDB-MULTIPLE-COUNT-ONE"
    design = _v06_design(design_id, cockpit_position="multiple", cockpit_count=1)
    _admit(conn, design)
    _admit_cockpit_position(conn, design_id, "multiple")
    _admit_cockpit_count(conn, design_id, 1)
    qualification, value = _cockpit_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


def test_multiple_with_count_zero_fails_closed(conn: Any) -> None:
    """Covered generically by the count==0 contradiction check, but proven
    explicitly for MULTIPLE too."""
    design_id = "BD-CDB-MULTIPLE-COUNT-ZERO"
    design = _v06_design(design_id, cockpit_position="multiple", cockpit_count=0)
    _admit(conn, design)
    _admit_cockpit_position(conn, design_id, "multiple")
    _admit_cockpit_count(conn, design_id, 0)
    qualification, value = _cockpit_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


def test_multiple_with_count_two_still_confirms(conn: Any) -> None:
    """A confirmed count of two or more is consistent with MULTIPLE and
    remains a confirmed positive match."""
    design_id = "BD-CDB-MULTIPLE-COUNT-TWO"
    design = _v06_design(design_id, cockpit_position="multiple", cockpit_count=2)
    _admit(conn, design)
    _admit_cockpit_position(conn, design_id, "multiple")
    _admit_cockpit_count(conn, design_id, 2)
    qualification, value = _cockpit_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == "MULTIPLE"


def test_multiple_with_count_unqualified_still_confirms(conn: Any) -> None:
    """`cockpit_count` is never fabricated as mandatory evidence -- MULTIPLE
    alone, with count unresolved, still confirms."""
    design_id = "BD-CDB-MULTIPLE-COUNT-UNQUALIFIED"
    design = _v06_design(design_id, cockpit_position="multiple", cockpit_count=2)
    _admit(conn, design)
    _admit_cockpit_position(conn, design_id, "multiple")
    # Deliberately no _admit_cockpit_count call: cockpit_count stays unresolved.
    qualification, value = _cockpit_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == "MULTIPLE"


def test_single_positions_with_count_one_are_unaffected_by_the_multiple_check(
    conn: Any,
) -> None:
    """The MULTIPLE+count==1 contradiction check is specific to MULTIPLE --
    AFT/CENTER/FORWARD paired with a confirmed count of one is consistent
    (one cockpit, at that one position) and must still confirm."""
    design_id = "BD-CDB-AFT-COUNT-ONE"
    design = _v06_design(design_id, cockpit_position="aft", cockpit_count=1)
    _admit(conn, design)
    _admit_cockpit_position(conn, design_id, "aft")
    _admit_cockpit_count(conn, design_id, 1)
    qualification, value = _cockpit_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == "AFT"


def test_named_variant_count_override_cannot_bypass_the_multiple_consistency_check(
    conn: Any,
) -> None:
    """A NamedVariant overriding `cockpit_count` to 1 while inheriting (or
    itself asserting) `cockpit_position=multiple` must still fail closed --
    the per-configuration cross-check applies independently to each
    resolved configuration's own qualified count, never bypassed by
    override/inheritance plumbing."""
    design_id = "BD-CDB-VAR-MULTIPLE-BYPASS"
    design = _v06_design(design_id, cockpit_position="multiple", cockpit_count=2)
    design["named_variants"] = [
        {"id": "VAR-CDB-MULTIPLE-BYPASS", "overrides": {"deck": {"cockpit_count": 1}}}
    ]
    _admit(conn, design)
    _admit_cockpit_position(conn, design_id, "multiple")
    _admit_cockpit_count(conn, design_id, 2)
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.NAMED_VARIANT,
        subject_id="VAR-CDB-MULTIPLE-BYPASS",
        field_pointer="/overrides/deck/cockpit_count",
        value=Decimal(1),
        resolution_id="FR-VAR-CDB-MULTIPLE-BYPASS",
        fetch_canonical_value=lookup_cockpit_position_canonical_value,
    )
    config_set = build_boat_design_cockpit_position_set(conn, design)
    baseline_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == f"{design_id}::baseline"
    )
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == f"{design_id}::VAR-CDB-MULTIPLE-BYPASS"
    )
    baseline_qualified = baseline_config.projection.get_categorical(
        COCKPIT_POSITION_PROJECTION_FIELD
    )
    variant_qualified = variant_config.projection.get_categorical(COCKPIT_POSITION_PROJECTION_FIELD)
    assert baseline_qualified.qualification is ValueQualification.CONFIRMED
    assert baseline_qualified.value == "MULTIPLE"
    assert variant_qualified.qualification is ValueQualification.MISSING
    assert variant_qualified.value is None


# ---------------------------------------------------------------------------
# compatible_boat_design_ids_for_cockpit_position
# ---------------------------------------------------------------------------


def test_compatible_boat_design_ids_for_cockpit_position_admits_matching_design(
    conn: Any,
) -> None:
    design_id = "BD-CDB-COMPAT-1"
    design = _v06_design(design_id, cockpit_position="aft")
    _admit(conn, design)
    _admit_cockpit_position(conn, design_id, "aft")
    compatible = compatible_boat_design_ids_for_cockpit_position(conn, "AFT", [design])
    assert compatible == frozenset({design_id})


def test_compatible_boat_design_ids_for_cockpit_position_rejects_non_v0_1_value(
    conn: Any,
) -> None:
    design = _v06_design("BD-CDB-COMPAT-2", cockpit_position="aft")
    with pytest.raises(ValueError):
        compatible_boat_design_ids_for_cockpit_position(conn, "OTHER", [design])
