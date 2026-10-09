# SLICE-0079 — Acceptance Closure

**Status:** OWNER_ACCEPTED  
**Slice type:** IMPLEMENTATION / PRODUCTION READINESS FOUNDATION  
**Implementation PR:** #310  
**Accepted exact branch HEAD:** `e97ddfd8793aabcc5a999880a44edf0024c9e9ac`  
**Merge commit:** `6e53d8e228947d99f34b586edc097f0320b4805b`  
**Independent exact-head review:** ACCEPT on 2026-10-09  
**Project Owner acceptance:** explicitly recorded on 2026-10-09

## Accepted capability

SLICE-0079 implements the repository-owned production-readiness foundation required by the accepted HullQ production architecture without starting a real external production pilot or claiming Production Readiness PASS.

Accepted scope includes:

- repository-owned API and web Docker images;
- versioned production Compose/Caddy deployment configuration;
- CI-gated GHCR image publication;
- immutable release identity bound to OCI manifest digests;
- durable off-host commit-to-image identity retained in GHCR;
- fail-closed durable-manifest lookup semantics;
- canonical lowercase GHCR namespace derivation;
- per-release deploy state and exact previous-release rollback;
- replaceable/stateless application-host assumptions and host-loss reconstruction proof;
- pinned SSH host authenticity rather than runtime trust-on-first-use;
- PostgreSQL backup/restore mechanism with encrypted off-database object-storage boundary;
- explicit RTO/RPO and retained solo-operator recovery runbook;
- production health/readiness endpoints, structured logging and actionable alert path;
- release migration and post-deploy smoke procedures;
- retained Production Readiness evidence with honest residual infrastructure dependencies.

This slice intentionally does **not** provision or claim successful operation of real production infrastructure that requires Project Owner/provider access.

## Accepted implementation and independent-review findings

Independent review found and closed all material Findings A through P before Owner acceptance:

- **A** — deployment artifact paths/layout were inconsistent: FIXED;
- **B** — release configuration was not mechanically bound to the immutable release identity: FIXED;
- **C** — successful deployment could destroy the previous rollback target: FIXED;
- **D** — deploy/rollback mechanism lacked execution against a real Docker Engine: FIXED with retained executable lifecycle proof;
- **E** — retained evidence overstated/staled actual observations: FIXED;
- **F** — migration runbook contained obsolete procedure: FIXED;
- **G** — production deploy could be dispatched from non-main refs and deploy concurrency was ref-scoped: FIXED with main-only deployment and one global production deploy group;
- **H** — deployment publication was not mechanically gated on exact-SHA CI/security/reproducibility success: FIXED;
- **I** — SSH host authenticity relied on runtime `ssh-keyscan` trust-on-first-use: FIXED with independently provisioned pinned `known_hosts`;
- **J** — documentation incorrectly described all operational scripts as JSON-emitting: FIXED;
- **K** — post-deploy smoke check used an unpinned ad-hoc dependency path: FIXED with the repository's locked `uv` environment;
- **L** — a `sha-<commit>` registry tag alone was mutable and insufficient as release identity: FIXED by binding deployment to real OCI manifest digests;
- **M** — commit-to-digest identity existed only on the replaceable VPS and could be silently rebuilt differently after host loss: FIXED by using GHCR as the durable off-host release manifest and reusing an established digest;
- **N** — any failed GHCR lookup could be misread as absence and permit an unsafe rebuild: FIXED with fail-closed three-way lookup semantics plus post-push re-resolution;
- **O** — mixed-case `github.repository_owner` could produce an invalid/inconsistent GHCR namespace: FIXED with one canonical lowercase namespace output reused by lookup, metadata/push and deploy;
- **P** — confirmed-absence detection was suffix-based and could misclassify nested `...not found` failures: FIXED with exact full-message matching tied to the exact queried reference and adversarial regression coverage.

No unresolved independent-review findings remain on the accepted implementation head.

## Validation result

Accepted retained evidence includes:

```text
docs/validation/PRODUCTION_READINESS_EVIDENCE_2026-10.md
docs/operations/PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md
docs/operations/PRODUCTION_BACKUP_RESTORE_RUNBOOK.md
docs/operations/PRODUCTION_RELEASE_MIGRATION_RUNBOOK.md
docs/operations/PRODUCTION_INCIDENT_OBSERVABILITY_RUNBOOK.md
```

Exact accepted head remote verification at
`e97ddfd8793aabcc5a999880a44edf0024c9e9ac`:

```text
GitHub Actions CI: SUCCESS
Manufacturer artifact reproducibility: SUCCESS
Deploy workflow Docker build jobs: SUCCESS
Canonical lowercase GHCR namespace job: SUCCESS
GHCR push / production deploy jobs on PR event: correctly SKIPPED
```

The real-Docker deploy/rollback lifecycle proof was re-executed after the final classifier amendment and observed clean twice with all 11 retained invariants true.

The PostgreSQL backup/restore proof uses real PostgreSQL 18 dump/restore behavior against disposable resources and includes destructive restore verification.

## Production Readiness gate consequence

Implementation acceptance of SLICE-0079 does **not** equal Production Readiness PASS.

Canonical state after this closure remains:

```text
PRODUCTION_READINESS_GATE_STATUS = IN_PROGRESS
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS = NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS = NOT_PRESENT
PRODUCTION_PILOT_STATUS = NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS = NOT_STARTED
```

The remaining blockers are real provider/infrastructure observations rather than unimplemented repository mechanisms. They include, as applicable at the eventual production boundary:

- first real GHCR publication/pull observation;
- real production VPS provisioning and deployment;
- real DigitalOcean Managed PostgreSQL provisioning;
- PostgreSQL HA activation before any real external buyer exposure;
- real R2 backup/media storage configuration;
- real Cloudflare edge configuration;
- real alert-delivery endpoint and operator routing;
- GitHub `production` Environment restrictions/secrets and pinned production SSH host identity.

These must be proven through the canonical Production Readiness Gate. No external production data, broker pilot, buyer exposure or public launch is authorized merely by accepting this slice.

## Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

- accepted lean production packaging/deployment architecture;
- CI-verified image build path;
- exact-SHA prerequisite-check gate before publication;
- digest-bound immutable release identity;
- durable off-host release identity/reconstruction mechanism;
- fail-closed absence-vs-error handling for registry lookup;
- deterministic lowercase GHCR namespace;
- exact previous-release rollback state;
- pinned SSH host authenticity mechanism;
- PostgreSQL backup/restore mechanism and retained disposable restore proof;
- health/readiness, structured observability and alerting mechanisms;
- production migration/smoke/recovery runbooks and evidence;
- honest Production Readiness gate evidence state.

### DECIDED_NOT_YET_IMPLEMENTED / NOT YET OPERATIONALLY PROVEN

- actual paid/provider production infrastructure provisioning where not yet present;
- real GHCR publication/pull path;
- real VPS deployment;
- real DigitalOcean Managed PostgreSQL target and required later HA state;
- real R2/Cloudflare/alert-provider production configuration;
- external production-data use;
- real broker production pilot;
- public production launch.

### EXPLICITLY DEFERRED

- starting/recruiting the external broker pilot;
- public launch;
- paid broker plan activation;
- unrelated buyer/broker feature expansion;
- Kubernetes/Coolify/Dokploy or another deployment-platform redesign;
- any production-provider spend/provisioning not required to implement the repository mechanisms in this slice.

### GENUINELY_OPEN

- exact timing of provider provisioning and subsequent Production Readiness PASS work;
- next product capability after the required post-SLICE-0079 reassessment;
- exact timing/scope of the eventual bounded external broker pilot after all controlling gates permit it.

### CONFLICT_OR_REGRESSION

None.

## Project-state closure

After this acceptance closure:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0079
PROJECT_STATE_QUEUE_SLICE: 0080
SLICE-0080: UNSELECTED
```

SLICE-0080 must not be selected automatically. A fresh post-SLICE-0079 Decision/Implementation Reconciliation and reassessment must first determine the highest-leverage next capability while preserving:

- `PRODUCTION_READINESS_GATE_STATUS = IN_PROGRESS`;
- no real external production data;
- no external production pilot;
- no public launch;
- the separately hard PostgreSQL HA trigger before real external buyer exposure.

Before any SLICE-0080 readiness is created, the Project Owner must receive the required short plain-language description of what the proposed slice would build/change and why.

`FINISH_SLICE.bat` for 0079 is permitted only after this closure PR passes independent exact-head closure review, required remote gates and merge to `main`.
