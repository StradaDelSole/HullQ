"""SLICE-0079 production database backup CLI.

Dumps the production PostgreSQL database (or one named schema within it),
encrypts the dump with the configured Fernet key, and uploads it to the
backup-dedicated R2 bucket -- `docs/governance/PRODUCTION_READINESS_GATE.md`
§2 / `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §21.

Required environment:
  HULLQ_DATABASE_URL            -- the database to back up
  HULLQ_BACKUP_ENCRYPTION_KEY   -- Fernet key (see
                                    `docs/operations/PRODUCTION_BACKUP_RESTORE_RUNBOOK.md`
                                    for how to generate one)
  HULLQ_BACKUP_R2_ACCOUNT_ID
  HULLQ_BACKUP_R2_ACCESS_KEY_ID
  HULLQ_BACKUP_R2_SECRET_ACCESS_KEY
  HULLQ_BACKUP_R2_BUCKET

Run:
  uv run python scripts/ops/backup_database.py [--schema SCHEMA] [--object-key KEY]

Prints one JSON result line: {"object_key": ..., "size_bytes": ..., "created_at": ...}
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime

from hullq.ops.backup_restore import (
    BackupError,
    create_encrypted_backup,
    get_backup_encryption_key,
    get_backup_r2_object_storage,
)
from hullq.persistence.connection import get_database_url


def _default_object_key(schema: str | None) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    scope = schema if schema is not None else "full-database"
    return f"backups/{scope}/{stamp}.dump.enc"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schema",
        default=None,
        help="restrict the backup to one PostgreSQL schema (default: entire database)",
    )
    parser.add_argument(
        "--object-key",
        default=None,
        help="backup object key (default: backups/<schema-or-full-database>/<UTC timestamp>.dump.enc)",
    )
    args = parser.parse_args(argv)

    object_key = (
        args.object_key if args.object_key is not None else _default_object_key(args.schema)
    )

    try:
        database_url = get_database_url()
        encryption_key = get_backup_encryption_key()
        object_storage = get_backup_r2_object_storage()
        result = create_encrypted_backup(
            database_url,
            schema=args.schema,
            encryption_key=encryption_key,
            object_storage=object_storage,
            object_key=object_key,
        )
    except BackupError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "object_key": result.object_key,
                "size_bytes": result.size_bytes,
                "created_at": result.created_at.isoformat(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
