"""Real PostgreSQL 18 proof for SLICE-0096 independent review Finding E:
`open_connection`'s optional `statement_timeout_ms` (`hullq.persistence.
connection`) actually binds an enforceable server-side deadline, composes
safely with an already-DSN-embedded `options` value (e.g. a test's own
`-c search_path=...` isolation -- the exact kind of value a bare `options=`
keyword passed straight to `psycopg.connect` would otherwise silently
discard), and -- directly mirroring a real leaked-connection/lock incident
observed during this slice's own review remediation -- that the connection
is fully, cleanly releasable after a cancelled statement, leaving no
orphaned backend/lock behind for a later request to block on.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any
from urllib.parse import quote

import psycopg
import pytest

from hullq.persistence.connection import open_connection


@pytest.fixture()
def admin_conn(db_url: str) -> Generator[Any]:
    conn = psycopg.connect(db_url, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


def test_statement_timeout_cancels_a_long_running_statement(db_url: str) -> None:
    conn = open_connection(db_url, statement_timeout_ms=200)
    try:
        with pytest.raises(psycopg.errors.QueryCanceled):
            conn.execute("SELECT pg_sleep(2)")
    finally:
        conn.rollback()
        conn.close()


def test_statement_timeout_composes_with_an_existing_dsn_embedded_options_value(
    db_url: str,
) -> None:
    schema_name = f"hullq_s0096conn_{uuid.uuid4().hex[:16]}"
    admin = psycopg.connect(db_url, autocommit=True)
    try:
        with admin.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema_name}"')

        option = quote(f"-c search_path={schema_name}", safe="")
        url_with_search_path = f"{db_url}?options={option}"

        conn = open_connection(url_with_search_path, statement_timeout_ms=5_000)
        try:
            # Both the caller's pre-existing `-c search_path=...` AND the
            # new `-c statement_timeout=...` must survive -- a bare
            # `options=` keyword naively passed to `psycopg.connect` would
            # instead silently replace the DSN's own `options` value and
            # lose the search_path isolation (verified empirically while
            # implementing this fix).
            with conn.cursor() as cur:
                cur.execute("SHOW search_path")
                (search_path,) = cur.fetchone()
                assert schema_name in search_path, (
                    f"expected {schema_name!r} in search_path, got {search_path!r} -- "
                    "the DSN-embedded options value was lost"
                )
                cur.execute("SHOW statement_timeout")
                (statement_timeout,) = cur.fetchone()
                assert statement_timeout == "5s", statement_timeout
        finally:
            conn.close()
    finally:
        with admin.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        admin.close()


def test_connection_is_cleanly_releasable_after_a_cancelled_statement(
    db_url: str, admin_conn: Any
) -> None:
    conn = open_connection(db_url, statement_timeout_ms=200)
    backend_pid = conn.info.backend_pid
    try:
        with pytest.raises(psycopg.errors.QueryCanceled):
            conn.execute("SELECT pg_sleep(2)")
    finally:
        # Mirrors `hullq.api.app`'s own except/finally around the bounded
        # page evaluators: roll back the aborted transaction, then close.
        conn.rollback()
        conn.close()

    with admin_conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_stat_activity WHERE pid = %(pid)s", {"pid": backend_pid})
        leaked = cur.fetchall()
    assert leaked == [], (
        f"backend pid {backend_pid} is still visible in pg_stat_activity after "
        "close() -- a cancelled statement must not leak a lingering/idle-in-"
        "transaction backend"
    )
