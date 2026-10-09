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
| CI-verified immutable Docker images | `Dockerfile`, `web/Dockerfile`, `.github/workflows/deploy.yml` | The real production `Dockerfile` was built live via the real Docker Engine as part of the §below lifecycle proof (2026-10-08); `web/Dockerfile` builds in CI. Independent-review Finding H (closed) added the exact-SHA prerequisite-check gate before publication. Post-merge canonical-main Deploy run #28 / run id `37868264887` at SHA `5532cd2cc13d9e2ce8bcee90cfc7f0591f14ae9a` then executed that gate for real and it completed SUCCESS before both image-publish jobs | **PROVEN locally + OBSERVED on real GitHub Actions main push** | real production VPS pull/deploy remains unobserved |
| Images stored in GHCR, versioned | `.github/workflows/deploy.yml` (`push_api_to_ghcr`/`push_web_to_ghcr` jobs, tag = `sha-<commit>` for human readability, never `latest`) | Workflow YAML reviewed; uses `secrets.GITHUB_TOKEN` for same-repo GHCR publication. Independent-review Finding O (closed) canonicalizes the mixed-case GitHub owner to one lowercase GHCR namespace. Canonical-main Deploy run #28 / `37868264887` real-executed GHCR login, durable-identity lookup, API build/push, web build/push and post-push digest resolution; both publish jobs completed SUCCESS | **OBSERVED on real GHCR publication path** | production VPS pull/deploy of these digests remains unobserved |
| Image identity is mechanically immutable, not merely a `sha-<commit>` tag convention | `.github/workflows/deploy.yml` (`push_api_to_ghcr`/`push_web_to_ghcr`'s `digest` outputs, `deploy`'s first-publish-wins `image-refs.env` materialization), `scripts/ops/deploy.sh`, `docker-compose.prod.yml` | Independent-review Finding L (closed): a `sha-<commit>` tag alone is not mechanically immutable. Each release is bound to the real OCI manifest digest. The local-registry lifecycle proof established first-publish-wins behavior; canonical-main Deploy run #28 additionally real-executed both GHCR digest resolution paths after publication | **PROVEN locally + real GHCR digest resolution OBSERVED** | first VPS materialization of `image-refs.env` from those digests remains unobserved |
| That immutable image identity is durably retained OFF the application host, not only in VPS-local `image-refs.env` | `.github/workflows/deploy.yml` (`push_api_to_ghcr`/`push_web_to_ghcr`'s "Check GHCR for this exact commit's durable image identity" step, via `docker buildx imagetools inspect`) | Independent-review Finding M (closed): `image-refs.env` exists only on the replaceable VPS, so GHCR is the durable off-host release manifest. The local lifecycle proof established host-loss reconstruction semantics; canonical-main Deploy run #28 real-executed the GHCR durable-identity lookup/publication/re-resolution path for both images | **PROVEN locally + real GHCR durable-manifest path OBSERVED** | first real lost/new VPS reconstruction consuming the retained GHCR identity remains operational evidence for later |
| That durable-manifest lookup fails closed on anything other than a confirmed absence | `.github/workflows/deploy.yml` (both push jobs' existence-check step), `scripts/ops/inspect_deploy_rollback_lifecycle.py` (`_resolve_existing_digest`) | Independent-review Findings N/P (closed): lookup distinguishes valid resolve, exact queried-ref absence and every other failure; only exact confirmed absence permits first publish. The local real-registry outage proof establishes fail-closed behavior and digest preservation, while the adversarial classifier tests reject nested-content `not found` errors. Canonical-main Deploy run #28 additionally observed the successful real GHCR lookup/publication/re-resolution path | **FAIL-CLOSED FAILURE MODES PROVEN locally + real GHCR success path OBSERVED** | a real GHCR outage/auth/rate-limit event is not intentionally induced in production; local adversarial proof remains the retained failure evidence |
| Rollback to previous known-good image/configuration is documented and tested | `scripts/ops/deploy.sh`, `scripts/ops/rollback.sh`, `docker-compose.prod.yml` | `scripts/ops/inspect_deploy_rollback_lifecycle.py` — the REAL `deploy.sh`/`rollback.sh` run against the real Docker Engine and a real nested `releases/<sha>/`+`state/` layout (not reimplemented test doubles): (1) first deploy records no rollback target and the exact pushed digest; (2) A→B upgrade leaves A as the recorded rollback target, A/B genuinely distinct independent digests; (3) manual rollback restores A's exact original digest; (4)/(5) failure paths (auto-revert, corrupted rollback target) unchanged; (6) running container always matches its release's recorded digest; (7) real nested layout; (8) a "republish" attempt with a different digest for an already-established release is refused, its `image-refs.env` left untouched; (9) a host with no locally-cached copy (forced `docker rmi`) and a host with a cached copy resolve to the same content; (10) a release whose entire VPS-local directory is deleted (simulated total host loss) is reconstructed from the durable off-host registry record, redeploying the ORIGINAL content even when a simulated rebuild attempt for the same commit would have produced different content; (11) a real registry outage makes the resolver fail closed (raise, no build/push) rather than rebuild, and the established digest survives the outage unchanged. Executed 2026-10-08, exit 0, all 11 named invariants true, confirmed deterministic across two consecutive runs — exact command/output retained in `PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md` §5 | **PROVEN locally** against the real Docker Engine (mechanism; the real GHCR `docker compose pull` network leg still needs a real VPS — see residual) | first real VPS execution is operational (§9.2) |
| Application hosts stateless/replaceable | `Dockerfile`/`web/Dockerfile` (no local volume for app data); `docker-compose.prod.yml` (no app-data volume; Caddy's `caddy_data`/`caddy_config` volumes hold only TLS state, trivially reissuable); GHCR as the durable release manifest (independent-review Finding M, row above) | Reviewed; both images read all configuration from the environment and persist nothing to local disk. Finding M closes the one real gap in this claim: without a durable off-host image-identity record, "replaceable" would not actually have covered recovering a previously-deployed commit's EXACT image identity after host loss — it now does, proven by invariant 10 above, not merely asserted | **PROVEN by construction** (statelessness) + **PROVEN locally** (image-identity recovery, invariant 10) | none |

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
| Structured application logs | `src/hullq/observability/logging_config.py`; wired into `src/hullq/api/app.py`'s `_structured_access_logging` middleware | `tests/unit/test_observability_logging_config.py` (9 tests) + live containerized-API run emitting real JSON lines to stdout. The first real GitHub Actions run of this branch (2026-10-08) caught a genuine defect static review had missed: `_structured_access_logging` logged the raw request path on every request via a logger independent of uvicorn's own `--log-level`, so `GET /api/_preview/listings/{preview_token}` logged the secret preview token itself, violating SLICE-0048's own token-safe-logging test (`scripts/inspect_first_visible_listing_preview.py` check 13). Fixed with a `_loggable_path()` redaction helper; re-verified both by that script (now reports check 13 OK) and by rerunning the full test suite | **PROVEN**, including a real caught-and-fixed token-leak defect | none |
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
| Least-privilege roles | GHCR token scoped `read:packages` on the VPS; `packages: write` scoped only to the `push_api_to_ghcr`/`push_web_to_ghcr` jobs (not the whole workflow); backup R2 credentials separate bucket/role from media R2 and from the application DB role | reviewed | **DESIGNED** |
| Production SSH host authenticity (not trust-on-first-use) | `.github/workflows/deploy.yml`'s `deploy` job | Independent-review Finding I (closed): before this amendment, the workflow ran `ssh-keyscan` immediately before using the result, trusting whatever host key was presented over the same network path about to be used -- not independent authentication, vulnerable to an active MITM. The workflow now writes a `DEPLOY_SSH_KNOWN_HOSTS` `production`-Environment secret (the production VPS's known_hosts line(s), obtained once out-of-band) directly to `known_hosts` and passes `-o StrictHostKeyChecking=yes` explicitly on every ssh/scp call, instead of ever observing/trusting a key at runtime | **MECHANISM IMPLEMENTED, NOT YET OBSERVED** (no real VPS/host key exists yet to provision the secret against) |
| Auditable privileged operational actions | the four Python ops CLIs (`backup_database.py`, `restore_database.py`, `run_production_migration.py`, `health_monitor.py`) each print one structured JSON result line; the two shell release scripts (`deploy.sh`, `rollback.sh`) print ordinary sequential textual operational output (not JSON — the gate requires actions auditable enough for diagnosis, not a uniform JSON format). Every one of the six uses a distinct non-zero exit code per failure mode | real executions during this slice's proof work (§1-§3 above; `deploy.sh`/`rollback.sh` per the real lifecycle proof in `PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md` §5) produced exactly this output in each case | **PROVEN** |

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

## 9. Why the gate is not `PASS` — current post-merge residuals

Post-merge reconciliation on 2026-10-09 closes one of SLICE-0079's original
provider-observation gaps:

1. **Real GHCR publication — CLOSED.** Canonical-main Deploy run #28 /
   run id `37868264887` at exact SHA
   `5532cd2cc13d9e2ce8bcee90cfc7f0591f14ae9a` completed the exact-SHA
   prerequisite gate, canonical lowercase namespace resolution, API GHCR
   login/lookup/build-push/digest re-resolution and web
   login/lookup/build-push/digest re-resolution with SUCCESS.

The gate remains `IN_PROGRESS` because current-boundary provider evidence
is still incomplete. At minimum:

2. **No real production VPS exists.** `scripts/ops/deploy.sh`/`rollback.sh`
   and the Cloudflare Origin CA topology are written and locally drilled,
   but have never run against a real Contabo production host.
3. **No real DigitalOcean Managed PostgreSQL 18 FRA1 instance exists.**
   Provider backup/PITR, real production connectivity and the controlled
   production migration path therefore remain unobserved against the actual
   target. HA remains `NOT_ACTIVE`; that is allowed only while the stricter
   buyer-exposure trigger is not reached.
4. **The real Cloudflare R2 production configuration is not provisioned.**
   The database-backup mechanism is proven, but the independent encrypted
   production backup bucket/credentials do not yet exist; marketplace-media
   R2 production credentials likewise remain operator configuration.
5. **Real alert delivery is not configured.** The alert mechanism is
   unit-tested, but no production Slack/Discord webhook has been observed.
6. **Production deploy secrets/environment are not provisioned.** The GitHub
   `production` Environment, VPS SSH host/user/key, pinned
   `DEPLOY_SSH_KNOWN_HOSTS` and deploy path still require real operator
   setup before the deploy job can run.
7. **Public/pilot-only controls remain separately gated.** Cloudflare public
   ingress/edge protection, interactive production Auth0 broker login where
   exposed, and PostgreSQL HA before real external buyer exposure must be
   evidenced when those boundaries become active.

Post-SLICE-0079 reconciliation also restored one already-accepted
architecture obligation that was not visible in SLICE-0079's three-item
summary:

8. **Provider-independent broker-original media redundancy is not
   implemented.** `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §22
   requires an independent second copy of original broker media at a
   different storage provider before real broker production. SLICE-0068
   implemented primary Cloudflare R2 storage and future backup/purge
   compatibility only. Current code has one original-media storage write
   path. This implementation gap is selected for SLICE-0080 by
   `docs/POST_SLICE_0079_REASSESSMENT_2026-10-09.md`.

These residuals are not permission to infer production readiness from
mechanism-level proof. Provider-console state and real production
observations must be retained as evidence when established.

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
