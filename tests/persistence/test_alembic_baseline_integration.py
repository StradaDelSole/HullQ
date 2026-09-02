"""PostgreSQL-backed Alembic migration baseline adoption tests — SLICE-0042.

Each test runs against its own disposable PostgreSQL *schema* (created/
dropped by the ``scenario_url`` fixture below, isolated via the connection
``options=-c search_path=...`` parameter) because the scenarios under test
are mutually exclusive *database states* (genuinely empty, accepted legacy,
already-baselined, partial/unsafe) that cannot share one schema. Schema-
level isolation is used instead of ``CREATE DATABASE`` so these tests do
not require a CREATEDB-privileged role — only ``CREATE`` on the target
database, which the ordinary HULLQ_TEST_DATABASE_URL role already has.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from psycopg.types.json import Jsonb

from hullq.persistence.alembic_baseline import (
    ALEMBIC_VERSION_TABLE,
    BASELINE_REVISION,
    REQUIRED_LEGACY_MIGRATION_IDS,
    BaselineOutcome,
    alembic_heads,
    alembic_upgrade_head,
    prepare_alembic_baseline,
    read_alembic_version,
)
from hullq.persistence.migrations import MIGRATIONS_DIR, MIGRATIONS_TABLE, apply_migrations


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
def scenario_url(db_url: str) -> Generator[str]:
    """A fresh, empty, disposable-schema URL — the schema is dropped after the test."""
    schema_name = f"hullq_s0042_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        yield _with_search_path(db_url, schema_name)
    finally:
        _drop_schema(db_url, schema_name)


def _apply_only_001(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} ("
            "migration_id TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
        )
    conn.commit()
    migration_sql = (MIGRATIONS_DIR / "001_initial_schema.sql").read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(migration_sql)
        cur.execute(
            f"INSERT INTO {MIGRATIONS_TABLE} (migration_id) VALUES (%s)", ["001_initial_schema"]
        )
    conn.commit()


def _insert_probe_bundle(conn: psycopg.Connection, bundle_id: str, content_hash: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO research_bundles "
            "(bundle_id, bundle_version, content_hash, research_target) "
            "VALUES (%s, %s, %s, %s)",
            [
                bundle_id,
                "v1",
                content_hash,
                Jsonb({"manufacturer": "Probe", "model": "Boat", "first_built": None}),
            ],
        )
    conn.commit()


def test_fresh_database_bootstraps_and_stamps(scenario_url: str) -> None:
    result = prepare_alembic_baseline(scenario_url)
    assert result.outcome is BaselineOutcome.FRESH_BOOTSTRAPPED_AND_STAMPED
    assert read_alembic_version(scenario_url) == BASELINE_REVISION

    conn = psycopg.connect(scenario_url)
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT migration_id FROM {MIGRATIONS_TABLE}")
            applied = {row[0] for row in cur.fetchall()}
    finally:
        conn.close()
    assert applied == REQUIRED_LEGACY_MIGRATION_IDS


def test_existing_legacy_database_verified_and_data_preserved(scenario_url: str) -> None:
    conn = psycopg.connect(scenario_url)
    try:
        apply_migrations(conn)
        _insert_probe_bundle(conn, "S0042-PROBE", "deadbeefcafe0042")
    finally:
        conn.close()

    result = prepare_alembic_baseline(scenario_url)
    assert result.outcome is BaselineOutcome.LEGACY_VERIFIED_AND_STAMPED
    assert read_alembic_version(scenario_url) == BASELINE_REVISION

    conn = psycopg.connect(scenario_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content_hash FROM research_bundles WHERE bundle_id = %s", ["S0042-PROBE"]
            )
            row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == "deadbeefcafe0042"


def test_already_baselined_database_is_idempotent(scenario_url: str) -> None:
    first = prepare_alembic_baseline(scenario_url)
    assert first.outcome is BaselineOutcome.FRESH_BOOTSTRAPPED_AND_STAMPED

    second = prepare_alembic_baseline(scenario_url)
    assert second.outcome is BaselineOutcome.ALREADY_BASELINED
    assert read_alembic_version(scenario_url) == BASELINE_REVISION


def test_partial_legacy_migration_state_is_rejected(scenario_url: str) -> None:
    conn = psycopg.connect(scenario_url)
    try:
        _apply_only_001(conn)
    finally:
        conn.close()

    result = prepare_alembic_baseline(scenario_url)
    assert result.outcome is BaselineOutcome.REJECTED_UNSAFE_STATE
    assert result.reason is not None and "missing" in result.reason
    assert read_alembic_version(scenario_url) is None


def test_missing_structural_evidence_is_rejected(scenario_url: str) -> None:
    conn = psycopg.connect(scenario_url)
    try:
        apply_migrations(conn)
        with conn.cursor() as cur:
            cur.execute("DROP TABLE canonical_boat_designs CASCADE")
        conn.commit()
    finally:
        conn.close()

    result = prepare_alembic_baseline(scenario_url)
    assert result.outcome is BaselineOutcome.REJECTED_UNSAFE_STATE
    assert result.reason is not None and "structural evidence missing" in result.reason
    assert read_alembic_version(scenario_url) is None


def test_unexpected_post_002_legacy_migration_id_is_rejected(scenario_url: str) -> None:
    conn = psycopg.connect(scenario_url)
    try:
        apply_migrations(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {MIGRATIONS_TABLE} (migration_id) VALUES (%s)", ["003_unexpected"]
            )
        conn.commit()
    finally:
        conn.close()

    result = prepare_alembic_baseline(scenario_url)
    assert result.outcome is BaselineOutcome.REJECTED_UNSAFE_STATE
    assert result.reason is not None and "unexpected" in result.reason
    assert read_alembic_version(scenario_url) is None


def test_conflicting_alembic_revision_is_rejected(scenario_url: str) -> None:
    conn = psycopg.connect(scenario_url)
    try:
        apply_migrations(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE TABLE {ALEMBIC_VERSION_TABLE} ("
                "version_num VARCHAR(32) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
            )
            cur.execute(
                f"INSERT INTO {ALEMBIC_VERSION_TABLE} (version_num) VALUES (%s)", ["bogus0000"]
            )
        conn.commit()
    finally:
        conn.close()

    result = prepare_alembic_baseline(scenario_url)
    assert result.outcome is BaselineOutcome.REJECTED_UNSAFE_STATE
    assert result.reason is not None and "bogus0000" in result.reason
    # The unsafe stamp must not be silently corrected.
    assert read_alembic_version(scenario_url) == "bogus0000"


def test_alembic_current_reports_expected_baseline_after_adoption(scenario_url: str) -> None:
    result = prepare_alembic_baseline(scenario_url)
    assert result.outcome is BaselineOutcome.FRESH_BOOTSTRAPPED_AND_STAMPED

    assert read_alembic_version(scenario_url) == BASELINE_REVISION
    assert alembic_heads(scenario_url) == [BASELINE_REVISION]


def test_alembic_upgrade_head_is_schema_and_data_neutral(scenario_url: str) -> None:
    result = prepare_alembic_baseline(scenario_url)
    assert result.outcome is BaselineOutcome.FRESH_BOOTSTRAPPED_AND_STAMPED

    conn = psycopg.connect(scenario_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = current_schema() ORDER BY table_name"
            )
            before = [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

    alembic_upgrade_head(scenario_url)

    conn = psycopg.connect(scenario_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = current_schema() ORDER BY table_name"
            )
            after = [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

    assert after == before
    assert read_alembic_version(scenario_url) == BASELINE_REVISION
