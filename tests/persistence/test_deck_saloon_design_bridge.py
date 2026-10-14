"""PostgreSQL tests for `hullq.search.deck_saloon_design_bridge` — SLICE-0086.

Covers the v0.6-only `deck.deck_saloon` mapping (v0.5 has no `deck` section
at all), the `none`/`unknown` fail-closed rule (never a public `NONE`
filter), `DECK_SALOON`/`PILOTHOUSE` independence, and
`compatible_boat_design_ids_for_deck_saloon` -- mirroring
`tests/persistence/test_keel_design_bridge.py`'s structure (the simplest
single-field bridge shape).
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
from hullq.search.deck_saloon_design_bridge import (
    DECK_SALOON_PROJECTION_FIELD,
    SEARCH_DECK_SALOON_VALUES,
    build_boat_design_deck_saloon_configuration_set,
    compatible_boat_design_ids_for_deck_saloon,
    lookup_deck_saloon_canonical_value,
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
    schema_name = f"hullq_s0086ddb_{uuid.uuid4().hex[:16]}"
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


def _v06_design(design_id: str, *, deck_saloon: str | None = None) -> dict[str, object]:
    return {
        "id": design_id,
        "baseline": {"deck": {"deck_saloon": deck_saloon}},
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


def _admit_deck_saloon(conn: Any, design_id: str, value: str) -> None:
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/deck/deck_saloon",
        value=value,
        resolution_id=f"FR-{design_id}-DECKSALOON",
        fetch_canonical_value=lookup_deck_saloon_canonical_value,
    )


def _deck_saloon_value(
    conn: Any, design: dict[str, object]
) -> tuple[ValueQualification, str | None]:
    config_set = build_boat_design_deck_saloon_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_categorical(
        DECK_SALOON_PROJECTION_FIELD
    )
    return qualified.qualification, qualified.value


# ---------------------------------------------------------------------------
# Public v0.1 vocabulary
# ---------------------------------------------------------------------------


def test_accepted_search_deck_saloon_values() -> None:
    assert frozenset({"DECK_SALOON", "PILOTHOUSE"}) == SEARCH_DECK_SALOON_VALUES


# ---------------------------------------------------------------------------
# v0.6 mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_deck_saloon", "expected_value"),
    [("deck_saloon", "DECK_SALOON"), ("pilothouse", "PILOTHOUSE")],
)
def test_v06_mapping(conn: Any, raw_deck_saloon: str, expected_value: str) -> None:
    design_id = f"BD-DDB-V06-{raw_deck_saloon}"
    design = _v06_design(design_id, deck_saloon=raw_deck_saloon)
    _admit(conn, design)
    _admit_deck_saloon(conn, design_id, raw_deck_saloon)
    qualification, value = _deck_saloon_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == expected_value


@pytest.mark.parametrize("unsupported", ["none", "unknown"])
def test_none_and_unknown_fail_closed_never_a_public_filter_value(
    conn: Any, unsupported: str
) -> None:
    """`none` is a real design value (positively-asserted absence) but has
    no authorized v0.1 public Search mapping -- it fails closed to MISSING
    exactly like an unmapped raw token, never a bespoke non-match sentinel."""
    design_id = f"BD-DDB-UNSUP-{unsupported}"
    design = _v06_design(design_id, deck_saloon=unsupported)
    _admit(conn, design)
    _admit_deck_saloon(conn, design_id, unsupported)
    qualification, value = _deck_saloon_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


def test_v05_design_with_no_deck_section_is_missing(conn: Any) -> None:
    design_id = "BD-DDB-V05"
    design = _v05_design(design_id)
    _admit(conn, design)
    qualification, value = _deck_saloon_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


def test_deck_saloon_and_pilothouse_are_never_merged(conn: Any) -> None:
    """A design confirmed `deck_saloon` must not also qualify as PILOTHOUSE,
    and vice versa -- the two categories are independent."""
    deck_saloon_design_id = "BD-DDB-DECKSALOON-ONLY"
    design = _v06_design(deck_saloon_design_id, deck_saloon="deck_saloon")
    _admit(conn, design)
    _admit_deck_saloon(conn, deck_saloon_design_id, "deck_saloon")
    assert compatible_boat_design_ids_for_deck_saloon(conn, "DECK_SALOON", [design]) == frozenset(
        {deck_saloon_design_id}
    )
    assert compatible_boat_design_ids_for_deck_saloon(conn, "PILOTHOUSE", [design]) == frozenset()


# ---------------------------------------------------------------------------
# compatible_boat_design_ids_for_deck_saloon
# ---------------------------------------------------------------------------


def test_compatible_boat_design_ids_for_deck_saloon_admits_matching_design(conn: Any) -> None:
    design_id = "BD-DDB-COMPAT-1"
    design = _v06_design(design_id, deck_saloon="pilothouse")
    _admit(conn, design)
    _admit_deck_saloon(conn, design_id, "pilothouse")
    compatible = compatible_boat_design_ids_for_deck_saloon(conn, "PILOTHOUSE", [design])
    assert compatible == frozenset({design_id})


def test_compatible_boat_design_ids_for_deck_saloon_rejects_non_v0_1_value(conn: Any) -> None:
    design = _v06_design("BD-DDB-COMPAT-2", deck_saloon="pilothouse")
    with pytest.raises(ValueError):
        compatible_boat_design_ids_for_deck_saloon(conn, "NONE", [design])
