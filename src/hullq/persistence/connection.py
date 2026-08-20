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


def open_connection(url: str | None = None) -> Any:
    """Open and return a new psycopg Connection.

    If *url* is None, reads HULLQ_DATABASE_URL from the environment.
    The caller owns the returned connection and is responsible for closing it.
    """
    import psycopg  # deferred import — no module-level network side effect

    resolved = url if url is not None else get_database_url()
    return psycopg.connect(resolved)
