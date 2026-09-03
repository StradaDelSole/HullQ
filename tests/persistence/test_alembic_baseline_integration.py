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
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from psycopg.types.json import Jsonb

import hullq.persistence.migrations as migrations_mod
from hullq.persistence.alembic_baseline import (
    ALEMBIC_VERSION_TABLE,
    BASELINE_REVISION,
    REQUIRED_LEGACY_MIGRATION_IDS,
    BaselineOutcome,
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


def _table_names(url: str) -> set[str]:
    conn = psycopg.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = current_schema()"
            )
            return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


def test_pre_existing_non_fingerprint_table_blocks_fresh_bootstrap(scenario_url: str) -> None:
    """A HullQ table outside REPRESENTATIVE_LEGACY_TABLES (e.g. canonical_brands)
    must still prevent the database from being misclassified as genuinely
    empty — otherwise apply_migrations() could commit 001 before failing on
    002's pre-existing table, leaving a partially-migrated database."""
    conn = psycopg.connect(scenario_url)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE canonical_brands (id TEXT PRIMARY KEY)")
        conn.commit()
    finally:
        conn.close()

    result = prepare_alembic_baseline(scenario_url)

    assert result.outcome is BaselineOutcome.REJECTED_UNSAFE_STATE
    assert result.reason is not None
    assert read_alembic_version(scenario_url) is None
    # No legacy/tracking tables were added as a side effect of the rejected attempt.
    assert _table_names(scenario_url) == {"canonical_brands"}


def test_unrecognized_untracked_table_blocks_fresh_bootstrap(scenario_url: str) -> None:
    """A table that belongs to neither the legacy 001/002 schema nor Alembic
    (e.g. an unrelated ``hullq_untracked_probe``) must also block treating
    the database as genuinely empty — "empty" means no relation of any
    kind, not merely "no relation we happen to recognize." Otherwise
    apply_migrations() would run against, and Alembic baseline stamping
    could legitimize, a previously unknown schema state."""
    conn = psycopg.connect(scenario_url)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE hullq_untracked_probe (id TEXT PRIMARY KEY, note TEXT)")
            cur.execute(
                "INSERT INTO hullq_untracked_probe (id, note) VALUES (%s, %s)", ["P1", "untouched"]
            )
        conn.commit()
    finally:
        conn.close()

    result = prepare_alembic_baseline(scenario_url)

    assert result.outcome is BaselineOutcome.REJECTED_UNSAFE_STATE
    assert result.reason is not None
    assert read_alembic_version(scenario_url) is None
    # No legacy application tables (including the hullq_schema_migrations
    # tracking table) were added as a side effect of the rejected attempt.
    assert _table_names(scenario_url) == {"hullq_untracked_probe"}

    conn = psycopg.connect(scenario_url)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, note FROM hullq_untracked_probe")
            rows = cur.fetchall()
    finally:
        conn.close()
    assert rows == [("P1", "untouched")]


def test_fresh_bootstrap_is_blocked_by_frozen_legacy_guard(
    scenario_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The actual preparation path (not just the isolated guard function)
    must refuse to run the legacy bootstrap when a post-002 legacy SQL
    migration file is present, and must do so before any database mutation."""
    for stem in sorted(REQUIRED_LEGACY_MIGRATION_IDS):
        (tmp_path / f"{stem}.sql").write_text(
            (MIGRATIONS_DIR / f"{stem}.sql").read_text(encoding="utf-8"), encoding="utf-8"
        )
    (tmp_path / "003_unexpected.sql").write_text(
        "-- would-be post-baseline marketplace DDL", encoding="utf-8"
    )
    monkeypatch.setattr(migrations_mod, "MIGRATIONS_DIR", tmp_path)

    result = prepare_alembic_baseline(scenario_url)

    assert result.outcome is BaselineOutcome.REJECTED_UNSAFE_STATE
    assert result.reason is not None and "003_unexpected" in result.reason
    assert read_alembic_version(scenario_url) is None
    # The legacy runner must never have been invoked: no tables at all.
    assert _table_names(scenario_url) == set()


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

    # prepare_alembic_baseline() stamps to the baseline only — it does not
    # run `alembic upgrade head` — so the stamped revision is expected to
    # differ from the script directory's current head once later revisions
    # (e.g. SLICE-0043's native_listing_persistence) exist on top of it.
    assert read_alembic_version(scenario_url) == BASELINE_REVISION


def test_alembic_upgrade_head_from_baseline_adds_only_the_authorized_native_listings_table(
    scenario_url: str,
) -> None:
    """SLICE-0042's baseline revision itself remains schema-neutral, but
    `alembic upgrade head` from that baseline now also applies SLICE-0043's
    native_listing_persistence revision — which is expected to add exactly
    the one authorized `native_listings` table and nothing else."""
    result = prepare_alembic_baseline(scenario_url)
    assert result.outcome is BaselineOutcome.FRESH_BOOTSTRAPPED_AND_STAMPED

    conn = psycopg.connect(scenario_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = current_schema() ORDER BY table_name"
            )
            before = {row[0] for row in cur.fetchall()}
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
            after = {row[0] for row in cur.fetchall()}
    finally:
        conn.close()

    assert after - before == {"native_listings"}
    assert read_alembic_version(scenario_url) != BASELINE_REVISION
