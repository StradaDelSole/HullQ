"""Ad-hoc check that the SLICE-0068 migration applies cleanly to a fresh
Alembic-baselined schema and that the expected tables/constraints exist.

Not a pytest test; a quick manual sanity script (mirrors the repository's
`scripts/inspect_*.py` convention). Reads `HULLQ_TEST_DATABASE_URL`.
"""

from __future__ import annotations

import os
import uuid
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg

from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline


def _with_search_path(base_url: str, schema_name: str) -> str:
    parts = urlsplit(base_url)
    option = quote(f"-c search_path={schema_name}", safe="")
    query = f"{parts.query}&options={option}" if parts.query else f"options={option}"
    return urlunsplit(parts._replace(query=query))


def main() -> None:
    base_url = os.environ["HULLQ_TEST_DATABASE_URL"]
    schema_name = f"hullq_s0068_migration_{uuid.uuid4().hex[:16]}"
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
    finally:
        conn.close()

    url = _with_search_path(base_url, schema_name)
    try:
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)

        check_conn = psycopg.connect(url)
        try:
            with check_conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_name IN "
                    "('media_assets', 'media_placements', 'native_listing_media_state') "
                    "ORDER BY table_name",
                    [schema_name],
                )
                tables = [row[0] for row in cur.fetchall()]
                print("tables:", tables)
                assert tables == [
                    "media_assets",
                    "media_placements",
                    "native_listing_media_state",
                ], tables

                cur.execute(
                    "SELECT conname FROM pg_constraint WHERE conrelid = %s::regclass",
                    [f'"{schema_name}".media_assets'],
                )
                print("media_assets constraints:", sorted(r[0] for r in cur.fetchall()))
        finally:
            check_conn.close()
        print("OK")
    finally:
        conn2 = psycopg.connect(base_url, autocommit=True)
        try:
            with conn2.cursor() as cur:
                cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        finally:
            conn2.close()


if __name__ == "__main__":
    main()
