"""Lightweight SQL migration runner — SLICE-0013.

Applies numbered .sql files from the bundled sql/ directory in lexicographic
order. Applied migration IDs are tracked in a hullq_schema_migrations table
created on first use. Migrations are transactional: each migration runs
atomically and is recorded in the same transaction.

No external migration framework dependency. Idempotent: already-applied
migrations are skipped. Does not delete or reorder applied migrations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

MIGRATIONS_DIR = Path(__file__).parent / "sql"
MIGRATIONS_TABLE = "hullq_schema_migrations"

_CREATE_TRACKING_TABLE = f"""
CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
    migration_id TEXT        PRIMARY KEY,
    applied_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


def list_migration_files(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    """Return SQL migration file paths sorted lexicographically."""
    return sorted(directory.glob("*.sql"))


def apply_migrations(conn: Any, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply any unapplied migrations from *directory*.

    Returns the list of migration IDs that were applied in this call (empty if
    all were already applied). Each migration is applied in its own transaction
    together with the tracking-table INSERT so the two are always atomic.

    *conn* must be a psycopg Connection opened with autocommit=False (default).
    The caller retains ownership of the connection.
    """
    applied: list[str] = []

    # Ensure the tracking table exists (idempotent DDL).
    with conn.cursor() as cur:
        cur.execute(_CREATE_TRACKING_TABLE)
    conn.commit()

    for path in list_migration_files(directory):
        migration_id = path.stem

        # Check whether this migration has already been applied.
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT 1 FROM {MIGRATIONS_TABLE} WHERE migration_id = %s",
                [migration_id],
            )
            already_applied = cur.fetchone() is not None
        conn.commit()

        if already_applied:
            continue

        sql = path.read_text(encoding="utf-8")
        with conn.cursor() as cur:
            cur.execute(sql)
            cur.execute(
                f"INSERT INTO {MIGRATIONS_TABLE} (migration_id) VALUES (%s)",
                [migration_id],
            )
        conn.commit()
        applied.append(migration_id)

    return applied
