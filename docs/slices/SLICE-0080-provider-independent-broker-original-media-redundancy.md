# SLICE-0080 — Provider-Independent Broker Original-Media Redundancy

**ID:** SLICE-0080
**Type:** IMPLEMENTATION
**Status:** REVIEW
**Stage:** pre-production broker-media durability
**Depends on:** SLICE-0079 owner-accepted / DONE; post-SLICE-0079 reconciliation PASS; Backblaze B2 provider decision OWNER_ACCEPTED
**Blocks:** real broker production media until independent original/source redundancy is implemented and later operationally configured/proven

## Objective

Extend the accepted SLICE-0068 broker-media upload path so every newly durable broker-uploaded original/source media object is synchronously stored both in primary Cloudflare R2 and independently in Backblaze B2 before PostgreSQL may claim the MediaAsset/redundancy state exists.

## Plain-language capability

A broker uploads an image once.

HullQ keeps its normal private original in Cloudflare R2, but also stores an independent private copy in Backblaze B2. If the second provider fails, HullQ does not pretend the upload is safely backed up. No listing/gallery/public truth is created from a partially redundant upload.

Processed public derivatives stay in R2 and are not duplicated.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS
One coherent capability only: establish truthful provider-independent redundancy for broker-uploaded original/source image bytes at MediaAsset creation time. Storage adapter/configuration, persistence metadata, upload orchestration and tests are inseparable layers of that one durability outcome.

**VISIBLE-RESULT CHECK:** PASS
The Project Owner can inspect a retained proof showing dual-store success, forced B2 failure with zero MediaAsset truth, legacy rows remaining unverified, and unchanged primary derivative/public-read behavior. The Broker Workspace upload still looks like one upload action; success now means the required independent original copy was actually established.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS
The slice closes the already-accepted `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` `22 rule rather than adding a new feature. It preserves Cloudflare R2 as primary marketplace-media storage, uses the Owner-selected Backblaze B2 EU Central secondary provider, does not change public media serving or publication readiness, and starts no production pilot.

**REPOSITORY RECONCILIATION CHECK:** PASS
Canonical main after SLICE-0079 and PR #314 was reconciled against SLICE-0068 implementation/spec/closure, current `ObjectStorage`/R2 adapter, upload application ordering, MediaAsset schema/persistence, API wiring, partial-failure/concurrency tests, Production Readiness evidence and the post-SLICE-0079 reassessment. Current code stores exactly one original copy and contains no second-provider original-media write or durable redundancy truth.

**TRIGGER GATES CHECK:** PASS
Production Readiness remains `IN_PROGRESS`; no real external seller/listing data, pilot or public launch starts here. The slice is repository implementation only. The real B2 account/bucket/key and other provider setup remain Production Launch Pack/operator work.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS
`MVP-PROD-013` is the selected already-accepted pre-real-broker-production gap. Other pending support/admin/privacy/legal/communications/monetization/data-operations capabilities retain their existing triggers. This slice is selected ahead of unrelated feature expansion because real broker original media may not enter production without the independent copy.

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/POST_SLICE_0079_REASSESSMENT_2026-10-09.md`; `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` `22; `docs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_PROVIDER_DECISION_2026-10-09.md`; `specs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_CONTRACT.v0.1.md`; `specs/MARKETPLACE_MEDIA_GALLERY_CONTRACT.v0.1.md`; SLICE-0068 primary slice + acceptance closure; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; `docs/operations/PRODUCTION_LAUNCH_PACK.md`.
**Production implementation checked:** `src/hullq/storage/object_storage.py`; `src/hullq/application/media_gallery.py`; `src/hullq/persistence/media_gallery.py`; `src/hullq/api/app.py` media storage resolver/upload route; `alembic/versions/d4e8f2a71b93_marketplace_media_gallery.py`; media API/persistence/partial-failure/concurrency tests; object-storage unit tests; production environment template.
**Already implemented / not re-decided:** MediaAsset/MediaPlacement identity; Organization/MFA/PUBLISHER authorization; Cloudflare R2 as primary private original/quarantine + derivative store; approved derivative-only serving; rights/processing/public-usability rules; same-Organization byte reuse; D24 retirement compatibility; storage-before-database fail-closed ordering; primary object-storage abstraction; bounded upload/CSRF/rate-limit boundaries.
**Exact remaining gap:** a newly durable broker MediaAsset currently proves only the primary R2 original write. PostgreSQL contains no durable indication/locator for an independent original copy, FastAPI resolves only one object store, and no Backblaze B2 configuration/adapter exists. The accepted `22 provider-independent original/source redundancy requirement is therefore unimplemented.
**Accepted-but-unimplemented obligations:** MVP-PROD-013; accepted architecture `22 second-provider copy before real broker production; durable non-fabricated redundancy truth; Backblaze B2 adapter/configuration and upload integration; migration preserving legacy rows as unverified; future-purge-compatible B2 locator metadata. Real B2 account/bucket/key provisioning remains operator work, not implementation.
**Material classifications:** `DECIDED_AND_IMPLEMENTED` existing SLICE-0068 media identity/primary storage/public derivative path and SLICE-0079 production foundation; `DECIDED_NOT_YET_IMPLEMENTED` provider-independent original-media redundancy and durable redundancy metadata; `EXPLICITLY_DEFERRED` historical backfill, automatic B2 read failover/restore, full purge/legal-hold worker, owner-direct media, derivatives backup and real provider provisioning; `GENUINELY_OPEN` only bounded schema/class naming and safe internal S3-client factoring that do not weaken the normative contract; `CONFLICT_OR_REGRESSION` none after the post-0079 reconciliation restored the previously hidden obligation.

## Production phase transition check

**Launch-pack phase before this slice:** NOT_APPLICABLE
**Launch-pack phase after this slice:** NOT_APPLICABLE
**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE

SLICE-0080 implements a repository capability required before broker production but does not provision the Backblaze account/bucket/key, create production data, change the active operational exposure boundary, begin a pilot or advance the canonical Launch Pack phase. `PRODUCTION_LAUNCH_PACK_PHASE` remains `NOT_STARTED`. The real Backblaze account belongs to Phase 1; secrets/connectivity belong to later applicable phases.

## Trigger gates

**Production readiness gate:** IN_PROGRESS
**Adds technical native Search criterion:** NO
**Technical Search criterion ordinal:** NOT_APPLICABLE
**Second-criterion bridge comparison:** NOT_APPLICABLE
**Third-copy abstraction guard:** NOT_APPLICABLE
**Workflow reassessment status:** PASS

No external broker production data/pilot/public launch is authorized by implementation or acceptance of this slice.

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK
**Why this classification:** This slice changes durable source-media redundancy across two external storage providers plus PostgreSQL. A fail-open partial write could make HullQ believe irreplaceable broker originals are protected when they are not.
**Must-never-change invariant:** A newly durable post-SLICE-0080 broker MediaAsset may claim established independent original redundancy only after the exact upload's primary R2 original write and independent Backblaze B2 original write both returned confirmed success. One provider success, queued intent, retry intent or unknown provider result never counts as two copies.
**Durable source of truth / loss boundary:** PostgreSQL remains authoritative for MediaAsset identity and whether an independent copy is established; stored operational locator/provider metadata must allow the B2 copy to be found without provider URLs becoming identity. R2 and B2 hold bytes; application host/process/cache is replaceable. Existing pre-0080 rows migrate as explicitly unverified/not-established, never fabricated as backed up.
**Retry / replay / partial-failure behavior:** Primary failure creates no row; primary-success/B2-failure creates no row or placement; dual-original-success/derivative-failure creates no approved row or placement; storage-success/database-failure leaves no database truth. Orphan objects may remain for later GC. API/browser retry is a new upload attempt unless an already-accepted idempotency mechanism applies; same-Organization reuse never writes a duplicate backup. Concurrent gallery/retirement behavior remains under existing MediaAsset lock/order rules and cannot rewrite established storage identity.
**Absence-vs-error / fail-closed behavior:** B2 timeout, DNS/TLS/network error, auth/permission failure, quota/rate limit, endpoint/region mismatch, malformed response or unknown SDK error is never treated as “copy absent but acceptable.” Only an exact provider-documented not-found for an exact read key may be classified as absence. Upload establishment needs confirmed PUT success; missing/malformed B2 config fails fast.
**Executable adversarial proof:** Execute deterministic dual-store tests for success and forced failure at every boundary: primary fail; B2 auth/network/transport-style fail; rejected image after dual original writes; derivative fail after dual original writes; DB failure after storage writes; legacy row migration; impossible redundancy row shape rejected; same-Organization reuse writes no new backup; public/broker derivative read never touches B2; retirement preserves backup locator; primary/backup production resolvers cannot both resolve to Cloudflare R2; malformed/missing B2 configuration errors redact secrets. Run real PostgreSQL migration/persistence tests, existing media partial-failure/concurrency suites, normal repository validation and exact-head CI/reproducibility.
**Slice sizing assessment:** COHERENT

The B2 adapter/config, database redundancy truth and upload dual-write ordering are not independently useful capabilities: without all three, the accepted “independent original copy before durable MediaAsset truth” outcome cannot be established. Full restore/failover, historical backfill and purge automation are separate failure domains and explicitly excluded.

## Why this slice exists

SLICE-0079 closed the repository-owned general production mechanisms, and the first real GHCR push has since been observed. Post-0079 reconciliation then found that the 2026-09-02 architecture's provider-independent broker-original requirement remained only future-compatible in SLICE-0068, not implemented.

Real broker production media would violate accepted architecture if HullQ proceeded without closing this gap. The scope is deliberately narrower than another umbrella production slice.

## Controlling artifacts

- Normative redundancy contract: `specs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_CONTRACT.v0.1.md`
- Existing media contract: `specs/MARKETPLACE_MEDIA_GALLERY_CONTRACT.v0.1.md`
- Owner provider decision: `docs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_PROVIDER_DECISION_2026-10-09.md`
- Accepted architecture: `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` `22
- Reassessment/selection: `docs/POST_SLICE_0079_REASSESSMENT_2026-10-09.md`
- Production gate: `docs/governance/PRODUCTION_READINESS_GATE.md`
- Overall MVP register: `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md` — MVP-PROD-013
- Existing implementation baseline: SLICE-0068 primary/closure plus current media/storage/API/persistence code and tests
- Provider behavior reference: current Backblaze B2 S3-compatible API/application-key/data-region documentation cited by the provider decision
- Relevant open questions: NONE at product/provider-policy level; implementation names/refactoring only

## In scope

1. Add Backblaze B2 EU Central secondary-original storage configuration and adapter construction behind the existing `ObjectStorage` byte-store behavior boundary.
2. Keep Cloudflare R2 as the existing primary store and make primary vs independent-original storage roles explicit in FastAPI/application wiring.
3. Extend broker image upload orchestration so primary original and B2 original both succeed before a new MediaAsset row is committed.
4. Preserve the existing processing flow:
   - rejected uploads retain private originals but no derivative;
   - approved uploads create the controlled derivative in primary R2;
   - public/broker preview reads use the approved primary derivative only.
5. Add durable PostgreSQL metadata sufficient to distinguish legacy/unverified rows from post-0080 rows with an established B2 copy and to locate that copy later.
6. Add an Alembic migration that preserves existing rows as unverified/not-established and enforces any new redundancy-state shape constraints without fabricating success.
7. Extend persistence/domain/application serialization only as needed for internal truth/evidence; do not expose provider secrets/URLs publicly.
8. Add production environment-template secret/config names for B2 without values.
9. Add focused deterministic proof for dual-provider partial failure/retry/read-boundary/migration semantics.
10. Update retained Production Readiness evidence/register only to reflect implementation status truthfully after implementation; do not claim live B2 provider proof without real credentials/execution.

## Explicitly out of scope

- creating the real Backblaze account;
- choosing the account region again — EU Central is already Owner-decided;
- creating the real B2 bucket or application key;
- putting real B2 secret values in GitHub/repository docs;
- live B2 network execution as a prerequisite to implementation acceptance;
- advancing Production Launch Pack phase;
- historical/pre-production MediaAsset backfill;
- automatic restore/read failover from B2;
- complete disaster-recovery orchestration;
- complete timed purge/legal-hold/cross-provider deletion worker;
- B2 Object Lock policy;
- duplicating derivatives;
- owner-direct media;
- direct uploaded video/HEIC;
- changes to rights/publication readiness/cover/Search semantics;
- external production data, broker pilot, buyer exposure or public launch;
- unrelated storage abstraction redesign.

## Required behavior

### Provider independence

Production primary media resolution remains Cloudflare R2. Independent-original resolution is Backblaze B2 and uses separate endpoint, region, bucket and credentials.

The runtime wiring must make it impossible for the ordinary production configuration path to satisfy both roles from the same R2 configuration by accident.

### S3-compatible integration

Backblaze B2 must be consumed through server-side S3-compatible APIs/SDK behavior. Runtime configuration uses the exact endpoint and S3 region identifier returned by the real B2 bucket/account; do not hardcode a guessed EU cluster suffix.

Dedicated B2 credentials are separate from R2 and from database-backup R2 credentials.

### Database truth

The schema must preserve legacy rows without claiming they are backed up. For new rows, any stored “established” redundancy state must have its required provider/locator shape enforced at the database boundary where practical.

Provider identity is operational recovery metadata only; it does not participate in MediaAsset ID, listing ID or public URL identity.

### Upload ordering

Minimum safe ordering:

```text
authorize/validate request
→ primary R2 original PUT
→ independent B2 original PUT
→ process image
→ if approved: primary R2 derivative PUT
→ PostgreSQL MediaAsset + placement transaction
```

An equivalent ordering is acceptable only if it preserves the mechanical invariants in the normative redundancy contract.

### Error surface

Provider/config failures must not leak endpoint credentials, application-key secret, raw SDK exception payloads or bucket-private details to broker/public responses or logs.

A secondary-store failure should surface as one bounded generic storage-unavailable/error outcome appropriate to the existing API style, not as a false successful upload.

### Existing behavior preserved

- primary originals remain private;
- only processed derivative bytes are served;
- cross-Organization isolation remains unchanged;
- rights/processing/public-usability and active-listing cover invariants remain unchanged;
- same-Organization reuse reuses the existing MediaAsset and bytes;
- Search criterion count stays exactly 2.

## Deliverables

At minimum:

- `docs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_PROVIDER_DECISION_2026-10-09.md` retained as controlling Owner decision;
- `specs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_CONTRACT.v0.1.md`;
- Backblaze B2 secondary-storage configuration/adapter support;
- explicit primary + independent-original app/API dependency wiring;
- MediaAsset redundancy persistence/migration;
- dual-write upload orchestration;
- focused unit/PostgreSQL/API partial-failure and migration proof;
- production environment-template B2 names only;
- truthful updates to current media/production evidence/register as required.

## Acceptance criteria

- [ ] Cloudflare R2 remains the production primary media store and Backblaze B2 is the only accepted production independent-original provider;
- [ ] real configuration has distinct B2 endpoint/region/key/bucket variables and no committed secret values;
- [ ] missing/malformed B2 configuration fails fast with redacted errors;
- [ ] new broker upload cannot commit MediaAsset/redundancy truth until both primary and B2 original writes succeed;
- [ ] primary-success/B2-failure produces no MediaAsset, placement or derivative/public truth;
- [ ] B2 auth/network/timeout/unknown provider errors fail closed and are not treated as absence/success;
- [ ] rejected image after successful dual-original writes persists REJECTED MediaAsset with established redundancy truth and no derivative;
- [ ] derivative failure after successful dual-original writes produces no APPROVED MediaAsset or placement;
- [ ] database transaction failure after storage success leaves no durable database truth;
- [ ] migration preserves all existing MediaAssets as unverified/not-established rather than fabricating backup success;
- [ ] database constraints reject impossible established-redundancy shapes;
- [ ] durable metadata can locate the established B2 copy for future restore/purge without making provider URLs/IDs MediaAsset identity;
- [ ] same-Organization reuse creates no second backup copy;
- [ ] broker preview/public media reads remain primary-derivative-only and never read B2 originals;
- [ ] retirement keeps B2 locator metadata intact for future purge;
- [ ] ordinary production resolver cannot accidentally satisfy primary and secondary roles from one Cloudflare R2 configuration;
- [ ] full existing SLICE-0068 media API/persistence/partial-failure/concurrency behavior remains green;
- [ ] Production Readiness remains `IN_PROGRESS` unless separately supported by real provider evidence;
- [ ] Production Launch Pack remains `NOT_STARTED`;
- [ ] no real external production data/pilot/public launch is started;
- [ ] repository validation passes;
- [ ] exact-head GitHub Actions CI succeeds;
- [ ] Manufacturer artifact reproducibility succeeds;
- [ ] independent exact-head implementation review accepts the final candidate;
- [ ] explicit Project Owner acceptance occurs before implementation merge.

## Expected touch points

Expected implementation areas:

```text
src/hullq/storage/object_storage.py
src/hullq/application/media_gallery.py
src/hullq/persistence/media_gallery.py
src/hullq/domain/media_gallery.py              # only if record/value shape needs it
src/hullq/api/app.py
alembic/versions/<new media redundancy migration>.py
docs/operations/production.env.example
docs/validation/PRODUCTION_READINESS_EVIDENCE_2026-10.md
docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md
tests/unit/test_object_storage_unit.py
tests/persistence/test_media_gallery_*.py
scripts/inspect_media_gallery_*.py              # if retained proof extension is useful
```

Do not modify frontend UX unless required only to map the bounded generic upload-storage failure; the primary capability is backend durability, not a media-workspace redesign.

## Validation

At minimum:

```bash
uv run python scripts/validate_repository.py
uv run pytest tests/unit/test_object_storage_unit.py
uv run pytest tests/persistence/test_media_gallery_application_partial_failure.py
uv run pytest tests/persistence/test_media_gallery_persistence.py
uv run pytest tests/persistence/test_media_gallery_api.py
uv run python scripts/inspect_media_gallery_migration.py
uv run python scripts/inspect_media_gallery_persistence.py
uv run python scripts/inspect_media_image_processing.py
```

Run the full repository-prescribed test/quality suite and remote exact-head gates before handoff.

Mechanical/adversarial proof must execute the failure cases listed in `specs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_CONTRACT.v0.1.md` `14. Static inspection alone is insufficient.

Remote requirements:

```text
GitHub Actions CI = SUCCESS
Manufacturer artifact reproducibility = SUCCESS
Deploy workflow build-only PR jobs = SUCCESS
production push/deploy jobs on PR = correctly SKIPPED
```

Live Backblaze execution is **not** required for slice implementation acceptance because the real account/bucket/key belongs to Production Launch Pack operator setup. Evidence must clearly say `MECHANISM PROVEN, REAL B2 NOT YET OBSERVED`.

## Stop conditions

Stop and report rather than inventing a solution if:

- implementing synchronous dual-store truth would require changing MediaAsset/listing identity;
- a Backblaze limitation makes a private S3-compatible server-side object store impossible under the accepted provider decision;
- the only possible design would expose B2 originals publicly;
- implementation requires an eventual/asynchronous repair contract to satisfy the basic pre-production copy invariant;
- schema migration would have to mark legacy rows backed up without proof;
- provider/config errors cannot be distinguished from confirmed success without fail-open behavior;
- a new cross-Organization media-rights/publication policy is required;
- full restore/backfill/purge becomes necessary to make the upload-time redundancy capability safe, indicating `SPLIT_REQUIRED` or reassessment;
- any trigger gate changes state unexpectedly;
- implementation requires real provider credentials to pass ordinary CI.

## Status handoff rule

Implementation may finish in `REVIEW`, never `DONE`.

Independent exact-head implementation review plus explicit Project Owner acceptance remain mandatory before merge. No later slice starts automatically.

## Required completion report

Use the current `docs/slices/SLICE_TEMPLATE.md` completion-report structure exactly, including the Mechanical Invariants / Failure Modes and Production Launch Pack checks.
