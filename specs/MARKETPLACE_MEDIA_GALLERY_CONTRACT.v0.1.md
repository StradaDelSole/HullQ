# HullQ — Marketplace Mixed-Media Gallery Contract v0.1

**Status:** READINESS
**Owning slice:** SLICE-0068
**Subject:** Organization-controlled media for existing NativeListing marketplace inventory
**Controlling decisions:** D13–D15, D24, D29–D31 in `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md`

## 1. Capability outcome

SLICE-0068 delivers one coherent broker capability:

```text
authorized professional publisher
→ existing Organization-owned NativeListing
→ add/manage validated listing media
→ order media / choose explicit image cover
→ see durable mixed-media gallery state
```

It spans persistence, storage, application/API and Broker Workspace UI only as required for that outcome.

It does not implement canonical PublicationReadiness/publish integration, direct uploaded-video processing, full Broker-CI administration, lead handling, inventory fact/offer editing, owner-direct media, or a complete timed D24 purge/backup worker.

## 2. Identity and ownership

`MediaAssetId != MediaPlacementId != NativeListingId != PhysicalBoatId != MarketEpisodeId`.

A MediaAsset is controlled by exactly one uploading MarketplaceOrganization and records the uploader Account plus provenance/source and declared-rights state. Same-Organization reuse is explicit; same PhysicalBoat never grants reuse rights. Cross-Organization reuse is denied unless a future explicit usage-grant authority exists; 0068 does not invent that authority.

A MediaPlacement is listing-specific use of a MediaAsset/external media item and owns ordering/cover semantics. Removing a placement does not delete the asset.

Media attaches only to an existing marketplace NativeListing, never to ProfessionalListingDraft.

## 3. Authorization and isolation

All broker media reads/writes reuse the accepted authenticated Organization workspace boundary: current ACTIVE membership, required MFA and current PUBLISHER authorization for mutating marketplace media. Foreign Organization listing/asset identifiers and unknown identifiers remain non-enumerating.

State-changing browser requests reuse the accepted exact-Origin + distinct fixed non-simple-header CSRF pattern through FastAPI. No browser credential or R2 secret is exposed.

## 4. Media kinds in v0.1

### IMAGE

Accepted source formats: JPEG, PNG, WebP.

HEIC/HEIF, SVG, animated image semantics and arbitrary binary/document uploads are not accepted in v0.1. An implementation may reject animated input rather than preserve animation.

### YOUTUBE

A broker may add a supported YouTube URL/reference. HullQ parses and normalizes it to a bounded structured YouTube video identity. Arbitrary iframe/embed HTML, script, arbitrary external URL embedding and broker-controlled HTML are prohibited.

YouTube is gallery media but never satisfies D15's required public-usable image or cover.

### VIDEO

The domain/gallery representation must remain extensible to future direct uploaded video, but 0068 performs no broker video upload, transcoding, streaming or poster-frame pipeline.

### BROKER_CI

Not persisted as MediaAsset/MediaPlacement. It is a future virtual presentation slide generated from publishing-Organization public CI/profile state. It cannot be cover or satisfy any media readiness condition.

## 5. Object-storage boundary

Cloudflare R2 Standard is the initial primary marketplace-media object store.

Storage access is behind an S3-compatible HullQ boundary. Domain/persistence truth stores opaque object references/keys, not provider URLs as identity. Application hosts remain stateless and media bytes are not persisted on local host disk.

PostgreSQL stores authoritative MediaAsset/MediaPlacement metadata; image bytes live in object storage.

Provider credentials are server-side secrets only.

## 6. Image ingestion and trust boundary

An uploaded image begins non-public in private/quarantined object storage.

Client filename, extension, Content-Type and dimensions are untrusted hints. Before an image can become approved/public-usable, server-controlled processing must at minimum:

1. enforce bounded request/object size before unbounded buffering;
2. decode the file as a supported real image;
3. enforce bounded decoded dimensions/pixel count to prevent decompression/resource abuse;
4. reject unsupported/malformed content;
5. remove EXIF and other unnecessary embedded metadata, including location metadata;
6. safe-re-encode a public derivative in a supported controlled output format;
7. determine authoritative output MIME type/dimensions from processing;
8. compute/store a cryptographic content hash suitable for integrity/dedup support;
9. persist processing result/state atomically enough that database truth never claims a missing/unprocessed object is public-usable.

Original/quarantine objects are never directly public merely because upload succeeded. Public gallery delivery uses approved processed derivatives.

Exact byte/dimension limits and derivative dimensions are implementation constants/configuration with tests; they must be finite and operationally reasonable and may not weaken the above invariants. Changing them later is operational policy, not media identity.

## 7. Processing/public-usability state

The persistence model must mechanically distinguish at least non-public in-progress/failed state from approved state. A useful implementation may use states such as UPLOADING/QUARANTINED, PROCESSING, APPROVED and REJECTED, but exact token naming is implementation-owned provided no intermediate/failure state can be mistaken for APPROVED.

Rights state is independent of processing state. Rights UNKNOWN/not-declared never becomes publicly usable merely because processing succeeds.

A public-usable IMAGE requires both successful approved processing and a rights state that explicitly permits HullQ public display under the uploader's declaration/provenance model. 0068 must not silently manufacture rights authorization.

Rights/privacy invalidation makes an asset non-public immediately without waiting for physical purge.

## 8. Placement, order and cover

A listing may have multiple placements with deterministic explicit ordering. Reordering is a durable server-authoritative mutation with concurrency protection; stale writes do not silently overwrite newer order.

Exactly zero or one placement is the explicit cover at any instant. If present, the cover must be an approved, rights-valid public-usable IMAGE placement belonging to that listing. YouTube/future VIDEO/Broker-CI cannot be cover.

Removing/rejecting/retiring an asset that is cover must not leave a phantom cover reference. For ACTIVE listings, D15/D29 hard-current-public invariants remain controlling: a broker mutation may not knowingly remove the final valid public image without an atomic valid replacement. 0068 does not redefine lifecycle or auto-withdraw.

## 9. Same-Organization reuse

An authorized publisher may deliberately place an eligible asset controlled by the same Organization onto another Organization-owned listing without copying bytes. Reuse still creates listing-specific MediaPlacement/order/cover truth.

The asset library/read surface must never expose another Organization's assets. Content-hash equality does not authorize cross-Organization reuse or merge identity.

## 10. YouTube safety and durability

Accepted YouTube URL forms are parsed server-side into a canonical video identifier/reference. Rendering constructs the supported embed from that structured value; stored broker HTML is never rendered.

A YouTube placement records enough structured provenance to reproduce the reference and ordering. Availability/removal by YouTube is external availability, not evidence about yacht truth. Failure/unavailability of YouTube must not make an image cover disappear or satisfy/fail D15 image readiness by itself.

## 11. R2 upload mechanism

The implementation should avoid proxying large media bodies through Astro. FastAPI remains the authorization/application boundary.

A direct-to-R2 upload may use short-lived, narrowly scoped presigned operations after FastAPI creates/authorizes a pending MediaAsset/upload intent. Object keys are server-generated and Organization/listing/user filenames never choose storage authority. Completion/finalization must revalidate authoritative object metadata and run server-controlled processing before APPROVED.

If the implementation instead proxies bounded image bytes through FastAPI for v0.1 simplicity, it must preserve the same auth, size, quarantine, stateless-host and processing invariants and must not persist local disk state. Storage transport choice is not permission to bypass the application boundary.

## 12. Retirement/deletion boundary

0068 must support placement removal without equating it to asset deletion. Asset retirement must prevent new placement/reuse and make affected public usability fail closed as required by D24.

The schema/storage abstraction must preserve D24's future lifecycle `ACTIVE → RETIRED → PURGE_ELIGIBLE → PURGED` and allow originals, derivatives and independent backups to be purged later under the accepted conditions. A complete retention scheduler, legal-hold system and cross-provider purge worker are outside 0068.

## 13. Broker UI

The existing Broker Workspace gains an Organization-owned listing media/gallery surface reachable for marketplace inventory. It must support practical multi-file image selection/upload, visible per-item success/failure/processing state, retry without silently losing already successful items, gallery ordering, explicit cover selection, removal, same-Organization reuse, and YouTube add/remove.

The UI never invents success: after mutations it resolves authoritative server state. Private workspace responses remain no-store/noindex.

## 14. Public-surface boundary

0068 establishes media truth and gallery-ready data. It does not make a DRAFT listing public and does not replace canonical PublicationReadiness.

Existing public listing behavior must not accidentally expose quarantined, processing, rejected, rights-unknown, retired or foreign-Organization media. Any public-gallery integration included for already-legitimately-public existing inventory may expose only approved rights-valid public-usable placements and must preserve existing public eligibility semantics.

The next publication capability may consume this contract's canonical media state; it must not create a parallel media-readiness definition.

## 15. Broker-CI insertion rule

The gallery composition layer may later insert one virtual Broker-CI slide derived from stable `NativeListingId` plus publishing Organization CI state. Its position is deterministic for the same listing/gallery inputs rather than fresh runtime randomness. It is presentation-only and excluded from persisted placement order/count, cover and readiness calculations.

Full logo/colors/CI authoring is deferred.

## 16. Concurrency and failure

All metadata mutations are transactional and use explicit expected-version/head semantics or an equivalent race-safe authority. Object-storage operations cannot participate in the PostgreSQL transaction; therefore orchestration must be retry-safe and tolerate DB/object partial failure without promoting orphan/missing bytes to public truth.

Failed processing leaves a visible recoverable/rejected state and never silently discards other successful gallery items. Retrying an operation must not create uncontrolled duplicate placement/order/cover truth.

## 17. Required proof

Acceptance must prove at minimum:

- migration from the current accepted PostgreSQL head and persistence round-trip;
- Organization isolation/non-enumeration and current MFA/PUBLISHER authorization;
- supported image acceptance and unsupported/malformed/spoofed image rejection;
- finite size/pixel/decode limits;
- metadata/EXIF removal on public derivative;
- quarantine/non-public intermediate states never appear as public-usable;
- rights UNKNOWN does not become public-usable;
- multi-file partial failure preserves successful items and reports failures;
- deterministic ordering and stale reorder conflict;
- exactly-zero-or-one valid image cover invariant;
- YouTube normalization and arbitrary embed/HTML rejection;
- same-Organization reuse without byte duplication;
- cross-Organization asset reuse/read denied;
- placement removal does not delete shared asset;
- retirement prevents new placement and public use;
- R2 adapter uses opaque server-owned keys and no credential leakage;
- retained local/fake S3-compatible proof is deterministic; live Cloudflare credentials are not required in ordinary CI;
- broker browser workflow upload/order/cover/YouTube/retry reads authoritative state;
- existing Search count/semantics and draft-promotion behavior remain unchanged;
- repository validation, lint/type/tests and applicable PostgreSQL/browser suites pass.

## 18. Explicit non-goals

No canonical PublicationReadiness/publish integration; no owner-direct media; no direct uploaded VIDEO; no HEIC/HEIF; no arbitrary external embeds; no broker CI editor; no cross-Organization usage-grant system; no full automatic backup/purge scheduler; no media-based yacht fact extraction; no image ranking/scoring; no Search criterion; no lead/CRM capability.
