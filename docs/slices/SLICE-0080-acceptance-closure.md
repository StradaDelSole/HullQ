# SLICE-0080 — Acceptance Closure

**Status:** OWNER_ACCEPTED  
**Slice type:** IMPLEMENTATION / HIGH_RISK PRODUCTION MEDIA DURABILITY  
**Implementation PR:** #317  
**Accepted exact branch HEAD:** `de45c65b67b40f197a271bf8a591f62328c70a57`  
**Merge commit:** `c8becb326a4b7e2ef6bd1fdb6edd94057c7f864d`  
**Independent exact-head review:** ACCEPT on 2026-10-09  
**Project Owner acceptance:** explicitly recorded on 2026-10-09

## Accepted capability

SLICE-0080 closes the accepted architecture §22 requirement that broker-uploaded original/source media must have an independent second copy at a storage provider different from primary Cloudflare R2 before real broker production media is permitted.

Accepted production direction is:

```text
primary original/quarantine + processed derivatives
→ Cloudflare R2

independent second copy of broker original/source bytes
→ Backblaze B2
→ EU Central
```

The implemented upload invariant is synchronous and fail-closed:

```text
primary R2 original write succeeds
AND
independent B2 original write succeeds
BEFORE
PostgreSQL may commit MediaAsset/redundancy truth
```

Processed public derivatives remain primary-R2-only and regenerable. Backblaze B2 is never a public serving origin and never becomes MediaAsset identity.

## Accepted implementation

The owner-accepted implementation includes:

- a distinct Backblaze B2 S3-compatible adapter/configuration boundary separate from Cloudflare R2;
- structural validation that production B2 configuration is HTTPS Backblaze S3 in the accepted EU Central region family and cannot silently resolve to Cloudflare R2, AWS or another arbitrary S3 provider;
- explicit primary and independent-original storage roles in application/API wiring;
- synchronous R2-original then B2-original write ordering before processing/database truth;
- byte-identical B2 copy under the server-generated opaque original object key;
- durable PostgreSQL redundancy metadata:
  - `backup_provider`;
  - `backup_object_key`;
  - `backup_established_at`;
- database constraints preserving legacy/pre-0080 rows as all-NULL/unverified and rejecting partial, unsupported-provider or empty/whitespace established-backup shapes;
- retained backup locator metadata through MediaAsset retirement for future purge/recovery;
- same-Organization MediaAsset reuse without duplicate backup writes;
- public/broker media reads remaining processed-derivative-only;
- bounded S3 provider error handling across PUT/GET/DELETE and streaming-body reads, with raw provider/SDK details suppressed from propagated exception context;
- deterministic adversarial proof without requiring live production Backblaze credentials.

## Independent-review findings

All material findings were closed before Owner acceptance.

### Finding A — HIGH — raw S3/provider error leakage

Initial implementation bounded GET provider errors but allowed raw PUT/DELETE and other Botocore failures to escape the storage boundary. The amendment introduced common bounded provider-error mapping for R2/B2 PUT, GET and DELETE, preserving exact confirmed-not-found semantics while treating every other provider/transport/auth/quota/timeout failure as a dependency error.

### Finding B — HIGH — accepted B2 EU Central identity not mechanically enforced

Initial B2 configuration accepted arbitrary non-empty endpoint/region values, permitting a false `BACKBLAZE_B2` database claim over another provider or non-EU Backblaze region. The amendment added structural URL/hostname/region validation requiring the accepted Backblaze B2 EU Central S3-compatible shape while leaving the exact numeric cluster suffix runtime-configurable.

### Finding C — MEDIUM/HIGH — established backup allowed an unusable empty locator

Initial database shape required only non-NULL backup locator state. The amendment strengthened both PostgreSQL and persistence validation so empty or whitespace-only backup object keys cannot represent established redundancy.

### Finding A residual — HIGH — streaming-body read errors bypassed bounded mapping

A subsequent exact-head review found that `response["Body"].read()` occurred outside the bounded GET error block. The final amendment moved streaming-body ClientError/BotoCoreError handling into the same bounded error boundary. Read timeout and incomplete-stream failures now fail closed as `ObjectStorageConfigError`, never as object absence, with suppressed raw exception chaining.

No unresolved independent-review findings remain on the accepted implementation head.

## Mechanical invariants / failure modes result

**Risk classification:** HIGH_RISK  
**Mechanical invariants review:** PASS  
**Slice sizing:** COHERENT

Accepted must-never-change behavior includes:

- one provider write never counts as two copies;
- failed/unknown B2 write never creates backup-present database truth;
- legacy rows never gain fabricated backup state;
- primary-success/B2-failure creates no MediaAsset/placement truth;
- dual-original-success/derivative-failure creates no approved MediaAsset/placement truth;
- storage-success/database-failure leaves no database truth;
- rejected uploads that become durable REJECTED MediaAssets have established original redundancy;
- same-Organization reuse does not create another B2 copy;
- B2 is never used as the public/broker preview media origin;
- provider dependency errors are never interpreted as confirmed object absence;
- retirement preserves the secondary locator for future purge/recovery;
- established-backup database truth requires a supported provider, usable object locator and establishment timestamp.

## Validation result

Exact accepted-head remote verification at
`de45c65b67b40f197a271bf8a591f62328c70a57`:

```text
GitHub Actions CI: SUCCESS
PostgreSQL 18 integration: SUCCESS
Ubuntu quality: SUCCESS
Windows quality: SUCCESS
Dependency audit: SUCCESS
Historical research/bootstrap replay: SUCCESS
Web quality: SUCCESS

Manufacturer artifact reproducibility:
  Ubuntu: SUCCESS
  Windows: SUCCESS

Deploy PR workflow:
  API image build: SUCCESS
  Web image build: SUCCESS
  lowercase GHCR namespace: SUCCESS
  GHCR push: correctly SKIPPED on pull_request
  production deploy: correctly SKIPPED on pull_request
```

Focused retained proof also covered the normative §14 matrix, including dual-store success/failure, rejected and derivative-failure ordering, database failure after storage success, legacy non-fabrication, reuse, read isolation, retirement, provider/config rejection and database constraint bypass attempts.

## Production Readiness / Launch Pack consequence

SLICE-0080 acceptance closes the repository implementation gap for provider-independent broker-original redundancy, but it does **not** prove the real Backblaze provider boundary.

Canonical production state remains:

```text
PRODUCTION_READINESS_GATE_STATUS = IN_PROGRESS
PRODUCTION_LAUNCH_PACK_PHASE = NOT_STARTED

EXTERNAL_BROKER_PRODUCTION_DATA_STATUS = NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS = NOT_PRESENT
PRODUCTION_PILOT_STATUS = NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS = NOT_STARTED
```

The real Backblaze B2 EU Central account, MFA/recovery/billing evidence, private bucket, least-privilege application key, secret-store placement and real connectivity/write/read/delete proof remain Production Launch Pack operator work.

Likewise, acceptance does not waive the other outstanding provider/infrastructure requirements such as real production VPS, DigitalOcean Managed PostgreSQL, Cloudflare R2/edge, alert delivery and the separate PostgreSQL HA hard trigger before real external buyer exposure.

## Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

- Backblaze B2 EU Central as the independent broker-original storage provider;
- Cloudflare R2 remains primary marketplace media storage;
- synchronous dual-original write before durable MediaAsset redundancy truth;
- truthful legacy/unverified database state;
- future-purge/recovery-compatible B2 locator metadata;
- fail-closed provider/configuration/error semantics;
- bounded S3 error propagation including streaming-body failures;
- processed derivatives remain primary-only and public serving never uses B2.

### DECIDED_NOT_YET_OPERATIONALLY_PROVEN

- real Backblaze account/bucket/application-key configuration;
- real B2 connectivity and actual provider write/read/delete observation;
- real Cloudflare R2 production media configuration;
- real production infrastructure/deployment boundary generally.

### EXPLICITLY_DEFERRED

- historical MediaAsset backup backfill;
- automatic B2 public/read failover;
- full disaster-recovery restore orchestration from B2;
- timed cross-provider purge/legal-hold worker;
- B2 Object Lock policy;
- derivative duplication;
- owner-direct media redundancy;
- real external broker production data or pilot;
- public launch.

### GENUINELY_OPEN

- no material SLICE-0080 product/provider-policy question remains;
- exact timing of Production Launch Pack provider provisioning remains operational sequencing work;
- the next product/production capability must be selected only after fresh post-SLICE-0080 reassessment.

### CONFLICT_OR_REGRESSION

None.

## Project-state closure

After this acceptance closure:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0080
PROJECT_STATE_QUEUE_SLICE: 0081
SLICE-0081: UNSELECTED
PRODUCTION_LAUNCH_PACK_PHASE: NOT_STARTED
```

SLICE-0081 must not be selected or started automatically. A fresh post-SLICE-0080 Decision/Implementation Reconciliation and reassessment must first determine the highest-leverage next capability while preserving all current production/exposure gates.

`FINISH_SLICE.bat` for 0080 is permitted only after this closure PR passes independent exact-head closure review, required remote gates and merge to canonical `main`.
