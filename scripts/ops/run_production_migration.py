"""SLICE-0079 controlled production migration CLI.

Implements `docs/governance/PRODUCTION_READINESS_GATE.md` §8's "production
migration procedure is controlled and forward-compatible with the accepted
Alembic boundary."

`hullq.persistence.alembic_baseline.prepare_alembic_baseline` is a one-time
legacy-adoption step (SLICE-0042): it is only meaningful the very first time
a database is ever placed under Alembic control (a brand-new database, or
the historical pre-Alembic 001/002 schema) and deliberately rejects any
database that has already moved past the baseline revision through a
*normal* `alembic upgrade head` -- calling it again on every later release
would therefore reject the database's own expected forward progress rather
than protect it. This script runs it only when the target database has
never been stamped with an Alembic revision at all
(`read_alembic_version` returns `None`); every later release on an
already-baselined database skips straight to `alembic upgrade head`.

Reports the before/after schema version either way, so the deploy runbook
has a concrete value to compare if anything downstream fails.

Run:
  uv run python scripts/ops/run_production_migration.py
"""

from __future__ import annotations

import json
import sys

from hullq.persistence.alembic_baseline import (
    alembic_upgrade_head,
    prepare_alembic_baseline,
    read_alembic_version,
)
from hullq.persistence.connection import get_database_url


def main(argv: list[str]) -> int:
    del argv  # no arguments; the production database URL always comes from the environment
    database_url = get_database_url()

    version_before = read_alembic_version(database_url)
    if version_before is None:
        # Never-before-baselined database: the one-time legacy/fresh
        # reconciliation applies.
        baseline = prepare_alembic_baseline(database_url)
        if not baseline.accepted:
            print(
                json.dumps({"ok": False, "stage": "baseline_check", "reason": baseline.reason}),
                file=sys.stderr,
            )
            return 1
        baseline_outcome = baseline.outcome.value
        version_before = read_alembic_version(database_url)
    else:
        # Already under Alembic control from a prior release -- re-running
        # prepare_alembic_baseline here would incorrectly reject the
        # database's own expected forward progress (see module docstring).
        baseline_outcome = "ALREADY_BASELINED_PRIOR_RELEASE"

    try:
        alembic_upgrade_head(database_url)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "stage": "upgrade",
                    "version_before": version_before,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            ),
            file=sys.stderr,
        )
        return 1
    version_after = read_alembic_version(database_url)

    print(
        json.dumps(
            {
                "ok": True,
                "baseline_outcome": baseline_outcome,
                "version_before": version_before,
                "version_after": version_after,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
