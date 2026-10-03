# Production Readiness Gate Evidence — 2026-10 (SLICE-0079)

**Status:** `PRODUCTION_READINESS_GATE_STATUS` recommendation: **remains `IN_PROGRESS`**, not `PASS`. This slice builds, and locally proves against real (non-production) resources, every mechanism the gate requires. It does **not** claim `PASS` because three concrete, named gaps remain that genuinely require the Project Owner's production credentials/infrastructure decisions (§9) rather than anything this slice could fabricate or work around. This is the honest outcome `CLAUDE.md`'s stop-condition discipline requires: *"production credentials/provider access required for a mandatory proof are unavailable"* → do not invent a PASS.

**This slice does not start the pilot, store real external production data, or expose anything publicly.** `EXTERNAL_BROKER_PRODUCTION_DATA_STATUS`, `EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS` remain `NOT_PRESENT`; `PRODUCTION_PILOT_STATUS`, `PUBLIC_PRODUCTION_LAUNCH_STATUS` remain `NOT_STARTED`.

**Required outputs this document completes:**

```text
docs/validation/PRODUCTION_READINESS_EVIDENCE_2026-10.md       (this file)
docs/operations/PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md
docs/operations/PRODUCTION_BACKUP_RESTORE_RUNBOOK.md
docs/operations/PRODUCTION_RELEASE_MIGRATION_RUNBOOK.md
docs/operations/PRODUCTION_INCIDENT_OBSERVABILITY_RUNBOOK.md
docs/operations/production.env.example
```

## 1. Controlled deployment and rollback — `docs/governance/PRODUCTION_READINESS_GATE.md` §1

| Requirement | Artifact | Proof | Result | Residual |
|---|---|---|---|---|
| CI-verified immutable Docker images | `Dockerfile`, `web/Dockerfile`, `.github/workflows/deploy.yml` | Both images built locally via the real Docker Engine from the exact repository Dockerfiles; see `PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md` §5 for the full command transcript | **PROVEN locally** | `push_to_ghcr` job has not yet run on a real GitHub Actions `push` to `main` — first real exact-head observation happens post-merge |
| Images stored in GHCR, versioned | `.github/workflows/deploy.yml` (`push_to_ghcr` job, tag = `sha-<commit>`, never `latest`) | Workflow YAML reviewed; uses `secrets.GITHUB_TOKEN` (no extra secret needed for same-repo GHCR push) | **MECHANISM PROVEN, NOT YET OBSERVED** | needs a real `push` to `main` to actually populate GHCR — **BLOCKING item for full gate PASS (§9.1)** |
| Rollback to previous known-good image/configuration is documented and tested | `scripts/ops/deploy.sh`, `scripts/ops/rollback.sh`, `docker-compose.prod.yml` | Full deploy→new-deploy→rollback drill executed against the real Docker Engine: tag A healthy → tag B (distinct image digest) healthy → rollback to tag A (byte-identical digest confirmed) healthy again | **PROVEN locally** (mechanism; the scripts' own `docker compose pull` step needs real GHCR network access not available in this sandbox — see runbook §5) | first real VPS execution is operational (§9.2) |
| Application hosts stateless/replaceable | `Dockerfile`/`web/Dockerfile` (no local volume for app data); `docker-compose.prod.yml` (no app-data volume; Caddy's `caddy_data`/`caddy_config` volumes hold only TLS state, trivially reissuable) | Reviewed; both images read all configuration from the environment and persist nothing to local disk | **PROVEN by construction** | none |

## 2. Database availability and recoverability — gate §2

| Requirement | Artifact | Proof | Result | Residual |
|---|---|---|---|---|
| Explicit RTO/RPO | `PRODUCTION_BACKUP_RESTORE_RUNBOOK.md` §2 | RPO 24h (daily backup + provider PITR), RTO 2h (solo-operator conservative upper bound) | **DOCUMENTED** | real RTO measurement against production-sized data is a later operational task |
| Automated provider backup | DigitalOcean Managed PostgreSQL's own continuous WAL/PITR backup (provider feature, not HullQ code) | n/a — provider capability, assumed available per `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §19/§21 | **ASSUMED PER ACCEPTED ARCHITECTURE, NOT PROVISIONED** | no real DO Managed PostgreSQL instance exists yet — **BLOCKING item (§9.3)** |
| Independent encrypted off-provider backup | `src/hullq/ops/backup_restore.py` (`create_encrypted_backup`/`restore_encrypted_backup`, Fernet + `ObjectStorage`) | `tests/persistence/test_backup_restore_disposable_proof.py` — real `pg_dump`/`pg_restore` 18.6, real local PostgreSQL 18, real Fernet encryption | **PROVEN against disposable resources** | real R2 backup bucket not provisioned — mechanism is provider-agnostic (`ObjectStorage` boundary), only credentials are missing |
| Tested restore proving recoverability (not backup existence alone) | same test file | Backup → **genuinely destroy** the schema (`DROP SCHEMA ... CASCADE`) → restore → exact original rows recovered; a second test proves a wrong decryption key is rejected (`BackupError`), never silently returning corrupt data | **PROVEN**: 2/2 tests pass | none at the mechanism level |
| Documented recovery runbook for a solo operator | `PRODUCTION_BACKUP_RESTORE_RUNBOOK.md` | reviewed | **DOCUMENTED** | none |
| PostgreSQL HA state + hard buyer-exposure trigger | `PRODUCTION_BACKUP_RESTORE_RUNBOOK.md` §3 | explicit marker: `POSTGRESQL_HA_STATUS = NOT_ACTIVE` with the retained hard rule `NO REAL EXTERNAL BUYER EXPOSURE UNTIL HA REQUIREMENT IS SATISFIED` | **EXPLICITLY RECORDED, NOT ACTIVE** | HA activation is a real DigitalOcean provisioning decision/cost — required before any real buyer exposure, independent of this gate |

## 3. Production observability and actionable alerting — gate §3

| Requirement | Artifact | Proof | Result | Residual |
|---|---|---|---|---|
| Structured application logs | `src/hullq/observability/logging_config.py`; wired into `src/hullq/api/app.py`'s `_structured_access_logging` middleware | `tests/unit/test_observability_logging_config.py` (9 tests) + live containerized-API run emitting real JSON lines to stdout during the deploy drill | **PROVEN** | none |
| Exception capture for web/API paths | `src/hullq/api/app.py`'s `_handle_unexpected_exception` (`@app.exception_handler(Exception)`) | `tests/persistence/test_production_readiness_health_api.py::test_unhandled_exception_is_captured_and_never_leaks_detail` — a real monkeypatched exception through the real route, asserting the HTTP response never contains the exception type/message | **PROVEN** | none |
| Service/database/dependency health visibility | `GET /healthz`, `GET /readyz` (`src/hullq/api/app.py`) | Proven three ways: (1) unit/integration tests, (2) real `curl` against a real containerized instance during the deploy drill, (3) the real Docker `HEALTHCHECK` directive itself reporting `healthy` via `docker inspect` | **PROVEN** | none |
| Actionable alert delivery | `src/hullq/observability/alerting.py` (`send_alert`), `scripts/ops/health_monitor.py` | `tests/unit/test_observability_alerting.py` (8 tests: payload shape, success, non-2xx, transport failure, unconfigured no-op) | **MECHANISM PROVEN** | no real Slack/Discord webhook URL available in this sandbox — real delivery is a one-time operational step once `HULLQ_ALERT_WEBHOOK_URL` is configured |
| No silent critical failure mode | `scripts/ops/health_monitor.py` exit-code contract (0/1/2, see `PRODUCTION_INCIDENT_OBSERVABILITY_RUNBOOK.md` §3) | reviewed; cron + exit code 2 distinguishes "service down" from "service down AND alert also failed" | **DESIGNED AND UNIT-TESTED** | real cron deployment is operational |

## 4. Edge abuse / bot protection — gate §4

| Requirement | Result | Residual |
|---|---|---|
| Cloudflare (or superseding) edge boundary configured | **NOT YET APPLICABLE** — no public ingress exists yet (no VPS, no DNS pointed at one). `Caddyfile` is written for the accepted Cloudflare Full (strict) + Origin-CA-certificate topology (`docs/engineering/APPLICATION_STACK_BASELINE.v0.1.md`), reviewed but not deployed. | mandatory before pilot/public exposure, per gate text's explicit allowance for a strictly-internal phase |
| Practical rate/abuse controls on costly/sensitive endpoints | **ALREADY IMPLEMENTED by SLICE-0078** (`FixedWindowRateLimiter` on login/contact/media-upload — unchanged by this slice) | public Search itself still has no explicit rate limiter; acceptable while there is no public ingress, re-evaluate before pilot |
| Owner-direct endpoints anti-abuse/rate controls | **ALREADY IMPLEMENTED by SLICE-0078** (unchanged) | n/a |

This section is validly `NOT_YET_APPLICABLE` under the gate's own text: *"For a strictly internal real-data phase with no public ingress, external abuse controls may be evidenced as not-yet-applicable, but they become mandatory before pilot/public exposure."*

## 5. Secrets and privileged access — gate §5

| Requirement | Artifact | Proof | Result |
|---|---|---|---|
| No production secret committed | `docs/operations/production.env.example` (names only), `.gitignore` (`.env`/`.env.*` already excluded pre-existing) | reviewed; grepped this slice's diff for credential-shaped literals — none found | **VERIFIED** |
| Defined storage/rotation for deploy/DB/Auth0/backup credentials | `PRODUCTION_INCIDENT_OBSERVABILITY_RUNBOOK.md` §4 | reviewed | **DOCUMENTED** |
| Least-privilege roles | GHCR token scoped `read:packages` on the VPS; `packages: write` scoped only to the `push_to_ghcr` job (not the whole workflow); backup R2 credentials separate bucket/role from media R2 and from the application DB role | reviewed | **DESIGNED** |
| Auditable privileged operational actions | every ops script (`backup_database.py`, `restore_database.py`, `run_production_migration.py`, `deploy.sh`, `rollback.sh`, `health_monitor.py`) prints one structured JSON result line and uses a distinct non-zero exit code per failure mode | real executions during this slice's proof work (§1-§3 above) produced exactly this JSON output each time | **PROVEN** |

## 6. Authentication / authorization / seller trust controls — gate §6

Unchanged by this slice. Already implemented by SLICE-0053 (broker Auth0/session/MFA boundary) and SLICE-0054 (owner-direct draft path), both still `IMPLEMENTED` per `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md` MVP-BROKER-001. Real broker/owner-direct authentication is not newly exposed by this slice.

## 7. Media durability and rights — gate §7

**`NOT_APPLICABLE` with evidence**: no real external production data (and therefore no real seller/broker media) exists or is introduced by this slice. `hullq.storage.object_storage` (SLICE-0068) already implements the quarantine/validation/re-encode boundary this item would require once media enters production; this slice adds no change to that path.

## 8. Release / production-data verification — gate §8

| Requirement | Artifact | Proof | Result |
|---|---|---|---|
| Controlled, forward-compatible migration procedure | `scripts/ops/run_production_migration.py`, `src/hullq/persistence/alembic_baseline.py` (SLICE-0042, unchanged) | Real CLI execution against the real local PostgreSQL 18 database at an intermediate revision (the genuine "incremental release" case, not a fresh DB): `{"ok": true, "baseline_outcome": "ALREADY_BASELINED_PRIOR_RELEASE", "version_before": "8b6d3f0a2c17", "version_after": "a2e7c0f5b931"}` — see `PRODUCTION_RELEASE_MIGRATION_RUNBOOK.md` §5 | **PROVEN**; this run also caught and fixed a real defect in this slice's first draft of the script (see runbook §5) |
| Smoke/health checks for relied-upon production paths | `scripts/ops/smoke_check.py` | Real CLI execution against a real locally-running `uvicorn` process: `{"all_ok": true, "checks": [...3 checks, all 200...]}` | **PROVEN** |
| Rollback/recovery named operator path | §1/§2 above | — | **PROVEN** (mechanism) |
| No undocumented local-machine dependency | `PRODUCTION_RELEASE_MIGRATION_RUNBOOK.md` §4 | every step runs from either a GitHub Actions runner or the VPS's own `uv`-managed ops checkout | **DESIGNED** |
| Internal-vs-external-exposure distinction explicit | this document's header + §4 | — | **EXPLICIT** |
| PASS record names which supply paths are covered | this document covers the professional-broker boundary only (owner-direct publication remains separately `PENDING` per `OVERALL_MVP_CAPABILITY_REGISTER.md` MVP-OWNER-002 and is not newly exposed by this slice) | — | **NAMED** |

## 9. Why the gate is not `PASS` — the exact residual list

Three items require Project-Owner-level production access/decisions this
slice cannot fabricate (`CLAUDE.md` stop condition: *"production
credentials/provider access required for a mandatory proof are
unavailable"*):

1. **No real GHCR push has been observed.** `push_to_ghcr` in
   `.github/workflows/deploy.yml` runs on `push: branches: [main]` —
   it has not fired yet because this slice has not merged. The first
   exact-head CI run after merge is the real observation.
2. **No real production VPS exists.** `scripts/ops/deploy.sh`/`rollback.sh`
   and the Cloudflare Origin CA certificate setup in
   `PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md` §2 are written and locally
   drilled against the real Docker Engine, but have never run against a
   real host.
3. **No real DigitalOcean Managed PostgreSQL instance exists.** HA state
   is honestly recorded as `NOT_ACTIVE` (§2); this is explicitly allowed
   for a strictly-internal phase by the gate's own text, but it means
   "production PostgreSQL target/configuration evidence" is currently a
   design + locally-proven-mechanism, not an actually-provisioned target.

None of these three can be satisfied inside this slice's sandbox without
either fabricating a provider relationship (forbidden by the slice's
explicit "pretending a provider capability exists when it has not been
configured/tested" out-of-scope item) or taking an action
(provisioning real paid infrastructure, or triggering a real GHCR package
publish under the project's namespace) that is the Project Owner's call,
not this agent's. Every mechanism the gate requires is built, reviewed and
proven against real (non-production) resources everywhere that was
possible in this sandbox; the remaining gap is provisioning, not
engineering.

## 10. `MVP-PROD-012` stale-marker reconciliation

`docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md` already correctly
states `MVP-PROD-012 | ... | IMPLEMENTED by SLICE-0078 — gate PASS;
SEC-0078-07 Owner-risk-accepted with retained re-review triggers` — this
was already current as of the 2026-10-03 reassessment this slice's own
readiness reconciliation cites. No further edit was required for that row
specifically; the slice-doc's "stale MVP-PROD-012 DUE marker" reference
describes the state this register already reconciled before SLICE-0079
began. This document and the companion register update (§ below) instead
move the other `MVP-PROD-*` rows from `PENDING`/`PENDING/PARTIAL` to
`PARTIAL` with a pointer to this evidence, reflecting the real work done.
