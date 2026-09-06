# HullQ — Current Project State

<!-- PROJECT_STATE_ACCEPTED_SLICE: 0048 -->
<!-- PROJECT_STATE_QUEUE_SLICE: 0049 -->

**Updated:** 2026-09-06  
**Latest owner-accepted / DONE slice:** SLICE-0048  
**Current queue:** SLICE-0049 — post-0048 architecture/product reassessment pending; no readiness or implementation capability is authorized yet.  
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
- first browser-visible real listing preview vertical (SLICE-0048): operator-assisted intake, finite signed preview capability, FastAPI preview read model and Astro SSR page over real persisted listing data.

The accepted PhysicalBoat persistence preserves unresolved identity (`BoatDesignRef = NONE`), permits sister ships to share one BoatDesign, rejects unknown design refs for new PhysicalBoat identities, and never projects BoatDesign baseline data into individual-yacht truth.

The accepted MarketEpisode/NativeListing linkage preserves the immutable NativeListing creation envelope: there is no post-creation attach/detach mutation. A NativeListing may remain unresolved with `market_episode_id = NONE`; when a non-null MarketEpisodeId is supplied for a new NativeListing it must already exist durably.

SLICE-0048 proves the complete application path:

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

The preview URL is time-bounded, bearer-capability gated, non-indexed, non-canonical and protected by no-store/no-referrer rules. It does not create production publication/lifecycle semantics.

## What is not built yet

Important marketplace/product capabilities still absent include:

- production publication/lifecycle state (`publish`, `withdraw`, `sold`, freshness/expiry policy);
- canonical/indexable public listing URL semantics;
- authenticated Auth0-backed broker workspace/form;
- persisted marketplace actor directory beyond accepted runtime eligibility types;
- PhysicalBoat marketplace fact persistence beyond identity;
- media upload/storage/presentation;
- public listing search/ranking over native inventory;
- lead/contact workflow;
- saved-search monitoring/alerts and price-history intelligence.

These are candidates for post-0048 prioritization, not implied requirements for the accepted preview proof.

## Product execution checkpoint after SLICE-0048

The previous execution target has been achieved:

```text
FIRST BROWSER-VISIBLE REAL LISTING = BUILT
```

There is therefore no longer a valid reason to keep the old “distance to first visible listing” metric as the controlling queue rule.

Before authorizing SLICE-0049, perform a fresh architecture/product reassessment and choose the next capability by direct product leverage. The reassessment must explicitly compare at least:

1. production publication/lifecycle + canonical public listing page;
2. broker intake/workspace/authentication;
3. minimal native-inventory search/discovery;
4. PhysicalBoat marketplace fact capture needed for useful buyer filtering;
5. media, only if it materially blocks the chosen next buyer/broker loop.

Do not automatically choose architectural completeness. Prefer the smallest capability that turns the accepted 0048 proof into a more usable market loop.

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

SLICE-0048 preview routes are deliberately excluded from canonical public SEO architecture. Production public URL/indexability/rendering decisions must preserve deterministic search semantics and avoid turning arbitrary facet combinations into indexable pages.

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

SLICE-0048 is the first accepted implementation of the FastAPI + Astro application surface. Do not introduce a second business-logic backend, dedicated search engine, Kubernetes/distributed infrastructure or paid managed dependency without measured need and an accepted decision.

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
