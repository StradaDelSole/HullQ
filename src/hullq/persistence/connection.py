"""Environment-driven database connection configuration — SLICE-0013.

No module-level connection. Importing this module does not open any network
connection. Connection creation is always explicit.
"""

from __future__ import annotations

import os
from typing import Any

HULLQ_DATABASE_URL_ENV = "HULLQ_DATABASE_URL"
HULLQ_TEST_DATABASE_URL_ENV = "HULLQ_TEST_DATABASE_URL"


def get_database_url(env_var: str = HULLQ_DATABASE_URL_ENV) -> str:
    """Return the database URL from the environment.

    Raises RuntimeError if the variable is not set or is empty.
    """
    url = os.environ.get(env_var, "").strip()
    if not url:
        raise RuntimeError(
            f"Environment variable {env_var!r} is not set or empty. "
            "Set it to a libpq-compatible connection string, e.g. "
            "'postgresql://user:pass@host:5432/dbname'."
        )
    return url


def open_connection(url: str | None = None, *, statement_timeout_ms: int | None = None) -> Any:
    """Open and return a new psycopg Connection.

    If *url* is None, reads HULLQ_DATABASE_URL from the environment.
    The caller owns the returned connection and is responsible for closing it.

    *statement_timeout_ms*, when given, binds a server-side
    ``statement_timeout`` (SLICE-0096 Finding E) to this connection only --
    every other caller omitting it keeps the prior unbounded behavior
    unchanged. A statement that runs past the deadline is aborted by
    PostgreSQL itself (``psycopg.errors.QueryCanceled``); the connection
    remains open but its current transaction is aborted, so the caller must
    still close/release it the same way any other failure path would.
    """
    import psycopg  # deferred import — no module-level network side effect

    resolved = url if url is not None else get_database_url()
    if statement_timeout_ms is None:
        return psycopg.connect(resolved)

    # A bare `options=...` keyword passed to `psycopg.connect` REPLACES --
    # rather than merges with -- any `options` already embedded in the DSN
    # (e.g. a test's own `-c search_path=...` isolation). Parsing the
    # existing value first and appending the new `-c` directive to it keeps
    # any such caller-supplied option intact instead of silently discarding
    # it.
    existing_options = psycopg.conninfo.conninfo_to_dict(resolved).get("options", "")
    combined_options = (
        f"{existing_options} -c statement_timeout={statement_timeout_ms}"
        if existing_options
        else f"-c statement_timeout={statement_timeout_ms}"
    )
    return psycopg.connect(resolved, options=combined_options)
