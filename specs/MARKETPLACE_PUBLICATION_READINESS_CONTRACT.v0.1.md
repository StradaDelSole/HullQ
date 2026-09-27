# HullQ — Canonical PublicationReadiness + Current Public Eligibility Contract v0.1

**Status:** READINESS
**Owning slice:** SLICE-0069
**Subject:** one canonical publication-readiness authority, authoritative publish integration, and one canonical current-public eligibility authority for professional NativeListings
**Controlling decisions:** D15, D22 and D29 in `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md`

## 1. Capability outcome

SLICE-0069 closes the next broker-launch vertical:

```text
Organization-owned NativeListing DRAFT
+ current publisher authorization
+ complete required offer/PhysicalBoat truth
+ valid current episode link
+ approved rights-valid media + explicit cover
→ canonical PublicationReadiness preflight
→ authoritative in-transaction re-evaluation
→ DRAFT -> ACTIVE
→ canonical current-public eligibility
→ buyer-visible listing + public mixed-media gallery
→ Direct Search/current-market surfaces consume the same current-public authority
```

This slice replaces the legacy SLICE-0049 publication-completeness shortcut with the accepted D22 readiness truth and extends current-public eligibility from the SLICE-0052 lifecycle+freshness subset to D29's accepted current-public boundary.

It does not create a second lifecycle, second Search truth, second media model or second MarketEpisode-resolution model.

## 2. Separation of authorities

The following remain mechanically distinct:

```text
PromotionReadiness
!= PublicationReadiness
!= NativeListing lifecycle
!= freshness
!= CurrentPublicEligibility
!= technical Search fit
!= listing-quality guidance
```

### PublicationReadiness

Answers whether the current authorized publisher may transition this exact DRAFT NativeListing to ACTIVE now.

### CurrentPublicEligibility

Answers whether an already-ACTIVE NativeListing belongs on current buyer-facing/public-market surfaces now.

An ACTIVE lifecycle value alone is not current-public eligibility.

## 3. Canonical PublicationReadiness

Exactly one canonical domain/application readiness evaluator owns D22 semantics. Preflight UI and authoritative publish-time evaluation must use the same result vocabulary and requirement rules.

Minimum readiness is:

- current authenticated Account is currently authorized to publish for the selected Organization under the accepted professional workspace boundary;
- MFA/step-up requirement for the privileged Broker Workspace write surface is satisfied;
- accepted publishing eligibility evaluates ALLOWED for the exact Account + Organization + current Membership;
- persisted NativeListing exists and is owned by that Organization;
- lifecycle is DRAFT;
- current MarketEpisode resolution is RESOLVED under the currently implemented authority;
- referenced MarketEpisode exists;
- referenced PhysicalBoat exists;
- current NativeListing offer head exists;
- all D22 required offer responses are valid;
- the publishing Organization's current PhysicalBoat claim exists and all D22 required PhysicalBoat responses are valid;
- at least one approved rights-valid non-retired IMAGE placement exists;
- one explicit cover exists and is itself an approved rights-valid non-retired IMAGE placement on this listing.

No BoatDesignRef, technical Search-fit/completeness, multiple-photo quality, YouTube presence or Broker-CI slide is a publication blocker.

## 4. Current MarketEpisode resolution before D20

D20/D21 remain accepted but not yet implemented.

SLICE-0069 MUST NOT invent a temporary second episode-resolution table, status column or hidden fallback authority.

Until D20's revision authority exists, the only implemented current resolution authority is the immutable NativeListing creation-envelope `market_episode_id`:

```text
market_episode_id IS NULL
→ UNRESOLVED

market_episode_id IS NOT NULL
+ referenced MarketEpisode exists
+ referenced PhysicalBoat exists
→ RESOLVED for this pre-D20 boundary
```

When D20 is later implemented, PublicationReadiness/CurrentPublicEligibility must migrate to that one explicit current resolution head rather than mixing both authorities.

0069 does not implement episode correction/rebinding.

## 5. Required PhysicalBoat responses

Publication requires the publishing Organization's current PhysicalBoat claim for the exact PhysicalBoat.

Required:

- `marketed_brand_claim`: bounded non-blank accepted current value;
- `model_designation_claim`: bounded non-blank accepted current value;
- `build_year`: either:
  - `VALUE_ASSERTION` with a valid accepted year; or
  - explicit `UNKNOWN`.

Omitted build year is not publication-ready.

Boat name is optional.

LOA, draft, keel configuration and rudder configuration are not D22 publication blockers.

Truth remains concrete PhysicalBoat/publisher claim truth. BoatDesign/configuration values must never backfill a missing required concrete response.

## 6. Required offer responses

Publication requires the current NativeListing offer head.

Required:

- `asking_price_mode`;
- `location_country`;
- non-blank `broker_description`;
- when asking-price mode is `AMOUNT`: valid amount and currency;
- when asking-price mode is `POA`: amount/currency semantics must remain whatever the accepted NativeListingOffer domain requires for POA and must not be synthesized.

Optional offer fields remain optional according to their existing accepted assertion semantics.

PublicationReadiness must consume the authoritative typed current offer snapshot, not browser strings.

## 7. Required media state

Publication requires:

- at least one MediaPlacement kind IMAGE on this exact listing;
- its MediaAsset processing state APPROVED;
- rights state DECLARED/rights-valid under the accepted v0.1 model;
- asset not retired;
- approved derivative object reference present;
- one explicit `cover_placement_id`;
- the cover placement belongs to this listing and points to a currently public-usable IMAGE.

YOUTUBE and future VIDEO never satisfy the image minimum or cover requirement.

The virtual Broker-CI slide never participates in readiness.

0069 does not broaden rights semantics or implement D24 byte purge.

## 8. PublicationReadiness result shape

Readiness is never one ambiguous boolean.

The canonical result must at minimum contain:

- overall status: `READY` or `BLOCKED`;
- exact `NativeListingId`;
- lifecycle/current-state fact needed by the caller;
- a stable deterministic set/list of structured blocker reason codes when BLOCKED.

Reason codes must be machine-readable and presentation-neutral.

The implementation may group codes, but must preserve material distinctions including at least:

- actor/publishing authorization denial;
- Organization publishing ineligibility/unverified state;
- listing not found/foreign listing as one non-enumerating external shape;
- lifecycle not DRAFT;
- MarketEpisode unresolved/missing;
- PhysicalBoat missing;
- current offer missing;
- required offer response missing/invalid;
- current PhysicalBoat claim missing;
- marketed brand missing/invalid;
- model designation missing/invalid;
- build year omitted/invalid;
- no public-usable image;
- explicit cover missing;
- cover invalid/not public-usable.

The broker UI may translate reason codes into concise copy but must not recompute readiness.

## 9. Preflight and authoritative publish

A Broker Workspace preflight may evaluate readiness for display.

Preflight is advisory only.

Publish MUST re-evaluate current readiness inside the same safe mutation authority that performs DRAFT -> ACTIVE, after taking the locks needed to exclude relevant concurrent mutations.

A preflight READY result is never a capability token.

The authoritative mutation must serialize against concurrent changes that can alter readiness, including at minimum:

- lifecycle transition;
- current offer head replacement;
- current PhysicalBoat claim head replacement;
- media placement/cover/retirement changes relevant to readiness.

If full cross-table locking would create an unsafe global lock graph, implementation may use exact expected current head/version identities captured and rechecked under the NativeListing publication transaction, provided a concurrent readiness-changing commit cannot result in publication from stale truth.

Successful publication must atomically append the existing publication-transition evidence and set lifecycle ACTIVE exactly once.

No new NativeListing, MarketEpisode, PhysicalBoat, offer revision, PhysicalBoat claim or media asset is created by publish.

## 10. Existing SLICE-0049 lifecycle integration

`publish_native_listing()` remains the accepted lifecycle transition authority but its legacy private `_publication_completeness_satisfied` predicate is no longer sufficient after 0069.

0069 must refactor publish so the authoritative DRAFT -> ACTIVE transition consumes the canonical PublicationReadiness result/rules rather than maintaining a parallel SLICE-0049 completeness definition.

Withdraw semantics remain unchanged.

Reconfirm semantics remain unchanged.

WITHDRAWN -> ACTIVE remains unimplemented.

## 11. Canonical CurrentPublicEligibility

One canonical evaluator owns D29 current-public eligibility for current buyer-market surfaces.

For a NativeListing to be current-public eligible now, at minimum:

- lifecycle is ACTIVE;
- freshness is current under the accepted SLICE-0052 rule;
- publishing Organization still exists and its OrganizationPublishingEligibility is ELIGIBLE;
- current MarketEpisode resolution is RESOLVED under §4;
- referenced MarketEpisode/PhysicalBoat still resolve;
- current offer head exists and still satisfies D22 required offer-content requirements;
- current publishing-Organization PhysicalBoat claim exists and still satisfies D22 required required-response rules;
- media state still has at least one approved rights-valid non-retired IMAGE and an explicit valid cover;
- any implemented applicable safety/moderation hard block is absent.

Current actor membership/PUBLISHER role is NOT a buyer-public eligibility condition after publication; that is action authorization, not persistent publisher identity. Organization eligibility is a current-public condition.

No technical Search criterion/BoatDesign fit is part of CurrentPublicEligibility.

## 12. Suppression without lifecycle rewrite

If CurrentPublicEligibility becomes BLOCKED after publication, the listing stays lifecycle ACTIVE unless an explicit accepted lifecycle action changes it.

Buyer/current-market surfaces suppress it.

No automatic WITHDRAWN or SOLD inference occurs.

The private Broker Workspace must expose structured current-public suppression reasons so a broker can distinguish an ACTIVE-but-suppressed listing from a withdrawn listing.

## 13. Public listing read integration

The existing exact NativeListing public route/page must consume canonical CurrentPublicEligibility.

DRAFT, WITHDRAWN, missing and ACTIVE-but-currently-ineligible listings must remain non-enumerating on the public exact-listing surface.

A current-public eligible listing retains the accepted public offer/PhysicalBoat/publisher/freshness projection and additionally exposes a bounded public gallery projection.

No private MediaAsset provenance, object keys, uploader Account, rights internals, source note, hashes or quarantine/original metadata may be exposed.

## 14. Public mixed-media gallery projection

For one current-public eligible listing, public gallery composition may include:

### IMAGE

Only current public-usable IMAGE placements.

Expose stable placement/media identity only as required to construct listing-scoped public derivative URLs. Never expose R2/object keys.

### YOUTUBE

Expose only the normalized structured YouTube video ID/reference required to render the accepted embed. Never render broker-supplied HTML.

### BROKER_CI

If 0069 has enough existing Organization CI source data to render the previously accepted virtual Broker-CI slide without inventing a new CI-management model, it MAY insert it using the accepted deterministic listing-derived position rule.

If no such CI source exists, actual Broker-CI rendering remains deferred; gallery architecture must leave the virtual insertion layer available.

### VIDEO

Direct uploaded VIDEO remains deferred.

Persisted MediaPlacement ordering remains authoritative for persisted media. A virtual Broker-CI slide is presentation-only and never alters that order in PostgreSQL.

## 15. Public media-byte route

Public image delivery must be listing-scoped and fail closed.

A public derivative request must only succeed when:

- the requested listing is currently public eligible;
- the requested MediaAsset/placement belongs to that listing;
- placement kind is IMAGE;
- asset is currently public-usable;
- derivative object reference exists.

The route serves only the processed derivative.

It must never accept/expose a raw object key and must never serve the private original/quarantine object.

Object-storage retrieval failure yields bounded unavailable/not-found behavior and does not mutate lifecycle.

## 16. Search/current-market integration

Direct Search is a current-market surface and must consume the canonical CurrentPublicEligibility authority before technical classification/result inclusion.

Both accepted Search paths:

- pure `draft_max`;
- mixed `draft_max` / `keel_configuration`;

must stop treating `ACTIVE + freshness` as sufficient current inventory.

They must reuse one current-public eligibility function/service rather than independently reimplementing D29 conditions.

Technical Search classification/evidence rules remain unchanged after current-public admission.

Search criterion count remains exactly 2.

No listing excluded for current-public reasons is reclassified as technical `INSUFFICIENT_DATA`; it is outside current inventory before technical classification.

## 17. Broker Workspace integration

For Organization-owned inventory:

### DRAFT

Broker can see canonical PublicationReadiness and structured blockers before Publish.

Publish control may remain available while BLOCKED if failure reasons are visibly shown, or may be disabled for usability, but server-side authoritative publish re-evaluation is mandatory either way.

### ACTIVE

Broker sees lifecycle ACTIVE separately from current-public status.

When suppressed, structured reason(s) must be visible.

### WITHDRAWN

No republish path is introduced.

After successful publish, browser state is re-read from authoritative server state.

No client-side calculation may claim READY/current-public independently.

## 18. Concurrency model

0069 must document and test one deterministic lock/recheck order that composes with:

- NativeListing lifecycle locks;
- offer-head revision writes;
- PhysicalBoat claim-head revision writes;
- media asset/placement/gallery-head locks introduced by 0068.

Do not add a lock order that deadlocks with the accepted 0068 MediaAsset -> NativeListing -> gallery-head order.

Where PublicationReadiness spans multiple mutable authorities, either lock in a globally compatible order or use immutable/head/version identities plus final in-transaction recheck to prove stale READY cannot publish.

At minimum prove races against:

- offer revision concurrent with publish;
- PhysicalBoat claim revision concurrent with publish;
- media cover/remove/retire concurrent with publish;
- competing publish attempt.

## 19. Current-public media/object availability

The canonical database predicate treats an approved, rights-valid, non-retired image with a valid derivative object reference as media-eligible.

0069 is not required to make a synchronous R2 HEAD request for every listing/Search candidate.

Actual public byte delivery remains fail-closed at the listing-scoped derivative route. If a future durable object-availability/health state is added, D29 CurrentPublicEligibility must consume that state rather than inventing another public rule.

## 20. Safety/moderation boundary

D29 names applicable safety/moderation blocks. No new moderation domain is invented in 0069 if none exists on current `main`.

The CurrentPublicEligibility result must be extensible to a future accepted hard moderation/safety block without redefining lifecycle or Search truth.

Absence of an implemented moderation authority is not equivalent to a fabricated `APPROVED` moderation claim.

## 21. API boundary

0069 should expose a private Organization-scoped readiness read endpoint, e.g.:

```text
GET /api/broker/organizations/{organization_id}/inventory/{native_listing_id}/publication-readiness
```

Equivalent explicit scoping is acceptable.

Existing publish endpoint remains the mutation surface and returns structured publication-block reasons from canonical authoritative re-evaluation rather than only legacy `INCOMPLETE_LISTING`.

Public exact-listing API extends its projection with public gallery state only for current-public eligible listings.

Public image bytes use a listing-scoped route, e.g.:

```text
GET /api/listings/{native_listing_id}/media/{media_placement_id}
```

Equivalent non-enumerating listing-scoped paths are acceptable.

## 22. Required proof

Acceptance must prove at minimum:

### PublicationReadiness

- all D22 required conditions individually block when absent/invalid;
- BoatDesignRef/Search-fit/multiple-photo quality do not block;
- YouTube-only media does not satisfy image/cover readiness;
- rights UNKNOWN/rejected/retired image does not count;
- explicit valid image cover is required;
- preflight and publish use the same blocker vocabulary/rules;
- foreign/unknown listing remains non-enumerating.

### Publish atomicity/concurrency

- READY DRAFT publishes exactly once;
- BLOCKED DRAFT writes no lifecycle transition;
- stale preflight cannot bypass authoritative publish recheck;
- concurrent offer/head change cannot publish from stale required offer truth;
- concurrent PhysicalBoat claim-head change cannot publish from stale required boat truth;
- concurrent media remove/cover/retire cannot publish from stale media truth;
- competing publish produces one transition and one bounded conflict;
- no deadlock with accepted media lock order.

### Current public

- ACTIVE + current freshness + all accepted conditions → eligible;
- ACTIVE + stale/unknown freshness → suppressed;
- Organization becomes INELIGIBLE/UNVERIFIED → suppressed with lifecycle still ACTIVE;
- episode/offer/required claim/media/cover loss → suppressed without lifecycle rewrite;
- DRAFT/WITHDRAWN never public;
- Broker Workspace exposes structured suppression reasons.

### Public gallery

- only public-usable image derivatives appear;
- originals/object keys/provenance/uploader/source reference never leak;
- YouTube renders from normalized ID only;
- listing-scoped image route rejects foreign/unplaced/non-public asset IDs;
- object retrieval failure fails closed.

### Search

- both Search paths exclude current-public-ineligible listings before technical classification;
- Search evidence/criterion semantics remain unchanged for admitted candidates;
- technical Search criterion count remains 2.

### Regression

- SLICE-0067 promotion unchanged;
- SLICE-0068 media workspace unchanged except readiness/suppression information needed here;
- withdraw/reconfirm semantics unchanged;
- owner-direct draft remains unchanged;
- public publisher identity/freshness disclosures remain unchanged;
- repository validator, ruff, mypy, full PostgreSQL suite, web check/build/tests and retained vertical proofs pass.

## 23. Explicit non-goals

No D20/D21 episode correction history; no WITHDRAWN republish; no owner-direct publication; no offer/price editing capability; no broker inventory fact editing capability; no direct uploaded VIDEO; no HEIC/HEIF; no new media-rights model; no D24 purge worker; no cross-Organization media grants; no new safety/moderation system; no leads/CRM; no outcome workflow; no analytics; no bulk import; no payments; no new Search criterion or ranking.
