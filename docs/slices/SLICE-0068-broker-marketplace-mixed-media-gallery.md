# SLICE-0068 — Broker Marketplace Mixed-Media Gallery

**Type:** IMPLEMENTATION
**Status:** REVIEW
**Status set by this handoff:** `REVIEW`
**Stage:** Broker launch path — media/gallery
**Depends on:** SLICE-0067 owner-accepted / DONE
**Normative contract:** `specs/MARKETPLACE_MEDIA_GALLERY_CONTRACT.v0.1.md`

## Capability

Deliver the minimum viable Organization-controlled mixed-media gallery for existing marketplace NativeListings:

```text
Organization-owned NativeListing
→ validated JPEG/PNG/WebP media
→ Cloudflare R2 primary object storage via S3-compatible boundary
→ durable MediaAsset + MediaPlacement truth
→ ordering + explicit image cover
→ same-Organization reuse
→ structured YouTube gallery references
→ broker media workspace
```

This is the accepted execution-focus step B after SLICE-0067 promotion. It materially advances the Broker Creates → Adds Media → Publishes loop while keeping canonical PublicationReadiness/publish integration separate.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One coherent outcome only: an authorized broker manages Organization-controlled mixed-media gallery state for an existing NativeListing. Persistence, storage, API and UI work are inseparable layers of that single capability.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can open an Organization-owned marketplace listing, add multiple JPEG/PNG/WebP images, observe per-item processing/error state, order them, choose one explicit valid image cover, reuse eligible same-Organization media, add/remove a normalized YouTube reference, and re-read the authoritative gallery state.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
This is execution-focus step B immediately after accepted SLICE-0067 promotion. It advances BROKER CREATES → BROKER ADDS MEDIA while leaving canonical PublicationReadiness/publish integration as the next distinct launch-path capability.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Canonical origin/main after accepted SLICE-0067, D13–D15/D24/D29, broker-launch focus, Broker Workspace launch gate/register, current NativeListing/auth/lifecycle/public-read implementation, current migration/persistence patterns and existing tests were checked. No marketplace media/storage implementation already exists.

**TRIGGER GATES CHECK:** PASS  
SLICE-0068 adds no technical native Search criterion, starts no external production broker data/pilot/paid/public launch, and does not trigger Production Readiness.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; SLICE-0067 acceptance closure; `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` D13–D15/D24/D29–D31; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; Broker Workspace requirements/launch gate/mandatory capability register; post-0051 trigger gates; production-readiness gate; marketplace identity/public-read/lifecycle contracts.

**Production implementation checked:** current FastAPI app and broker Organization/MFA/PUBLISHER authorization boundary; professional promotion application/persistence; NativeListing persistence/lifecycle/inventory/public-read paths; Astro broker inventory workspace; current PostgreSQL/Alembic patterns; current web/API/persistence tests. No MediaAsset/MediaPlacement or marketplace object-storage implementation exists on origin/main.

**Already implemented / not re-decided:** NativeListing/PhysicalBoat/MarketEpisode identity; Organization ownership and publisher authorization; MFA; broker write-CSRF pattern; lifecycle-DRAFT promotion result; public NativeListing read surface; stateless application-host direction; two accepted technical Search criteria.

**Exact remaining gap:** an Organization-owned NativeListing has no durable media model, rights/processing state, object-storage boundary, gallery ordering/cover, same-Organization reuse, YouTube placement or broker-facing media workflow.

**Accepted-but-unimplemented obligations:** D13 MediaAsset/MediaPlacement; D14 uploader/provenance/rights and same-Organization reuse; D15 approved public-usable image + explicit image cover state; D24 retirement/purge-compatible lifecycle; D30 R2/S3-compatible storage and JPEG/PNG/WebP v0.1; D31 IMAGE+YOUTUBE mixed-media gallery with future direct VIDEO and virtual Broker-CI compatibility. D22 PublicationReadiness remains later.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` identity/auth/lifecycle/public-read foundations; `DECIDED_NOT_YET_IMPLEMENTED` media persistence/storage/rights/processing/gallery/reuse/YouTube; `EXPLICITLY_DEFERRED` canonical PublicationReadiness/publish integration, direct VIDEO upload, HEIC/HEIF, full Broker-CI administration, full D24 purge worker, cross-Organization grants, owner-direct media; `GENUINELY_OPEN` bounded implementation constants/adapter details only; `CONFLICT_OR_REGRESSION` none found.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

Broker Workspace Launch Gate remains `NOT_READY`. External broker self-service pilot, paid broker plan and public production launch remain not started.


### DECIDED_AND_IMPLEMENTED

- NativeListing/PhysicalBoat/MarketEpisode marketplace identity and persistence.
- Professional draft atomic promotion to Organization-owned lifecycle-DRAFT NativeListing.
- Organization/Membership/MFA/PUBLISHER authorization patterns.
- Broker Workspace private/no-store/non-enumerating boundary and write-CSRF pattern.
- Existing public NativeListing read path.
- D13–D15 and D24 media domain/rights/publication/retention direction.

### DECIDED_NOT_YET_IMPLEMENTED — owned here where stated

- D13 MediaAsset + MediaPlacement persistence and listing gallery use.
- D14 Organization media control/uploader/provenance/declared rights and same-Organization reuse.
- D15 approved rights-valid public-usable IMAGE state and explicit image-cover semantics; 0068 creates the media truth but does not implement canonical PublicationReadiness.
- D24 placement removal/asset retirement and data-model compatibility with later purge.
- D30 R2 primary media storage + S3-compatible provider boundary + JPEG/PNG/WebP v0.1.
- D31 mixed-media gallery: IMAGE + structured YOUTUBE now; future direct VIDEO and virtual Broker-CI architecture preserved.

### EXPLICITLY_DEFERRED

- D22 canonical PublicationReadiness and integrated publish flow: next launch-path capability after media.
- Direct uploaded-video processing/transcoding/streaming.
- HEIC/HEIF.
- full Broker-CI authoring/profile controls and actual virtual-slide rendering if no CI source exists yet.
- complete D24 retention scheduler/legal-hold/backup-purge worker.
- cross-Organization media usage grants.
- owner-direct media.
- leads/CRM and marketplace inventory fact/offer editing.

### GENUINELY_OPEN

Implementation-level choices that do not alter the normative invariants: exact finite upload byte/pixel limits; derivative dimensions/output encoding; library pagination shape; concrete table/index names; exact processing-state token names; direct presigned R2 vs bounded FastAPI-proxied v0.1 transport; local deterministic S3-compatible/fake test adapter.

These are implementation choices, not permission to weaken quarantine, validation, privacy, Organization isolation, rights or public-usability rules.

### CONFLICT_OR_REGRESSION

None found in current `origin/main` at readiness preparation. Repository history contains no implemented marketplace media/storage model that conflicts with D30/D31.

## Scope

Implementation may span:

- Alembic/PostgreSQL persistence;
- domain/application media models and orchestration;
- object-storage adapter/configuration;
- FastAPI broker media endpoints;
- Astro Broker Workspace media/gallery UI;
- public read composition only to the extent needed to prevent unsafe media exposure and/or expose already-public approved gallery state without changing publication eligibility;
- tests and retained inspection/proof.

Do not create a second auth stack, second listing identity, second publication-readiness definition or provider-specific domain identity.

## Mandatory implementation invariants

The implementation MUST satisfy every rule in `MARKETPLACE_MEDIA_GALLERY_CONTRACT.v0.1`, particularly:

1. Media attaches to NativeListing, never ProfessionalListingDraft.
2. PostgreSQL owns media metadata/truth; R2 owns bytes.
3. R2 is accessed through an S3-compatible boundary using server-owned opaque object keys.
4. Uploaded originals/quarantine are private and never public merely after upload.
5. JPEG/PNG/WebP only for v0.1; real decode/finite resource limits/metadata stripping/safe re-encode required.
6. Processing approval and rights authorization are independent.
7. Only approved + rights-valid IMAGE may be public-usable or cover.
8. exactly zero/one explicit valid IMAGE cover per listing.
9. same-Organization reuse may reuse bytes; cross-Organization access/reuse fails closed.
10. YouTube stores normalized structured identity, never broker HTML/embed code.
11. YouTube/future VIDEO/Broker-CI never satisfies the D15 image minimum.
12. direct VIDEO upload and HEIC remain deferred.
13. placement removal != asset deletion; retirement prevents new use/public usability and preserves D24 future purge.
14. concurrency/stale writes fail rather than silently overwrite ordering/cover.
15. partial storage/database failures never promote missing/unprocessed bytes to public truth.
16. existing Search/promotion/public-listing truth must not regress.

## Readiness stop conditions

Stop implementation and return for reassessment if any of these emerges:

- a need for new cross-Organization media-rights policy;
- a new public-publication eligibility rule beyond accepted D15/D22/D29;
- a need to redefine NativeListing/MediaAsset identity;
- a provider choice that would put storage-provider URLs/IDs into domain identity;
- a requirement for arbitrary third-party embeds;
- a requirement to implement direct uploaded-video transcoding in this slice;
- an irreversible migration not covered by this readiness contract.

## Acceptance

Independent exact-head implementation review must verify the normative contract and required proof matrix. Owner Acceptance remains mandatory before implementation merge. This readiness package does not authorize implementation until it is independently reviewed, remote gates are green and merged to `main`; the initial implementation prompt must then come only from `START_SLICE.bat`.
