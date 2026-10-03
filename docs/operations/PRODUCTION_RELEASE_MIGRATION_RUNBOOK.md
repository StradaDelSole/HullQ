# Production Release / Migration Runbook — SLICE-0079

**Status:** operational runbook, required output of SLICE-0079.
**Controlling gate:** `docs/governance/PRODUCTION_READINESS_GATE.md` §8.

## 1. Release sequence

A release is always: **migrate, then deploy** — never the reverse, and
never simultaneous. This keeps the expand/migrate/contract discipline
(`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §25) honest: at every point
during a rollout, the currently-running application image (old or new)
must be compatible with the currently-applied schema.

```text
1. uv run python scripts/ops/run_production_migration.py   (this runbook, §2)
2. uv run python scripts/ops/smoke_check.py --base-url <...>  (confirms the
   PRE-deploy application image is still healthy against the migrated schema)
3. .github/workflows/deploy.yml's `deploy` job -> scripts/ops/deploy.sh <tag>
   (docs/operations/PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md)
4. scripts/ops/smoke_check.py again                          (confirms the
   POST-deploy application image against the same migrated schema)
```

If step 2 fails, stop — do not deploy a new image against a schema the
*current* image cannot also still serve; this is the expand/migrate/contract
rule turned into a concrete gate rather than prose.

## 2. Running a migration

```bash
cd /opt/hullq-ops
uv run python scripts/ops/run_production_migration.py
```

`scripts/ops/run_production_migration.py` wraps the same
`hullq.persistence.alembic_baseline.prepare_alembic_baseline` safety check
the test suite's own migration fixtures use: it refuses (exits non-zero,
runs nothing) if the target database is in an unexpected legacy/pre-Alembic
state rather than guessing what to do. On success it reports the exact
`version_before` / `version_after` Alembic revision, which is the manual
rollback target if a later step in the release fails (`alembic downgrade
<version_before>` — only for schema changes the migration's own `downgrade()`
implements; not every migration is safely reversible, which is exactly why
step 1→2 above gates the *forward* migration on smoke-passing before any
code deploy proceeds, rather than relying on being able to downgrade later).

## 3. Smoke checks

```bash
uv run python scripts/ops/smoke_check.py --base-url https://hullq.com
```

Checks, in order: `GET /healthz` (process serving HTTP), `GET /readyz`
(PostgreSQL reachable), `GET /api/search/en` (the real public Search route
resolves end-to-end). Exit code is non-zero if any check fails; both the
migration sequence (§1) and `.github/workflows/deploy.yml`'s `deploy` job
use this exit code as their go/no-go signal.

## 4. No undocumented local-machine dependency

Every step above runs from either (a) the GitHub Actions runner (build/push/
smoke-check-over-HTTP) or (b) the VPS's own `uv`-managed ops checkout
(migration, backup/restore, health-monitor) — never from an engineer's
personal machine. The ops checkout is itself just `git clone` + `uv sync`
of this repository; rebuilding it from scratch requires nothing beyond the
repository and the `.env` file described in
`docs/operations/production.env.example`.

## 5. Executable proof performed for this slice (2026-10-03)

`scripts/ops/run_production_migration.py` reuses
`hullq.persistence.alembic_baseline.{prepare_alembic_baseline,
alembic_upgrade_head, read_alembic_version}`, which is exercised by every
one of this repository's existing `tests/persistence/test_*_api.py` fixture
setups (each creates a disposable schema and calls exactly this path before
running its own test) — hundreds of real executions against the real local
PostgreSQL 18 test database, including by the two new test files this slice
adds (`test_production_readiness_health_api.py`,
`test_backup_restore_disposable_proof.py`). `scripts/ops/smoke_check.py` was
exercised directly against a real containerized API instance during the
deploy/rollback drill (`PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md` §5) via its
underlying `run_smoke_checks` function's exact HTTP calls (`curl` was used
interactively there; the Python CLI wraps the identical three checks).
Both CLIs were also executed directly (not just their underlying library
calls) for this slice:

```text
$ uv run python scripts/ops/run_production_migration.py   (HULLQ_DATABASE_URL
  pointed at the real local PostgreSQL 18 test database, already sitting at
  an intermediate revision from prior test runs -- the real "incremental
  release" case, not a fresh database)
{"ok": true, "baseline_outcome": "ALREADY_BASELINED_PRIOR_RELEASE",
 "version_before": "8b6d3f0a2c17", "version_after": "a2e7c0f5b931"}

$ uv run python scripts/ops/smoke_check.py --base-url http://127.0.0.1:18099
  (against a real locally-running `uvicorn hullq.api.app:create_app` process)
{"base_url": "...", "all_ok": true, "checks": [
  {"check": "liveness", "ok": true, "status_code": 200},
  {"check": "readiness", "ok": true, "status_code": 200},
  {"check": "public_search", "ok": true, "status_code": 200}]}
```

This run of `run_production_migration.py` also caught and fixed a real
defect in this slice's first draft: the script originally called
`prepare_alembic_baseline` unconditionally on every run, but that function
is a one-time legacy-adoption check (SLICE-0042) that correctly *rejects*
a database already past the baseline revision through normal
`alembic upgrade head` progress -- exactly the state every second-and-later
release is in. The fix (only call it when `read_alembic_version` returns
`None`, i.e. the database has never been Alembic-stamped at all) is what
the command above actually exercised.
