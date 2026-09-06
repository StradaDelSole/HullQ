# HullQ — Current Project State

<!-- PROJECT_STATE_ACCEPTED_SLICE: 0049 -->
<!-- PROJECT_STATE_QUEUE_SLICE: 0050 -->

**Updated:** 2026-09-06  
**Latest owner-accepted / DONE slice:** SLICE-0049  
**Current queue:** SLICE-0050 — capability not yet selected; post-0049 architecture/product reassessment required.  
**Exceptional historical state:** SLICE-0039 remains terminal `BLOCKED` and is not to be reopened.

This is the compact current-state entry point for HullQ. Historical implementation/review detail belongs in slice contracts, acceptance closures, retained research packages and Git history. Normative specs/ADRs remain authoritative where they apply.

## Product direction

HullQ is a native broker-first sailboat listing and technical-discovery marketplace.

Primary buyer loop:

```text
technical requirements
→ deterministic BoatDesign/configuration evaluation
→ native professional inventory
→ physical-boat/listing truth
→ save / monitor / alert
→ broker contact / qualified lead
```

Phase-1 public supply is broker/dealer/eligible-professional only. Independent private FSBO remains out of scope; a later owner-to-broker referral path may be added separately.

## Current architecture boundary

The accepted marketplace identity boundary is:

```text
BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId != ExternalMarketObservationId
```

Relationships:

```text
PhysicalBoat → optional BoatDesignRef
MarketEpisode → PhysicalBoatId
NativeListing → optional MarketEpisodeId
ExternalMarketObservation → optional MarketEpisodeId
```

Hard truth rule:

```text
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

No design fact becomes an individual-yacht fact merely because a PhysicalBoat references a BoatDesign.

## What is already built

The repository currently has accepted, tested foundations for:

- canonical sailboat identity/data contracts and PostgreSQL persistence;
- deterministic technical normalization/search behavior and provenance boundaries;
- source-rights gating and retained research/reproducibility paths;
- marketplace identity types and truth separation (SLICE-0040);
- Account / Organization / Membership publishing eligibility (SLICE-0041);
- Alembic as the sole forward migration path (SLICE-0042);
- durable immutable NativeListing identity persistence (SLICE-0043);
- Gate-1 marketplace fact/claim semantics and bounded field registry (SLICE-0044);
- durable revisioned NativeListing offer-fact persistence for the nine `LISTING_OFFER` fields (SLICE-0045);
- durable PhysicalBoat identity persistence with optional validated canonical `BoatDesignRef`, deterministic collision semantics and exact typed readback (SLICE-0046);
- durable MarketEpisode identity linked to exactly one PhysicalBoat plus PostgreSQL-backed optional NativeListing→MarketEpisode linkage (SLICE-0047);
- first browser-visible real listing preview vertical (SLICE-0048): operator-assisted intake, finite signed preview capability, FastAPI preview read model and Astro SSR page over real persisted listing data;
- first production-public NativeListing vertical (SLICE-0049): `DRAFT → ACTIVE → WITHDRAWN`, real SLICE-0041 transition authorization, immutable atomic publication history, public FastAPI exact-listing read and stable Astro SSR `/listings/{NativeListingId}` page without preview token or login.

The accepted PhysicalBoat persistence preserves unresolved identity (`BoatDesignRef = NONE`), permits sister ships to share one BoatDesign, rejects unknown design refs for new PhysicalBoat identities, and never projects BoatDesign baseline data into individual-yacht truth.

The accepted MarketEpisode/NativeListing linkage preserves the immutable NativeListing creation envelope: there is no post-creation attach/detach mutation. A NativeListing may remain unresolved with `market_episode_id = NONE`; when a non-null MarketEpisodeId is supplied for a new NativeListing it must already exist durably.

SLICE-0048 proved the internal/shareable application path:

```text
operator-assisted intake
→ PhysicalBoat
→ MarketEpisode
→ NativeListing
→ current LISTING_OFFER
→ finite signed preview capability
→ FastAPI
→ Astro SSR
→ browser-visible persisted listing
```

Its preview remains explicitly:

```text
PREVIEWABLE != PUBLISHED
DURABLE CREATION != PUBLICATION
```

SLICE-0049 now proves the production-public continuation:

```text
complete durable NativeListing
→ explicit authorized publish
→ DRAFT → ACTIVE
→ public FastAPI read
→ Astro SSR
→ /listings/{NativeListingId}
→ ordinary visitor can read without preview token
```

and controlled removal:

```text
ACTIVE
→ explicit authorized withdraw
→ WITHDRAWN
→ public API/web route becomes ordinary not-found
```

The accepted lifecycle is intentionally only `DRAFT → ACTIVE → WITHDRAWN`. Republish, `SOLD`, `ARCHIVED` and freshness/staleness semantics remain separate future capabilities.

All pre-0049 NativeListings migrate to `DRAFT`; no migration or creation path auto-publishes. Lifecycle state remains outside the accepted SLICE-0043 immutable creation envelope/content hash, so exact creation retries remain idempotent after `ACTIVE` and `WITHDRAWN` changes.

Every successful publication transition atomically appends immutable publication history. Denied, failed, stale or unsupported transitions change neither state nor history. Competing same-state transitions are serialized through PostgreSQL so only one succeeds.

## What is not built yet

Important marketplace/product capabilities still absent include:

- authenticated Auth0-backed broker workspace/form;
- persisted marketplace actor directory beyond accepted runtime eligibility types;
- PhysicalBoat marketplace fact persistence beyond identity;
- media upload/storage/presentation;
- public listing search/ranking over native inventory;
- lead/contact workflow;
- saved-search monitoring/alerts and price-history intelligence;
- republish, SOLD/ARCHIVED and freshness/staleness lifecycle behavior;
- full listing SEO/indexation/sitemap/hreflang distribution semantics beyond the bounded 0049 noindex NativeListing page-class decision.

## Accepted SLICE-0049 result

SLICE-0049 was selected after the post-0048 architecture/product reassessment because the accepted 0048 preview proved the persisted application path but deliberately stopped at `PREVIEWABLE != PUBLISHED`.

The accepted 0049 capability closes that bridge without pulling in broker authentication, search/discovery, media or broad SEO work.

Publication authorization reuses the real SLICE-0041 evaluator for every transition and requires the candidate Organization to match the NativeListing's durable owning `publishing_organization_id`.

The publication completeness predicate requires the durable chain:

```text
NativeListing
→ MarketEpisode
→ PhysicalBoat
+ explicit current LISTING_OFFER head
```

and never promotes BoatDesign/model facts into individual-yacht truth.

The public API/web surface resolves only complete `ACTIVE` listings. `DRAFT`, `WITHDRAWN`, missing and incomplete identities intentionally collapse to the same ordinary external not-found behavior.

The production public page identity is:

```text
/listings/{NativeListingId}
```

No slug is introduced. Query parameters do not alter listing identity or lifecycle/content selection. The page is public but deliberately `noindex` in this slice.

The existing SLICE-0048 preview route remains a separate finite bearer capability with private/no-store, no-referrer, non-canonical and noindex behavior.

## Current queue — SLICE-0050

SLICE-0050 is intentionally unassigned at acceptance closure time.

Before readiness is written, perform a post-0049 product/architecture reassessment and select exactly one highest-leverage continuation of the buyer/broker loop.

Candidate capability families include, without pre-selecting the answer:

1. broker operating surface / authenticated intake and management;
2. richer PhysicalBoat/listing facts needed for useful buyer decisions and filtering;
3. minimal native-inventory search/discovery over public listings;
4. media where materially blocking the chosen product loop;
5. buyer save/monitor/contact capability.

The next slice must be chosen by direct product leverage rather than foundation completeness. Do not start SLICE-0050 until readiness is explicitly defined, independently exact-head reviewed and merged.

## Marketplace fact semantics already frozen

The accepted SLICE-0044 contract preserves these distinctions:

```text
UNKNOWN != ABSENT != NO_KNOWN_HISTORY_DECLARED
BROKER_CLAIM != VERIFIED_FACT
DOCUMENT_AVAILABLE != DOCUMENT_VERIFIED
DESIGN_REFERENCE != PHYSICAL_BOAT_TRUTH
```

Assertion semantics and resolution/provenance remain separate dimensions.

Sensitive claims such as ownership/title, VAT/tax, major accident/damage/grounding, insurance, osmosis/latent-defect and survey-like condition claims remain conservative and display-only until field-specific policy is accepted.

`broad_use_history` is open-world positive multi-value history: omission of a category is not a negative assertion.

## Search and SEO

Search architecture and SEO remain part of product architecture, not later marketing.

SLICE-0048 preview routes remain excluded from canonical public SEO architecture.

SLICE-0049 accepts only the first bounded NativeListing public page class: `/listings/{NativeListingId}` uses the stable domain identity, introduces no slug and remains deliberately `noindex`. Query parameters are non-canonical and cannot change the selected listing/content/lifecycle truth. No alternate/legacy listing grammar was invented.

It does not authorize NativeListing sitemap publication, hreflang trees, faceted landing pages, broad structured-data expansion or full resolution of OQ-018.

Production public URL/indexability/rendering decisions beyond that bounded page class must preserve deterministic search semantics and avoid turning arbitrary facet combinations into indexable pages.

Mandatory public languages remain:

- English;
- German;
- French;
- Portuguese;
- Spanish.

Canonical IDs, technical values, provenance and query semantics remain language-neutral.

## Monetization direction

Search stays broadly open; persistence, monitoring and intelligence are preferred monetization surfaces.

Current framing:

```text
HullQ Free — Search everything. Save 5 searches.
```

Potential Pro surfaces include expanded saved searches, monitoring/alerts and, when rights/data permit, listing price history, price-change alerts, model/generation/configuration market trends, Days-on-Market and price-reduction signals.

## Accepted application architecture

```text
Cloudflare edge
      |
      v
portable Linux VPS
      |
      +-- Astro + TypeScript web
      |     \-- React islands where justified
      +-- FastAPI / CPython 3.14
      +-- PostgreSQL 18
      +-- scheduled/background Python worker when justified
      \-- simple VPS deployment / Caddy baseline
```

SLICE-0048 is the first accepted implementation of the FastAPI + Astro application surface; SLICE-0049 adds its first production-public NativeListing route on that same boundary. Do not introduce a second business-logic backend, dedicated search engine, Kubernetes/distributed infrastructure or paid managed dependency without measured need and an accepted decision.

## Development workflow

- `origin/main` is canonical shared truth.
- one implementation slice per isolated worktree/branch;
- Claude Code implements; independent reviewer verifies exact PR HEAD;
- material finding → `AMEND` on the same branch;
- clean exact-head review → `ACCEPT`;
- explicit Project Owner acceptance is mandatory before merge;
- acceptance closure follows the implementation merge;
- `FINISH_SLICE.bat` closes the local slice only after remote closure.

`docs/PROJECT_STATE.md` is mechanically freshness-gated by `scripts/validate_repository.py`: its `PROJECT_STATE_ACCEPTED_SLICE` marker must equal the highest accepted slice represented by an `SLICE-XXXX-acceptance-closure.md` file. Therefore each acceptance closure that advances the accepted slice number must update this document in the same closure change or repository validation fails.

The queue contract is also validated so merged readiness remains startable while a genuine implementation handoff may move the active slice to `REVIEW`/`BLOCKED` only with the required handoff marker.

For exact historical evidence, hashes, amendments and CI runs, read the corresponding `docs/slices/SLICE-XXXX-acceptance-closure.md` rather than expanding this file into a second history log.
