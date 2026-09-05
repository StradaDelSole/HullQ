# HullQ — Current Project State

<!-- PROJECT_STATE_ACCEPTED_SLICE: 0045 -->
<!-- PROJECT_STATE_QUEUE_SLICE: 0046 -->

**Updated:** 2026-09-05  
**Latest owner-accepted / DONE slice:** SLICE-0045  
**Current queue:** SLICE-0046 — PhysicalBoat Identity Persistence; readiness is merged, implementation is not yet owner-accepted.  
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
- durable revisioned NativeListing offer-fact persistence for the nine `LISTING_OFFER` fields (SLICE-0045).

The accepted offer persistence includes explicit revision history/head semantics, optimistic concurrency, PostgreSQL integrity constraints, organization isolation and exact typed readback.

## What is not built yet

As of this state document there is still no completed public product surface for marketplace listings:

- no durable PhysicalBoat identity yet;
- no durable MarketEpisode yet;
- no NativeListing→MarketEpisode durable attachment yet;
- no PhysicalBoat marketplace fact persistence yet;
- no public FastAPI listing endpoint;
- no broker workspace/form;
- no public listing detail page;
- no media upload flow;
- no public lifecycle/freshness presentation.

This absence is now treated as a product-execution constraint, not merely a future roadmap note.

## Near-term execution path to first visible listing

The project must optimize for the shortest safe path to a listing that can be entered and viewed outside repository internals.

Current intended path:

```text
SLICE-0046
PhysicalBoat identity persistence

SLICE-0047
MarketEpisode persistence + controlled NativeListing attachment

SLICE-0048 target
first visible listing vertical slice:
minimal listing intake path + FastAPI read boundary + simplest public listing rendering
```

SLICE-0048 should prefer a deliberately narrow vertical slice over waiting for media, full broker workspace, lifecycle polish or every PhysicalBoat fact to be complete. A CLI/operator-assisted intake is acceptable for the first visible proof if it avoids blocking on full Auth0/workspace UX.

A later slice can replace that temporary intake with the proper Auth0-backed broker workspace.

At every post-slice architecture reassessment, the reviewer must explicitly ask:

1. How many slices remain to first visible listing?
2. Can the next proposed foundation capability be deferred until after that vertical slice?
3. Does the next slice reduce time-to-visible-product, or only increase architectural completeness?

A foundation slice that does not materially unblock the first visible listing requires explicit justification.

## Current queue — SLICE-0046

SLICE-0046 is intentionally narrow:

```text
PhysicalBoatId
+ optional existing canonical BoatDesignRef
+ created_at
```

The optional BoatDesignRef must reference the existing `canonical_boat_designs(id)` authority. An unresolved PhysicalBoat (`BoatDesignRef = NONE`) is valid.

SLICE-0046 must not add MarketEpisode, listing attachment, PhysicalBoat facts, HIN/CIN identity proof, broker ownership, automatic dedup/merge, API or UI.

Collision semantics are deterministic:

```text
existing PhysicalBoatId + same stored nullable BoatDesignRef
→ ALREADY_EXISTS

existing PhysicalBoatId + different nullable BoatDesignRef
→ CONFLICT

new PhysicalBoatId + unknown non-null BoatDesignRef
→ DESIGN_NOT_FOUND
```

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

Public URL/indexability/rendering decisions must preserve deterministic search semantics and avoid turning arbitrary facet combinations into indexable pages. Product-led SEO remains the primary zero-budget acquisition direction.

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

Do not introduce a second business-logic backend, dedicated search engine, Kubernetes/distributed infrastructure or paid managed dependency without measured need and an accepted decision.

## Development workflow

- `origin/main` is canonical shared truth.
- one implementation slice per isolated worktree/branch;
- Claude Code implements; independent reviewer verifies exact PR HEAD;
- material finding → `AMEND` on the same branch;
- clean exact-head review → `ACCEPT`;
- explicit Project Owner acceptance is mandatory before merge;
- acceptance closure follows the implementation merge;
- `FINISH_SLICE.bat` closes the local slice only after remote closure.

`docs/PROJECT_STATE.md` is mechanically freshness-gated by `scripts/validate_repository.py`: its `PROJECT_STATE_ACCEPTED_SLICE` marker must equal the highest accepted slice represented by an `SLICE-XXXX-acceptance-closure.md` file. Therefore each future acceptance closure that advances the accepted slice number must update this document in the same closure change or repository validation fails.

For exact historical evidence, hashes, amendments and CI runs, read the corresponding `docs/slices/SLICE-XXXX-acceptance-closure.md` rather than expanding this file into a second history log.
