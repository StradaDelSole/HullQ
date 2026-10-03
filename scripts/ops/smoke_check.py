"""SLICE-0079 post-deploy/post-migration smoke check CLI.

Implements `docs/governance/PRODUCTION_READINESS_GATE.md` §8's "smoke/health
checks exist for the production paths actually being relied upon." Run this
immediately after every deploy and every migration
(`docs/operations/PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md`,
`docs/operations/PRODUCTION_RELEASE_MIGRATION_RUNBOOK.md`) before declaring
either one successful; a non-zero exit is the deploy/migration script's
rollback trigger.

Checks, in order (first failure stops and reports):
  1. GET /healthz  -> 200 (process is serving HTTP at all)
  2. GET /readyz   -> 200 (PostgreSQL is reachable)
  3. GET /api/search/en -> 200 (the real public Search route resolves)

Run:
  uv run python scripts/ops/smoke_check.py --base-url https://api.hullq.com
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx

_CHECKS: tuple[tuple[str, str], ...] = (
    ("liveness", "/healthz"),
    ("readiness", "/readyz"),
    ("public_search", "/api/search/en"),
)


def run_smoke_checks(base_url: str, *, timeout: float = 10.0) -> list[dict[str, object]]:
    """Run every check against *base_url*. Returns one result dict per check.

    Never raises for an individual check's HTTP failure -- every check's
    outcome (including a transport error) is captured in its result dict so
    the caller gets a complete report rather than stopping at the first
    failure.
    """
    results: list[dict[str, object]] = []
    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        for name, path in _CHECKS:
            try:
                response = client.get(path)
            except httpx.HTTPError as exc:
                results.append({"check": name, "path": path, "ok": False, "error": str(exc)})
                continue
            results.append(
                {
                    "check": name,
                    "path": path,
                    "ok": response.status_code == 200,
                    "status_code": response.status_code,
                }
            )
    return results


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="e.g. https://api.hullq.com")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)

    results = run_smoke_checks(args.base_url, timeout=args.timeout)
    all_ok = all(result["ok"] for result in results)
    print(json.dumps({"base_url": args.base_url, "all_ok": all_ok, "checks": results}, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
