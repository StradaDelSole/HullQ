"""SLICE-0042 Alembic migration baseline owner-inspection.

Executes real PostgreSQL/Alembic behavior against disposable schemas to
demonstrate the safe adoption states required by SLICE-0042: fresh-bootstrap
adoption, existing-legacy-database adoption (with data preservation),
idempotent re-adoption, fail-closed rejection of an unsafe/partial state, the
frozen-legacy-migration guard, and standard `alembic current` / `upgrade
head` compatibility.

Run: uv run python scripts/inspect_alembic_migration_baseline.py

Requires HULLQ_TEST_DATABASE_URL to point at a local PostgreSQL 18 instance.
Each scenario below runs against its own freshly created/dropped disposable
PostgreSQL *schema* (isolated via the connection ``options=-c
search_path=...`` parameter) so that mutually exclusive database states
(empty / accepted-legacy / already-baselined / partial-unsafe) never share
a schema. Schema-level isolation is used instead of ``CREATE DATABASE`` so
this script only needs ordinary ``CREATE`` privilege on the target
database, not a CREATEDB-privileged role.
"""

from __future__ import annotations

import sys
import uuid
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
from psycopg.types.json import Jsonb

from hullq.persistence.alembic_baseline import (
    BASELINE_REVISION,
    BaselineOutcome,
    UnexpectedLegacyMigrationError,
    alembic_heads,
    alembic_upgrade_head,
    guard_no_post_002_legacy_migrations,
    prepare_alembic_baseline,
    read_alembic_version,
)
from hullq.persistence.connection import HULLQ_TEST_DATABASE_URL_ENV
from hullq.persistence.migrations import MIGRATIONS_DIR, MIGRATIONS_TABLE, apply_migrations


def _base_url() -> str:
    import os

    url = os.environ.get(HULLQ_TEST_DATABASE_URL_ENV, "").strip()
    if not url:
        print(
            f"{HULLQ_TEST_DATABASE_URL_ENV} is not set. Point it at a disposable "
            "local PostgreSQL 18 instance, e.g.\n"
            f'  {HULLQ_TEST_DATABASE_URL_ENV}="postgresql://hullq_test:hullq_test@localhost:5432/hullq_test"',
            file=sys.stderr,
        )
        raise SystemExit(1)
    return url


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


def _new_scenario_url(base_url: str, label: str) -> tuple[str, str]:
    schema_name = f"hullq_s0042_{label}_{uuid.uuid4().hex[:10]}"
    _create_schema(base_url, schema_name)
    return _with_search_path(base_url, schema_name), schema_name


def scenario_fresh(base_url: str) -> bool:
    url, schema_name = _new_scenario_url(base_url, "fresh")
    try:
        result = prepare_alembic_baseline(url)
        current = read_alembic_version(url)
        ok = (
            result.outcome is BaselineOutcome.FRESH_BOOTSTRAPPED_AND_STAMPED
            and current == BASELINE_REVISION
        )
        print("fresh database")
        print(f"  -> legacy 001/002 bootstrap: {result.outcome.value}")
        print(f"  -> alembic_version: {current}")
        return ok
    finally:
        _drop_schema(base_url, schema_name)


def scenario_existing_legacy(base_url: str) -> bool:
    url, schema_name = _new_scenario_url(base_url, "legacy")
    try:
        conn = psycopg.connect(url)
        try:
            apply_migrations(conn)
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO research_bundles "
                    "(bundle_id, bundle_version, content_hash, research_target) "
                    "VALUES (%s, %s, %s, %s)",
                    [
                        "S0042-OWNER-PROBE",
                        "v1",
                        "ownerprobehash0042",
                        Jsonb({"manufacturer": "Probe", "model": "Boat", "first_built": None}),
                    ],
                )
            conn.commit()
        finally:
            conn.close()

        result = prepare_alembic_baseline(url)

        conn = psycopg.connect(url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT content_hash FROM research_bundles WHERE bundle_id = %s",
                    ["S0042-OWNER-PROBE"],
                )
                row = cur.fetchone()
        finally:
            conn.close()

        data_preserved = row is not None and row[0] == "ownerprobehash0042"
        ok = result.outcome is BaselineOutcome.LEGACY_VERIFIED_AND_STAMPED and data_preserved
        print("existing accepted legacy database")
        print(f"  -> legacy state: {result.outcome.value}")
        print(f"  -> existing data preserved: {data_preserved}")
        return ok
    finally:
        _drop_schema(base_url, schema_name)


def scenario_already_baselined(base_url: str) -> bool:
    url, schema_name = _new_scenario_url(base_url, "idem")
    try:
        first = prepare_alembic_baseline(url)
        second = prepare_alembic_baseline(url)
        ok = (
            first.outcome is BaselineOutcome.FRESH_BOOTSTRAPPED_AND_STAMPED
            and second.outcome is BaselineOutcome.ALREADY_BASELINED
        )
        print("already-baselined database")
        print(f"  -> re-run outcome: {second.outcome.value}")
        return ok
    finally:
        _drop_schema(base_url, schema_name)


def scenario_unsafe_partial(base_url: str) -> bool:
    url, schema_name = _new_scenario_url(base_url, "unsafe")
    try:
        conn = psycopg.connect(url)
        try:
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
                    f"INSERT INTO {MIGRATIONS_TABLE} (migration_id) VALUES (%s)",
                    ["001_initial_schema"],
                )
            conn.commit()
        finally:
            conn.close()

        result = prepare_alembic_baseline(url)
        current = read_alembic_version(url)
        ok = result.outcome is BaselineOutcome.REJECTED_UNSAFE_STATE and current is None
        print("unsafe/partial legacy state (only 001 applied)")
        print(f"  -> outcome: {result.outcome.value}")
        print(f"  -> reason: {result.reason}")
        print(f"  -> not stamped: {current is None}")
        return ok
    finally:
        _drop_schema(base_url, schema_name)


def scenario_legacy_guard() -> bool:
    try:
        guard_no_post_002_legacy_migrations()
    except UnexpectedLegacyMigrationError as exc:
        print("legacy post-002 migration guard")
        print(f"  -> FAIL: {exc}")
        return False
    print("legacy post-002 migration guard")
    print("  -> PASS: no post-002 legacy SQL migration file present")
    return True


def scenario_alembic_command_compatibility(base_url: str) -> bool:
    url, schema_name = _new_scenario_url(base_url, "cmd")
    try:
        result = prepare_alembic_baseline(url)
        heads = alembic_heads(url)
        current = read_alembic_version(url)

        conn = psycopg.connect(url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = current_schema() ORDER BY table_name"
                )
                before = [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

        alembic_upgrade_head(url)

        conn = psycopg.connect(url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = current_schema() ORDER BY table_name"
                )
                after = [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

        no_schema_change = after == before
        current_matches = current == BASELINE_REVISION and heads == [BASELINE_REVISION]
        ok = (
            result.outcome is BaselineOutcome.FRESH_BOOTSTRAPPED_AND_STAMPED
            and current_matches
            and no_schema_change
        )
        print(f"alembic current == expected baseline: {current == BASELINE_REVISION} ({current})")
        print(f"alembic heads == [baseline]: {heads == [BASELINE_REVISION]} ({heads})")
        print(f"alembic upgrade head == no application-schema change: {no_schema_change}")
        return ok
    finally:
        _drop_schema(base_url, schema_name)


def main() -> int:
    base_url = _base_url()

    print("ALEMBIC MIGRATION BASELINE\n")

    checks = {
        "fresh database": scenario_fresh(base_url),
        "existing accepted legacy database": scenario_existing_legacy(base_url),
        "already-baselined database": scenario_already_baselined(base_url),
        "unsafe/partial legacy state": scenario_unsafe_partial(base_url),
        "legacy post-002 migration guard": scenario_legacy_guard(),
        "alembic command compatibility": scenario_alembic_command_compatibility(base_url),
    }

    print()
    all_ok = all(checks.values())
    print(f"MIGRATION BASELINE RESULT: {'PASS' if all_ok else 'FAIL'}")

    if not all_ok:
        failed = [name for name, ok in checks.items() if not ok]
        print(f"\nFailed scenarios: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
