# SLICE-0068 — Acceptance Closure

**ID:** SLICE-0068  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #258  
**Accepted implementation HEAD:** `0dc0dd5e928c34f94896b50d3eb299187a842790`  
**Implementation merge commit:** `a8145895dc819708ab58a5bec52552a8c4e002c7`  
**Independent exact-head ACCEPT review:** 2026-09-27  
**Owner acceptance:** explicitly recorded 2026-09-27

## Accepted capability

SLICE-0068 implements the accepted broker marketplace mixed-media gallery for existing Organization-owned NativeListings:

```text
Organization-owned NativeListing
→ JPEG / PNG / WebP upload
→ private original/quarantine object
→ validated / metadata-stripped / safely re-encoded derivative
→ durable MediaAsset + MediaPlacement truth
→ ordering + explicit valid IMAGE cover
→ same-Organization reuse
→ structured YouTube reference
→ Broker Workspace gallery management
```

Cloudflare R2 Standard is the initial primary object-storage provider behind HullQ's S3-compatible storage boundary. PostgreSQL remains authoritative for media identity, Organization control, uploader/provenance, rights, processing state, object references, ordering and cover truth.

## Accepted implementation behavior

- MediaAsset and MediaPlacement are independent durable identities attached to NativeListing, never ProfessionalListingDraft.
- IMAGE v0.1 accepts JPEG, PNG and WebP; HEIC/HEIF, SVG and arbitrary files remain out of scope.
- raw image uploads are stored under a private server-generated original/quarantine key;
- successful processing produces a separate derivative key;
- only approved derivatives are served by the broker preview route; original/quarantine objects have no serving route;
- image processing enforces finite byte/pixel limits, real decoding, animated-image rejection, EXIF/embedded-metadata removal, bounded downscaling and deterministic JPEG re-encoding;
- MediaAsset records Organization, uploader Account, structured `BROKER_UPLOAD` provenance, optional bounded source reference, rights state, processing state, hashes/dimensions/MIME and original/derivative object references;
- rights UNKNOWN remains distinct from APPROVED processing and never becomes public-usable or cover-eligible;
- same-Organization approved assets may be reused without duplicating bytes; cross-Organization access/reuse fails closed;
- REJECTED and RETIRED assets cannot be reused;
- YouTube inputs are normalized to structured video identity/reference; arbitrary embed HTML is rejected;
- gallery ordering is durable and optimistic-concurrency protected;
- exactly zero or one explicit cover is represented; a cover must be an approved, rights-valid, non-retired IMAGE placement;
- ACTIVE listings reject mutations that would remove the required valid image/cover without a valid replacement; no auto-withdraw is introduced;
- DRAFT/WITHDRAWN listings remain editable down to zero media;
- MediaAsset eligibility-sensitive mutations serialize on PostgreSQL row locks with a consistent MediaAsset → NativeListing → gallery-head lock order;
- retirement prevents stale concurrent reuse/set-cover success and preserves ACTIVE-listing invariants;
- the Broker Workspace upload path streams each bounded image through a same-origin Astro proxy to the bounded FastAPI upload endpoint without `formData()`/file-buffering in Astro;
- client upload batches are finitely bounded and report per-file outcomes;
- object-store/database partial failure remains fail-closed: no database state may claim missing/uncommitted media; unreferenced namespaced storage objects may remain for later GC;
- placement removal does not delete shared MediaAsset truth;
- retirement preserves future D24 original/derivative/backup purge compatibility;
- direct uploaded VIDEO remains deferred; the gallery model remains extensible;
- the future Broker-CI gallery slide remains virtual/presentation-only and cannot satisfy cover/media readiness;
- canonical PublicationReadiness/publish integration remains separate and unimplemented by 0068;
- accepted technical native Search criterion count remains exactly 2.

## Independent review and amendments

Initial implementation HEAD `8a85b07e8c9f0293a6439fe771eaee3c9565bc61` required three material fixes:

1. preserve private original/quarantine object truth separately from processed derivative truth;
2. persist D14 source/provenance on MediaAsset;
3. protect ACTIVE listings from losing their required valid image/cover through remove/clear-cover/retire mutations.

Amendment HEAD `f395dddefe6a6ba5a481394886e4777c758d971c` closed those findings.

Second exact-head review then found:

4. the original Broker Workspace upload path still buffered multipart bodies in Astro before the FastAPI size boundary;
5. retire/reuse/set-cover did not yet share a race-safe MediaAsset locking authority.

Second amendment HEAD `fcd4be0d8e160eca18394e180e17201c6ea7b213` replaced the upload flow with a bounded streaming same-origin proxy, added batch bounds, established one global row-lock order, added real PostgreSQL concurrency tests and added explicit partial-storage/database-failure tests.

Final handoff HEAD `0dc0dd5e928c34f94896b50d3eb299187a842790` changed only the primary slice document from READY to REVIEW and added the required REVIEW handoff marker. No implementation code changed after the final technical review.

No material implementation finding remains on the accepted exact head.

## Decision / implementation reconciliation at acceptance

```text
DECIDED_AND_IMPLEMENTED
- D13 MediaAsset + MediaPlacement marketplace media truth
- D14 Organization control, uploader provenance and declared-rights state
- D15 approved rights-valid public-usable IMAGE and explicit IMAGE cover semantics
- D24 retirement-compatible original/derivative lifecycle foundation
- D30 Cloudflare R2 primary storage behind S3-compatible HullQ boundary
- JPEG/PNG/WebP image v0.1
- D31 mixed-media IMAGE + structured YOUTUBE gallery
- same-Organization media reuse without byte duplication
- broker media workspace upload/order/cover/remove/reuse/retire/YouTube operations
- bounded streaming upload path
- ACTIVE-listing last-valid-image/cover protection
- race-safe media retirement/reuse/cover locking
- technical native Search criterion count remains exactly 2

DECIDED_NOT_YET_IMPLEMENTED
- D22 canonical PublicationReadiness and integrated publish flow
- public gallery/read integration consuming canonical media truth where not already present
- direct broker VIDEO upload/transcoding/streaming
- virtual Broker-CI slide rendering and CI authoring controls
- full D24 retention/legal-hold/backup-purge worker
- cross-Organization media usage grants
- owner-direct media
- durable buyer contact / Lead creation
- broker lead operating surface
- post-promotion marketplace inventory editing
- sale/outcome, import/export, analytics and alerts

EXPLICITLY_DEFERRED
- HEIC/HEIF
- arbitrary external embeds
- direct uploaded VIDEO
- complete purge scheduler/independent-backup deletion automation
- production pilot/public launch in this slice

CONFLICT_OR_REGRESSION
- none remain on the accepted exact head
```

## Exact-head verification

Remote verification on exact accepted HEAD `0dc0dd5e928c34f94896b50d3eb299187a842790`:

```text
CI run 36353714200 → SUCCESS
Manufacturer artifact reproducibility run 36353714205 → SUCCESS
```

Independent exact-head implementation review: **ACCEPT**, review ID `5332338699`.

Implementation-agent validation additionally recorded repository validation PASS; ruff check/format clean; mypy clean across 122 source files; complete PostgreSQL-backed Python suite 5636 passed / 3 skipped / 0 failed; retained media migration/image-processing/persistence proofs PASS; web check/build PASS; 312 web tests passed.

PR #258 merged the exact accepted implementation to `main` as `a8145895dc819708ab58a5bec52552a8c4e002c7`.

## Trigger-gate state after acceptance

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_STATUS: PASS

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED

BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

0068 introduces no real external production inventory, external pilot, paid broker plan or public production launch and changes no Search criterion.

## Broker launch execution checkpoint

The broker launch path is now:

```text
BROKER CREATES
→ BROKER ADDS MEDIA   [implemented through SLICE-0068]
→ BROKER PUBLISHES   [next reassessment target: canonical PublicationReadiness + publish integration]
→ BUYER CONTACTS
→ BROKER HANDLES LEAD
→ BROKER EDITS / MAINTAINS INVENTORY
→ BROKER CLOSES / RECORDS OUTCOME
```

The next post-0068 reassessment should evaluate canonical PublicationReadiness/publish integration as the shortest safe next capability unless repository evidence reveals a higher-priority blocker. This closure does not itself authorize SLICE-0069 implementation.

## PROJECT_STATE freshness closure

This closure advances canonical state atomically to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0068
PROJECT_STATE_QUEUE_SLICE:    0069
```

SLICE-0069 is **UNSELECTED**. Queue numbering does not authorize readiness, implementation, `START_SLICE.bat` or a capability choice.

## Closure decision

```text
SLICE-0068 = OWNER_ACCEPTED
PROJECT_STATE_ACCEPTED_SLICE = 0068
PROJECT_STATE_QUEUE_SLICE = 0069
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
WORKFLOW_REASSESSMENT_STATUS = PASS
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
```

Implementation is merged. Closure becomes canonical only after this closure PR passes repository validation/CI, independent exact-head closure review and guarded merge. `FINISH_SLICE.bat` may run only after that closure merge.
