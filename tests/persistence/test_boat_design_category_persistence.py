"""PostgreSQL-backed BoatDesign category assertion persistence tests -- SLICE-0091.

Each test runs against its own disposable PostgreSQL *schema*, brought from
genuinely empty to the SLICE-0091 Alembic head, mirroring the
`tests/persistence/test_physical_boat_claims_persistence.py` isolation
pattern.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.domain.physical_boat_claims import AssertionKind, VesselCategory
from hullq.domain.provenance import ResolverKind, ResolverMetadata
from hullq.domain.vessel_category import (
    BoatDesignCategoryAssertionId,
    DesignVesselCategoryAssertion,
)
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.boat_design_category import (
    CATALOG_ADMISSION_SECRET_ENV_VAR,
    BoatDesignCategoryAssertionWriteStatus,
    fetch_boat_design_category_assertion,
    fetch_current_boat_design_category_assertion,
    list_boat_design_category_assertion_revisions,
    write_boat_design_category_assertion,
)

VA = AssertionKind.VALUE_ASSERTION
UNK = AssertionKind.UNKNOWN
_TEST_ADMISSION_SECRET = "slice-0091-test-catalog-admission-secret"


@pytest.fixture(autouse=True)
def _configured_admission_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test in this file gets a real configured catalog-admission
    secret by default; tests exercising the missing/wrong-secret paths
    override it explicitly via the same `monkeypatch` fixture instance."""
    monkeypatch.setenv(CATALOG_ADMISSION_SECRET_ENV_VAR, _TEST_ADMISSION_SECRET)


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
def category_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0091_{uuid.uuid4().hex[:16]}"
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
def category_conn(category_url: str) -> Generator[Any]:
    conn = psycopg.connect(category_url)
    try:
        yield conn
    finally:
        conn.close()


def _table_names(conn: Any) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
        )
        return {row[0] for row in cur.fetchall()}


def _insert_minimal_boat_design(conn: Any, design_id: str, model_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, '{}'::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, "1" * 64],
        )
    conn.commit()


def _issuer() -> ResolverMetadata:
    """Ordinary audit/provenance metadata -- amendment Finding G: this no
    longer decides authorization by itself, only `admission_secret` does."""
    return ResolverMetadata(
        kind=ResolverKind.DETERMINISTIC_TOOL,
        identifier="slice-0091-test-harness",
        version="1",
    )


def test_migration_adds_the_expected_category_tables(category_conn: Any) -> None:
    tables = _table_names(category_conn)
    assert {"boat_design_category_assertions", "boat_design_category_assertion_heads"} <= tables
    with category_conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'physical_boat_claim_revisions' "
            "AND column_name IN ('vessel_category_assertion_kind', 'vessel_category_value')"
        )
        columns = {row[0] for row in cur.fetchall()}
    assert columns == {"vessel_category_assertion_kind", "vessel_category_value"}


def test_first_write_for_unknown_boat_design_fails_closed(category_conn: Any) -> None:
    result = write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-MISSING",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-1"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL),
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    assert result.status is BoatDesignCategoryAssertionWriteStatus.BOAT_DESIGN_NOT_FOUND
    assert result.current_assertion_id is None


def test_create_revise_readback_and_history(category_conn: Any) -> None:
    _insert_minimal_boat_design(category_conn, "BD-1", "BM-1")

    created = write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-1",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-1"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL),
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    assert created.status is BoatDesignCategoryAssertionWriteStatus.CREATED
    assert created.current_assertion_id == BoatDesignCategoryAssertionId("BDCAT-1")

    current = fetch_current_boat_design_category_assertion(category_conn, "BD-1")
    assert current is not None
    assert current.assertion.assertion_kind is VA
    assert current.assertion.value is VesselCategory.SAIL
    assert current.previous_assertion_id is None
    category_conn.commit()  # readback leaves the connection non-IDLE otherwise

    # Revise: SAIL -> MOTORSAILER, superseding BDCAT-1.
    revised = write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-1",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-2"),
        expected_current_assertion_id=BoatDesignCategoryAssertionId("BDCAT-1"),
        assertion=DesignVesselCategoryAssertion(
            assertion_kind=VA, value=VesselCategory.MOTORSAILER
        ),
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    assert revised.status is BoatDesignCategoryAssertionWriteStatus.REVISED

    current = fetch_current_boat_design_category_assertion(category_conn, "BD-1")
    assert current is not None
    assert current.assertion.value is VesselCategory.MOTORSAILER
    assert current.previous_assertion_id == BoatDesignCategoryAssertionId("BDCAT-1")

    history = list_boat_design_category_assertion_revisions(category_conn, "BD-1")
    assert [h.assertion_id.value for h in history] == ["BDCAT-1", "BDCAT-2"]

    # The superseded revision is still durably retrievable by its own id,
    # unmodified -- "a legitimate category change requires versioned
    # evidence rather than destructive overwrite" (SLICE-0091 §B).
    superseded = fetch_boat_design_category_assertion(
        category_conn, BoatDesignCategoryAssertionId("BDCAT-1")
    )
    assert superseded is not None
    assert superseded.assertion.value is VesselCategory.SAIL


def test_retraction_to_unknown_is_a_new_revision_never_an_overwrite(category_conn: Any) -> None:
    _insert_minimal_boat_design(category_conn, "BD-2", "BM-2")
    write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-2",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-A"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.POWER),
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    retracted = write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-2",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-B"),
        expected_current_assertion_id=BoatDesignCategoryAssertionId("BDCAT-A"),
        assertion=DesignVesselCategoryAssertion(assertion_kind=UNK, value=None),
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    assert retracted.status is BoatDesignCategoryAssertionWriteStatus.REVISED
    current = fetch_current_boat_design_category_assertion(category_conn, "BD-2")
    assert current is not None
    assert current.assertion.assertion_kind is UNK
    assert current.assertion.value is None

    history = list_boat_design_category_assertion_revisions(category_conn, "BD-2")
    assert len(history) == 2
    assert history[0].assertion.value is VesselCategory.POWER


def test_stale_expected_predecessor_fails_closed_as_conflict(category_conn: Any) -> None:
    _insert_minimal_boat_design(category_conn, "BD-3", "BM-3")
    write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-3",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-X"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL),
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    stale = write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-3",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-Y"),
        expected_current_assertion_id=None,  # stale -- real current is BDCAT-X
        assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.POWER),
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    assert stale.status is BoatDesignCategoryAssertionWriteStatus.CONFLICT
    assert stale.current_assertion_id == BoatDesignCategoryAssertionId("BDCAT-X")
    # No partial replacement of the already-valid current state.
    current = fetch_current_boat_design_category_assertion(category_conn, "BD-3")
    assert current is not None
    assert current.assertion.value is VesselCategory.SAIL


def test_exact_retry_is_idempotent_already_exists(category_conn: Any) -> None:
    _insert_minimal_boat_design(category_conn, "BD-4", "BM-4")
    assertion = DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL)
    first = write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-4",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-R"),
        expected_current_assertion_id=None,
        assertion=assertion,
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    assert first.status is BoatDesignCategoryAssertionWriteStatus.CREATED

    retry = write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-4",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-R"),
        expected_current_assertion_id=None,
        assertion=assertion,
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    assert retry.status is BoatDesignCategoryAssertionWriteStatus.ALREADY_EXISTS
    assert retry.current_assertion_id == BoatDesignCategoryAssertionId("BDCAT-R")


# ---------------------------------------------------------------------------
# Amendment Finding G: genuine admission-secret authorization boundary
# (supersedes the earlier Finding D self-declared-issuer-literal check,
# which any caller could read from source and trivially replicate).
# ---------------------------------------------------------------------------


def test_missing_admission_secret_configuration_rejects_every_caller(
    category_conn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deployment that has never configured the real secret admits
    nobody -- never a silent default-allow -- even with the exact right
    *value* supplied by the caller, since there is nothing correct to match
    against."""
    monkeypatch.delenv(CATALOG_ADMISSION_SECRET_ENV_VAR, raising=False)
    _insert_minimal_boat_design(category_conn, "BD-5", "BM-5")
    result = write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-5",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-NOENV"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.POWER),
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    assert result.status is BoatDesignCategoryAssertionWriteStatus.ADMISSION_NOT_AUTHORIZED
    assert result.current_assertion_id is None
    assert fetch_current_boat_design_category_assertion(category_conn, "BD-5") is None
    assert (
        fetch_boat_design_category_assertion(
            category_conn, BoatDesignCategoryAssertionId("BDCAT-NOENV")
        )
        is None
    )


def test_wrong_admission_secret_is_rejected_without_mutation(category_conn: Any) -> None:
    """A real secret is configured, but the caller supplies the wrong
    value -- fails closed, no row written, no head created."""
    _insert_minimal_boat_design(category_conn, "BD-6", "BM-6")
    result = write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-6",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-WRONG"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL),
        issuer=_issuer(),
        admission_secret="definitely-not-the-configured-secret",
    )
    assert result.status is BoatDesignCategoryAssertionWriteStatus.ADMISSION_NOT_AUTHORIZED
    assert fetch_current_boat_design_category_assertion(category_conn, "BD-6") is None


def test_empty_admission_secret_is_rejected(category_conn: Any) -> None:
    _insert_minimal_boat_design(category_conn, "BD-7", "BM-7")
    result = write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-7",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-EMPTY"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL),
        issuer=_issuer(),
        admission_secret="",
    )
    assert result.status is BoatDesignCategoryAssertionWriteStatus.ADMISSION_NOT_AUTHORIZED
    assert fetch_current_boat_design_category_assertion(category_conn, "BD-7") is None


def test_correct_secret_succeeds_regardless_of_issuer_kind(category_conn: Any) -> None:
    """Finding G's explicit consequence: `issuer` is audit metadata only --
    a HUMAN or LLM issuer with the *correct* secret is just as authorized
    as a DETERMINISTIC_TOOL one, since the secret (not the issuer literal)
    is what actually grants the capability."""
    _insert_minimal_boat_design(category_conn, "BD-8", "BM-8")
    human_result = write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-8",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-HUMAN-OK"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL),
        issuer=ResolverMetadata(
            kind=ResolverKind.HUMAN, identifier="an-owner-operator", version=None
        ),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    assert human_result.status is BoatDesignCategoryAssertionWriteStatus.CREATED

    current = fetch_current_boat_design_category_assertion(category_conn, "BD-8")
    assert current is not None
    assert current.issuer.kind is ResolverKind.HUMAN
    category_conn.commit()

    _insert_minimal_boat_design(category_conn, "BD-9", "BM-9")
    llm_result = write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-9",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-LLM-OK"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL),
        issuer=ResolverMetadata(kind=ResolverKind.LLM, identifier="an-llm-assistant", version="1"),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    assert llm_result.status is BoatDesignCategoryAssertionWriteStatus.CREATED


def test_authorized_secret_still_succeeds(category_conn: Any) -> None:
    """Positive control: the configured secret, supplied correctly, is
    unaffected by this amendment."""
    _insert_minimal_boat_design(category_conn, "BD-10", "BM-10")
    result = write_boat_design_category_assertion(
        category_conn,
        boat_design_id="BD-10",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-OK"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL),
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    assert result.status is BoatDesignCategoryAssertionWriteStatus.CREATED
