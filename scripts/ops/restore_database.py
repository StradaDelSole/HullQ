"""SLICE-0079 production database restore CLI.

Downloads one encrypted backup object, decrypts it, and restores it via
`pg_restore` into the target database -- the tested-restore half of
`docs/governance/PRODUCTION_READINESS_GATE.md` §2. Intended for disaster
recovery (restoring the real production database after loss/corruption) and
for periodic restore-drill verification against a disposable target
(`docs/operations/PRODUCTION_BACKUP_RESTORE_RUNBOOK.md`) -- never run this
against a database you cannot afford to have `--clean`-dropped into unless
that is genuinely the recovery you intend.

Required environment:
  HULLQ_BACKUP_ENCRYPTION_KEY
  HULLQ_BACKUP_R2_ACCOUNT_ID
  HULLQ_BACKUP_R2_ACCESS_KEY_ID
  HULLQ_BACKUP_R2_SECRET_ACCESS_KEY
  HULLQ_BACKUP_R2_BUCKET

Run:
  uv run python scripts/ops/restore_database.py --object-key KEY [--target-database-url URL] [--no-clean]

*--target-database-url* defaults to `HULLQ_DATABASE_URL`. Prints one JSON
result line: {"object_key": ..., "restored_at": ...}
"""

from __future__ import annotations

import argparse
import json
import sys

from hullq.ops.backup_restore import (
    BackupError,
    get_backup_encryption_key,
    get_backup_r2_object_storage,
    restore_encrypted_backup,
)
from hullq.persistence.connection import get_database_url


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--object-key", required=True, help="backup object key to restore")
    parser.add_argument(
        "--target-database-url",
        default=None,
        help="restore target (default: HULLQ_DATABASE_URL)",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="skip --clean --if-exists (restore into an empty target only)",
    )
    args = parser.parse_args(argv)

    target_url = (
        args.target_database_url if args.target_database_url is not None else get_database_url()
    )

    try:
        encryption_key = get_backup_encryption_key()
        object_storage = get_backup_r2_object_storage()
        result = restore_encrypted_backup(
            target_url,
            encryption_key=encryption_key,
            object_storage=object_storage,
            object_key=args.object_key,
            clean=not args.no_clean,
        )
    except BackupError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    print(
        json.dumps({"object_key": result.object_key, "restored_at": result.restored_at.isoformat()})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
