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
from hullq.search.criteria import CategoricalLeafCriterion, evaluate_categorical_leaf
from hullq.search.deck_saloon_design_bridge import (
    DECK_SALOON_NONE_SENTINEL,
    DECK_SALOON_PROJECTION_FIELD,
    SEARCH_DECK_SALOON_VALUES,
    build_boat_design_deck_saloon_configuration_set,
    compatible_boat_design_ids_for_deck_saloon,
    lookup_deck_saloon_canonical_value,
)
from hullq.search.types import TruthState, ValueQualification

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


def test_unknown_fails_closed_to_missing(conn: Any) -> None:
    """`unknown` has no taxonomy-map entry at all and fails closed to
    MISSING, exactly like any other unmapped raw token."""
    design_id = "BD-DDB-UNSUP-unknown"
    design = _v06_design(design_id, deck_saloon="unknown")
    _admit(conn, design)
    _admit_deck_saloon(conn, design_id, "unknown")
    qualification, value = _deck_saloon_value(conn, design)
    assert qualification is ValueQualification.MISSING
    assert value is None


def test_none_confirms_to_the_internal_sentinel_never_a_public_filter_value(
    conn: Any,
) -> None:
    """PR #349 review Finding A: a qualified, source-backed `none` is a
    *known* fact (positively-asserted absence) -- it must be CONFIRMED to
    the internal-only sentinel, mechanically distinct from the MISSING an
    unqualified/`unknown` value produces, and the sentinel itself must never
    be a member of the public `SEARCH_DECK_SALOON_VALUES` vocabulary."""
    design_id = "BD-DDB-NONE-CONFIRMED"
    design = _v06_design(design_id, deck_saloon="none")
    _admit(conn, design)
    _admit_deck_saloon(conn, design_id, "none")
    qualification, value = _deck_saloon_value(conn, design)
    assert qualification is ValueQualification.CONFIRMED
    assert value == DECK_SALOON_NONE_SENTINEL
    assert DECK_SALOON_NONE_SENTINEL not in SEARCH_DECK_SALOON_VALUES


@pytest.mark.parametrize("requested", ["DECK_SALOON", "PILOTHOUSE"])
def test_confirmed_none_is_a_typed_non_match_against_either_public_category(
    conn: Any, requested: str
) -> None:
    """A design whose `deck_saloon` is confirmed `none` must contribute a
    typed confirmed FALSE (non-match) against a buyer requesting either
    `DECK_SALOON` or `PILOTHOUSE` -- never UNKNOWN/insufficient-data merely
    because the request didn't ask for the sentinel itself, and never a
    fabricated TRUE for either requested category."""
    design_id = f"BD-DDB-NONE-NONMATCH-{requested}"
    design = _v06_design(design_id, deck_saloon="none")
    _admit(conn, design)
    _admit_deck_saloon(conn, design_id, "none")
    config_set = build_boat_design_deck_saloon_configuration_set(conn, design)
    qualified = config_set.configurations[0].projection.get_categorical(
        DECK_SALOON_PROJECTION_FIELD
    )
    evaluation = evaluate_categorical_leaf(
        CategoricalLeafCriterion(field=DECK_SALOON_PROJECTION_FIELD, equals=requested), qualified
    )
    assert evaluation.truth is TruthState.FALSE


def test_compatible_boat_design_ids_for_deck_saloon_excludes_a_confirmed_none_design(
    conn: Any,
) -> None:
    """The internal NONE sentinel must never let a design with a confirmed
    `none` deck_saloon slip into the compatible-ids set for either public
    category."""
    design_id = "BD-DDB-NONE-COMPAT-EXCLUDE"
    design = _v06_design(design_id, deck_saloon="none")
    _admit(conn, design)
    _admit_deck_saloon(conn, design_id, "none")
    assert compatible_boat_design_ids_for_deck_saloon(conn, "DECK_SALOON", [design]) == frozenset()
    assert compatible_boat_design_ids_for_deck_saloon(conn, "PILOTHOUSE", [design]) == frozenset()


def test_compatible_boat_design_ids_for_deck_saloon_rejects_the_internal_none_sentinel(
    conn: Any,
) -> None:
    """The internal sentinel must never be accepted as a caller-supplied
    public filter value -- it is a projection-side detail only."""
    design = _v06_design("BD-DDB-NONE-REJECT-SENTINEL", deck_saloon="none")
    with pytest.raises(ValueError):
        compatible_boat_design_ids_for_deck_saloon(conn, DECK_SALOON_NONE_SENTINEL, [design])


# ---------------------------------------------------------------------------
# NamedVariant own override / inheritance -- known (none) vs missing
# ---------------------------------------------------------------------------


def test_named_variant_own_override_to_none_is_confirmed_known_absence(conn: Any) -> None:
    """A NamedVariant overriding `deck_saloon` to `none` must itself qualify
    to the internal NONE sentinel -- the known/missing distinction survives
    NamedVariant override, not only on the baseline."""
    design_id = "BD-DDB-VAR-NONE-1"
    design = _v06_design(design_id, deck_saloon="deck_saloon")
    design["named_variants"] = [
        {"id": "VAR-DDB-NONE-1", "overrides": {"deck": {"deck_saloon": "none"}}}
    ]
    _admit(conn, design)
    _admit_deck_saloon(conn, design_id, "deck_saloon")
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.NAMED_VARIANT,
        subject_id="VAR-DDB-NONE-1",
        field_pointer="/overrides/deck/deck_saloon",
        value="none",
        resolution_id="FR-VAR-DDB-NONE-1",
        fetch_canonical_value=lookup_deck_saloon_canonical_value,
    )
    config_set = build_boat_design_deck_saloon_configuration_set(conn, design)
    baseline_config = next(
        c for c in config_set.configurations if c.identity.configuration_id == f"{design_id}::baseline"
    )
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == f"{design_id}::VAR-DDB-NONE-1"
    )
    baseline_qualified = baseline_config.projection.get_categorical(DECK_SALOON_PROJECTION_FIELD)
    variant_qualified = variant_config.projection.get_categorical(DECK_SALOON_PROJECTION_FIELD)
    assert baseline_qualified.qualification is ValueQualification.CONFIRMED
    assert baseline_qualified.value == "DECK_SALOON"
    assert variant_qualified.qualification is ValueQualification.CONFIRMED
    assert variant_qualified.value == DECK_SALOON_NONE_SENTINEL


def test_named_variant_without_own_override_inherits_a_confirmed_none_baseline(
    conn: Any,
) -> None:
    """A NamedVariant with no own `deck_saloon` override must inherit the
    baseline's own already-qualified NONE sentinel, not re-derive/lose it."""
    design_id = "BD-DDB-VAR-NONE-2"
    design = _v06_design(design_id, deck_saloon="none")
    design["named_variants"] = [{"id": "VAR-DDB-NONE-2", "overrides": {"deck": {}}}]
    _admit(conn, design)
    _admit_deck_saloon(conn, design_id, "none")
    config_set = build_boat_design_deck_saloon_configuration_set(conn, design)
    variant_config = next(
        c
        for c in config_set.configurations
        if c.identity.configuration_id == f"{design_id}::VAR-DDB-NONE-2"
    )
    qualified = variant_config.projection.get_categorical(DECK_SALOON_PROJECTION_FIELD)
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == DECK_SALOON_NONE_SENTINEL


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
