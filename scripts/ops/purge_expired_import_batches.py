"""SLICE-0083 scheduled expired-import-batch purge CLI.

Enforces the "an unconfirmed staged batch is retained for 24 hours and
then purged automatically" retention guarantee
(`docs/broker-import-templates/README.md`) independently of any
Organization's own upload/list/view activity -- the application itself
only purges a given Organization's own expired batches opportunistically
on that Organization's *next* upload
(`hullq.application.import_intake.upload_import_for_organization`),
which never fires for an Organization that simply stops uploading, so
that path alone cannot be the real guarantee (independent review
amendment Finding 3).

This script is the real, independent mechanism: intended to run as a
cron job on the production host (mirrors `scripts/ops/health_monitor.py`'s
identical "no dedicated always-on daemon justified at this scale"
scheduling discipline), one purge sweep per invocation across every
Organization via `hullq.persistence.import_intake.
purge_all_expired_unconfirmed_batches`. Eligibility is unchanged from the
per-Organization fast path: only `AWAITING_MAPPING`/`MAPPED` batches past
their `expires_at` are deleted; a `CONFIRMING` batch (possible partial
progress from a crashed/interrupted confirm call) and every `CONFIRMED`
batch (retained indefinitely as auditable import provenance) are never
touched.

Required environment:
  HULLQ_DATABASE_URL -- the database to sweep

Run (typically from cron, e.g. hourly):
  uv run python scripts/ops/purge_expired_import_batches.py

Prints one JSON result line: {"purged_batches": <int>}
"""

from __future__ import annotations

import json

from hullq.persistence.connection import open_connection
from hullq.persistence.import_intake import purge_all_expired_unconfirmed_batches


def main() -> int:
    conn = open_connection()
    try:
        with conn.transaction():
            purged = purge_all_expired_unconfirmed_batches(conn)
    finally:
        conn.close()
    print(json.dumps({"purged_batches": purged}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
