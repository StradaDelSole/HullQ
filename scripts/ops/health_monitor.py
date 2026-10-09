"""SLICE-0079 scheduled production health monitor + operator alert CLI.

Implements `docs/governance/PRODUCTION_READINESS_GATE.md` §3's "actionable
alert delivery for failures that require operator intervention" /
"no silent critical failure mode." Intended to run as a cron job on the
production host (`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §26: "scheduler/
cron where appropriate" -- no dedicated always-on monitoring daemon is
justified at this scale), one single check per invocation rather than a
long-running process: run `scripts/ops/smoke_check.py`'s checks, and if any
fail, POST an `AlertEvent` to the configured operator webhook
(`HULLQ_ALERT_WEBHOOK_URL`).

Exits 0 when every check passed, 1 when any check failed (regardless of
whether the alert itself could be delivered) and 2 when checks failed AND
the alert webhook delivery itself also failed -- distinguishing "the
service is down" from "the service is down AND the operator may not even
have been notified," which cron's own failure logging should still surface.

Run (typically from cron, e.g. every 5 minutes):
  uv run python scripts/ops/health_monitor.py --base-url https://api.hullq.com
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from hullq.observability.alerting import AlertDeliveryError, AlertEvent, send_alert

_ROOT = Path(__file__).resolve().parents[2]
# Direct script invocation (`uv run python scripts/ops/health_monitor.py`)
# puts only `scripts/ops/` itself on `sys.path`, not the repository root --
# mirrors the identical fix-up in `scripts/search_seed_corpus_wave1.py`.
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.ops.smoke_check import run_smoke_checks  # noqa: E402


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="e.g. https://api.hullq.com")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)

    checks = run_smoke_checks(args.base_url, timeout=args.timeout)
    failing = [check for check in checks if not check["ok"]]

    if not failing:
        print(json.dumps({"healthy": True, "checks": checks}))
        return 0

    failing_names = ", ".join(str(check["check"]) for check in failing)
    event = AlertEvent(
        severity="CRITICAL",
        source="health-monitor",
        message=f"{args.base_url} failed smoke checks: {failing_names}",
        occurred_at=datetime.now(UTC),
    )
    try:
        delivered = send_alert(event)
    except AlertDeliveryError as exc:
        print(
            json.dumps(
                {
                    "healthy": False,
                    "checks": checks,
                    "alert_delivered": False,
                    "alert_error": str(exc),
                }
            ),
            file=sys.stderr,
        )
        return 2

    print(json.dumps({"healthy": False, "checks": checks, "alert_delivered": delivered}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
