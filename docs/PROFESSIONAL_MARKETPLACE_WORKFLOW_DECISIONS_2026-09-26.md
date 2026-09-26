# HullQ — Professional Marketplace Workflow Owner Decisions

**Date:** 2026-09-26  
**Status:** OWNER_ACCEPTED PRODUCT / DOMAIN DIRECTION  
**Scope:** Professional draft promotion, marketplace identity, editing, media, outcomes, import and public-availability semantics  
**Implementation authorization:** NONE — each capability still requires normal reassessment, readiness, exact-head review and Owner Acceptance.

This record makes the Project Owner's accepted 2026-09-26 decision series durable in the canonical repository. It does not preassign slice numbers or authorize implementation outside a selected slice.

## D01 — PhysicalBoat resolution during professional promotion

Default: if no existing PhysicalBoat is safely proven, mint a new PhysicalBoatId.

Exception: reuse an existing PhysicalBoatId only when that exact PhysicalBoat is explicitly and safely resolved.

Never automatically merge a fuzzy/similar candidate. Under PhysicalBoat identity uncertainty, prefer duplicate over false merge.

## D02 — MarketEpisode resolution

- new PhysicalBoat -> create new MarketEpisode;
- known PhysicalBoat + proven same sale cycle -> reuse MarketEpisode;
- known PhysicalBoat + proven new sale cycle -> create new MarketEpisode;
- known PhysicalBoat + insufficient continuity evidence -> keep the NativeListing episode-unresolved.

Under MarketEpisode uncertainty, prefer UNRESOLVED over false SAME/NEW.

## D03 — Promotion atomicity

ProfessionalDraft -> marketplace materialization is one atomic transaction: validate readiness/auth/eligibility, resolve/create PhysicalBoat, resolve/create MarketEpisode as applicable, create NativeListing, create/reconcile PhysicalBoat claim head, create initial offer revision and required initial lifecycle state, then commit.

Any failure rolls back all newly created marketplace state.

Publication remains a separate explicit action: promotion produces NativeListing lifecycle DRAFT, not ACTIVE.

## D04 — Promoted draft provenance

A successfully promoted exact ProfessionalListingDraft version becomes immutable PROMOTED provenance linked to the resulting NativeListingId and leaves the active draft workflow.

Marketplace truth becomes the editable truth. The original promoted draft cannot be edited/reactivated. Duplicate/similar/relist workflows use a new ProfessionalListingDraftId, optionally safely prefilled.

## D05 — Promotion idempotency / identity allocation

Marketplace IDs are server-owned random identities.

Promotion uses exact expected draft version plus atomic lock/CAS. EDITABLE -> PROMOTED occurs exactly once and persists the resulting NativeListingId.

Retry of the same promoted draft returns the existing NativeListing; concurrent promotion is serialized. An optional operation ID may exist later but is not the primary domain guarantee.

## D06 — Promotion-ready vs publication-ready

There are two independent gates:

```text
private ProfessionalListingDraft
  -- PROMOTION_READY -->
Marketplace NativeListing DRAFT
  -- PUBLICATION_READY -->
ACTIVE
```

No required truth may be synthesized. Optional fields may remain absent. Omission is not explicit UNKNOWN.

## D07 — Minimum PROMOTION_READY responses

Required at promotion:

- concrete `physical_boat.marketed_brand_claim`;
- concrete `physical_boat.model_designation_claim`;
- explicit `physical_boat.build_year` response: VALUE_ASSERTION(year) or UNKNOWN;
- `listing_offer.asking_price_mode`;
- `listing_offer.location_country`;
- `listing_offer.broker_description`;
- when asking-price mode is AMOUNT: amount + currency.

Not required at promotion: boat_name, location_region, broker_listing_reference, BoatDesignRef or optional claims.

A confirmed BoatDesignRef may be linked; absence of a confirmed BoatDesignRef does not block promotion and must not cause BoatDesign truth to be copied into PhysicalBoat truth.

## D08 — Existing PhysicalBoat claim reconciliation during promotion

For a new PhysicalBoat, create the publishing Organization's initial claim revision.

For an existing PhysicalBoat with no claim head for that Organization, create an initial Organization claim head.

If the Organization's existing head is semantically identical, reuse it with no redundant revision.

If it differs, require explicit reconciliation: retain existing or explicitly update via a superseding immutable revision. Never silently supersede.

Other Organizations' claims remain independent and are never overwritten.

## D09 — NativeListing uniqueness per Organization + resolved MarketEpisode

For a resolved MarketEpisode, at most one NativeListing may exist for the same publishing Organization.

Different Organizations may each hold their own NativeListing for the same MarketEpisode.

The same Organization may hold a new NativeListing for the same PhysicalBoat only when a genuinely new MarketEpisode is resolved.

This supersedes/clarifies older wording that could be read as one global NativeListing per MarketEpisode. Enforcement must eventually be race-safe at the database boundary for resolved `(publishing_organization_id, market_episode_id)`.

## D10 — REPUBLISH vs RELIST

REPUBLISH means the same NativeListing + same MarketEpisode transitions from WITHDRAWN back to ACTIVE in a future explicitly implemented path.

RELIST means same PhysicalBoat + proven new MarketEpisode + new NativeListing.

Unresolved episode continuity must never be guessed into either path.

Republish must re-check current authorization, publishing eligibility, completeness and freshness; it is not a blind status toggle.

## D11 — Marketplace editing after promotion

One broker-facing edit experience may compose multiple truth authorities:

- offer changes -> new immutable NativeListingOfferRevision;
- PhysicalBoat changes -> new immutable publishing-Organization PhysicalBoat claim revision;
- both changed -> atomic combined save;
- unchanged subject -> no redundant revision;
- stale expected head -> CONFLICT, never overwrite.

Valid ordinary edits do not automatically withdraw an ACTIVE listing.

## D12 — Clone / relist / duplicate workflows

Relist this yacht:
- same PhysicalBoat;
- new MarketEpisode;
- new NativeListing;
- new ProfessionalListingDraft may be prefilled from current PhysicalBoat claims and prior offer;
- prior lifecycle/freshness/price-history/leads/analytics/outcomes/revision IDs are not copied as truth.

Create similar listing:
- new or unresolved PhysicalBoat;
- new draft;
- no concrete-yacht claims silently inherited.

Duplicate draft:
- new ProfessionalListingDraftId;
- copied private draft values;
- all identity/promotion checks still apply.

## D13 — Media domain architecture

Use independent MediaAsset plus listing-specific MediaPlacement.

MediaAsset owns stored media/provenance/processing metadata. MediaPlacement represents use in one NativeListing, including ordering and cover selection.

A legitimate asset may be deliberately reused across listings without byte duplication. PhysicalBoat association may aid provenance/reuse but does not make the PhysicalBoat own the asset and does not prove yacht facts.

Media is attached to real marketplace NativeListing DRAFT state, not to private ProfessionalListingDraft state.

## D14 — Media rights

MediaAsset is controlled by the uploading Organization and records uploader Account plus source/provenance and declared rights status.

Same Organization may deliberately reuse its authorized assets. Different Organizations cannot browse/reuse them by default, even for the same PhysicalBoat.

Cross-Organization reuse requires an explicit usage grant/authorization. Same PhysicalBoat grants no media rights.

Rights unknown -> not publicly usable.

HullQ receives only the service-use rights needed to store, validate, transform, derive, display and back up media; it does not acquire ownership or blanket redistribution rights.

## D15 — Media publication gate

Media is not required for PROMOTION_READY.

PUBLICATION_READY requires at least one approved public-usable rights-valid image and an explicit cover placement.

Uploading/quarantined/processing/rejected/rights-unknown media does not count.

For an ACTIVE listing, a broker mutation that would remove the final valid image should be rejected unless a valid replacement is part of the same safe change. Do not auto-withdraw merely for media invalidity.

## D16 — SLICE-0065 boundary / assertion prerequisite

Do not reopen SLICE-0065 for build-year UNKNOWN semantics.

Sequence direction:

```text
0065 Publication Input Alignment
-> Required-Response / Assertion Input Alignment
-> later Professional Draft Promotion
```

Normal post-slice reassessment still determines actual later slice selection.

## D17 — Draft build-year assertion representation

Keep the existing key `physical_boat.build_year`.

Canonical structured form:

```json
{"assertion_kind":"VALUE_ASSERTION","value":1987}
```

or:

```json
{"assertion_kind":"UNKNOWN"}
```

Omission remains mechanically distinct.

Legacy integer draft values remain readable and map internally to VALUE_ASSERTION(integer). Canonical new serialization/writes use the structured object.

The semantics are shared by OwnerDirect and Professional drafts. Introduce a small reusable assertion-response type but migrate only build_year in the owning slice; do not generalize every field prophylactically.

## D18 — Duplicate at promotion

If promotion discovers that this Organization already has a NativeListing for the same resolved MarketEpisode, treat it as duplicate conflict.

Do not adopt the existing listing into the second draft, do not mark that draft PROMOTED, do not mutate the existing listing and do not create another listing.

The second draft remains EDITABLE and the authorized broker may be shown/referred to the existing listing. Race-safe uniqueness resolves concurrent competing promotions.

## D19 — Broker listing reference after promotion

Preserve creation-time broker-reference provenance separately from the current operational broker reference.

Creation provenance is immutable. The current broker listing reference is Organization-controlled operational metadata with revision/concurrency semantics.

Broker reference is never marketplace identity, MarketEpisode/PhysicalBoat resolver, dedup key or cross-Organization ownership evidence and does not belong in offer revisions.

## D20 — Post-creation MarketEpisode resolution authority

Preserve immutable episode-at-creation provenance and add a separate immutable NativeListingEpisodeResolution revision history with one explicit current head.

Existing rows migrate deterministically: a non-null creation episode becomes the initial resolved head; creation NULL begins unresolved.

After this authority exists, current reads use exactly one resolution authority rather than mixing legacy creation-envelope episode values and new resolution state.

Corrections use explicit superseding revisions; never fuzzy/silent relinks.

## D21 — Correcting MarketEpisode on ACTIVE listing

An ACTIVE listing may receive an explicit immutable MarketEpisode-resolution correction while remaining ACTIVE only when the corrected episode belongs to the same PhysicalBoat.

Required checks include target existence, same PhysicalBoat, no same-Organization duplicate listing for target episode, expected current resolution head, authorization and explicit correction intent.

Correction to an episode belonging to a different PhysicalBoat is not an ordinary episode correction and must use a dedicated remediation path; never silently rebind PhysicalBoat identity.

## D22 — Canonical PublicationReadiness

Use one canonical PublicationReadiness domain evaluator for preflight UI and authoritative publish-time checks. Publish re-evaluates current truth inside the safe mutation boundary.

Minimum publication readiness includes:
- authorized publisher;
- Organization publishing eligibility ALLOWED;
- lifecycle DRAFT;
- current MarketEpisode resolution RESOLVED;
- referenced MarketEpisode and PhysicalBoat exist;
- current offer head exists;
- required offer responses valid;
- required PhysicalBoat responses valid;
- at least one approved rights-valid public image;
- explicit cover.

Required PhysicalBoat responses: marketed brand, model designation, build year VALUE_ASSERTION or explicit UNKNOWN. Boat name is optional.

Required offer responses: asking-price mode, location country, broker description and amount+currency when AMOUNT.

BoatDesignRef, Search-fit, technical Search completeness and multiple-photo quality are not publication blockers.

PublicationReadiness, PromotionReadiness, Search eligibility and listing-quality guidance remain distinct.

## D23 — Price-change events

NativeListingOfferRevision remains sole authoritative offer/price truth.

A semantic asking-price-state change atomically creates an immutable derived event tied to from_revision_id and to_revision_id. Description/location-only edits produce no price event.

Supported semantics must distinguish increase, decrease, AMOUNT->POA, POA->AMOUNT and currency change. Currency change is not classified as increase/decrease without a comparable basis.

The event is derived evidence, not independent price authority. Notification/subscription delivery is separate.

## D24 — Media retention/deletion

Removing a MediaPlacement removes only that listing use.

An Organization may retire an asset so it cannot be newly placed and is hidden from normal library use while retention/reference reasons remain.

Physical byte purge becomes eligible only after no active placement, no active usage grant, no applicable legal/security/moderation hold and required retention elapsed. Then originals at primary and independent backup storage plus derivatives may be removed.

Historical placement/provenance metadata and content hash may remain after byte purge.

Rights/privacy problems make the asset publicly unusable immediately, before physical purge completes.

Conceptual lifecycle: ACTIVE -> RETIRED -> PURGE_ELIGIBLE -> PURGED.

## D25 — Sale outcome

SaleOutcome is separate explicit truth; WITHDRAWN alone never means SOLD.

Recording SOLD on ACTIVE atomically records the explicit sale outcome and transitions ACTIVE -> WITHDRAWN. Recording SOLD on an already-WITHDRAWN listing records the outcome while lifecycle stays WITHDRAWN.

SaleOutcome is immutable/revisioned and may carry NativeListing, MarketEpisode, PhysicalBoat, Organization/account provenance, recorded_at and optional sold_date, achieved sale price/currency, originating lead and responsible broker.

recorded_at is not sold_date. Achieved sale price is never inferred from asking price. Corrections/undo are explicit superseding revisions.

## D26 — CSV / bulk import

Bulk import uses an explicit staging/mapping layer, never direct unreviewed marketplace writes.

Use ImportBatchId and ImportRowId. Rows are parsed/validated/classified before mutation.

Initial outcomes include CREATE_NEW_DRAFT, ALREADY_IMPORTED, CONFLICT_REVIEW and INVALID; controlled mapped-draft update may come later.

Durable recurring-source identity uses `(Organization + ImportSource + SourceRecordKey)` mapping. SourceRecordKey is not broker_listing_reference.

Similarity may suggest review but never auto-merge yacht identity. A source already mapped to promoted marketplace inventory does not create another draft/listing; changes route through normal reconciliation/edit semantics.

## D27 — Publisher / mandate change

A NativeListing has one immutable publishing principal.

Normal publisher/mandate change does not mutate `publishing_organization_id`. The old Organization preserves/withdraws its listing; the new Organization creates its own NativeListing.

The same proven MarketEpisode may therefore have listings from multiple Organizations under D09.

Leads and media do not automatically transfer. Cross-Organization media requires explicit usage grant.

Future co-brokerage is modeled as a separate professional relationship, not multiple owners of one NativeListing.

## D28 — Publisher sale report vs canonical MarketEpisode outcome

A publisher's SOLD report is a provenance-bearing SaleOutcomeReport, not immediate global MarketEpisode truth.

Reporting SOLD may close/withdraw that Organization's listing under D25 but does not automatically withdraw another Organization's listing for the same episode.

Canonical ResolvedMarketEpisodeOutcome is separate and evidence-based. Contradictory reports keep the episode outcome unresolved/conflicted until an accepted resolution process decides otherwise.

Achieved sale price reports likewise remain provenance-bearing reports unless separately resolved into canonical episode-level outcome truth.

## D29 — ACTIVE lifecycle vs current public availability

Lifecycle, freshness, publication readiness and current public availability are separate dimensions.

`ACTIVE` means the publisher has not withdrawn/closed the listing. It does not guarantee public visibility.

A canonical current-public-eligibility predicate evaluates current required conditions such as lifecycle, freshness, publisher eligibility, valid episode resolution, offer/content requirements, media rights/availability and applicable safety/moderation blocks.

If a required condition is lost externally or asynchronously, an ACTIVE listing is suppressed from public/current-market surfaces without rewriting lifecycle history.

Where a broker-controlled mutation would knowingly violate a hard ACTIVE public invariant, reject it or require an atomic replacement rather than accepting a broken state.

The private broker workspace must expose structured suppression/block reasons.

## Reassessment rule

These decisions are binding product/domain direction until explicitly superseded by a later Owner-accepted repository decision.

They do not mean every listed capability is due now. Each post-slice reassessment must classify relevant points as DECIDED_AND_IMPLEMENTED, DECIDED_NOT_YET_IMPLEMENTED, EXPLICITLY_DEFERRED, GENUINELY_OPEN or CONFLICT_OR_REGRESSION against current `origin/main`.
