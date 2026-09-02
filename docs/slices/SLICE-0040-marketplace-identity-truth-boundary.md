# SLICE-0040 — Marketplace Identity / Truth Boundary

**ID:** SLICE-0040  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Native Marketplace Foundation — identity/truth boundary  
**Depends on:** SLICE-0039 terminal outcome accepted/closed; 2026-09-02 Architecture Rebaseline accepted/merged; `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md` controlling  
**Blocks:** later native-listing persistence, professional publishing eligibility, physical-vessel identity/dedup, listing lifecycle/freshness and market-observation integration

## Objective

Deliver exactly one inspectable domain capability:

> **Represent a HullQ marketplace identity chain in code so canonical BoatDesign identity, a specific PhysicalBoat, one MarketEpisode, a HullQ NativeListing and an ExternalMarketObservation remain structurally distinct and cannot be silently substituted or collapsed into one identity.**

This slice establishes the smallest executable marketplace identity boundary required by the accepted 2026-09-02 rebaseline. It does **not** build a listing marketplace, persistence layer, dedup engine, authorization system, lifecycle state machine or feed adapter.

The capability is successful when the Project Owner can run one deterministic offline command and inspect a concrete identity graph that proves the separate namespaces/references and the allowed one-to-many relationships without copying design facts into physical/listing truth.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: typed marketplace identity separation and explicit references between the accepted identity scopes.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can run one local command and inspect the exact BoatDesign → PhysicalBoat → MarketEpisode → market-appearance identity chain, including a raw-token collision proof and an unresolved external observation.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The accepted post-SLICE-0039 reconciliation explicitly places the Marketplace Identity / Truth Boundary first after the architecture freeze. This slice stops before professional publishing eligibility, listing persistence, lifecycle/freshness, dedup, Auth0, media, leads, referrals, UI or external-source acquisition.

## Why this slice exists

The marketplace pivot introduced several identities that must never be flattened:

```text
BoatDesign
≠ PhysicalBoat
≠ MarketEpisode
≠ NativeListing
≠ ExternalMarketObservation
```

Without an executable domain boundary, later listing persistence, feeds, dedup and market history could accidentally encode assumptions such as:

```text
one BoatDesign = one physical boat
one physical boat = one listing
one listing = one sale episode
same external/native identifier string = same entity
external observation = resolved physical identity
```

All of those are invalid under the accepted architecture.

SLICE-0040 therefore creates only the minimal typed identity primitives and relationships necessary to make those mistakes mechanically visible/rejectable before later marketplace capabilities depend on them.

## Controlling artifacts

Apply the post-SLICE-0039 precedence in this order where relevant:

1. `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`;
2. `docs/PRIVATE_SELLER_POLICY_2026-09-02.md` where public/private supply semantics are relevant;
3. `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`;
4. `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`;
5. `docs/PRODUCT_EXECUTION_PLAN_AMENDMENT_2026-09-01.md`;
6. non-conflicting older execution/architecture material.

Also retain all non-conflicting strict-truth, provenance, explicit-`UNKNOWN`, configuration-scope, source-rights, ONE-CAPABILITY, VISIBLE-RESULT, slice-isolation and exact-head review rules.

Existing identity implementation style may be reused from `src/hullq/domain/identity.py`, but this slice must not mutate Brand/Organization semantics merely to fit marketplace identities.

## Locked semantic boundary

### 1. BoatDesign reference

Marketplace code may refer to an existing canonical BoatDesign identity, but this slice must not redefine, mint, merge or mutate canonical BoatDesign records.

The marketplace-side reference must remain distinguishable from all marketplace entity IDs even if their raw string values happen to be identical.

A `PhysicalBoat` may have a resolved BoatDesign reference or no resolved BoatDesign reference yet. Absence of that mapping is permitted and must not be guessed.

### 2. PhysicalBoat

`PhysicalBoat` / `MarketVessel` represents one specific real vessel identity.

It is not:

- a BoatDesign;
- a listing;
- a market episode;
- an external observation.

One PhysicalBoat must be able to participate in more than one MarketEpisode over time.

No HIN/CIN/registration/name-based matching or ownership proof is implemented in this slice.

### 3. MarketEpisode

`MarketEpisode` represents one market/sale episode for exactly one PhysicalBoat.

It must hold an explicit typed reference to its PhysicalBoat identity.

This slice does not decide whether two observed periods are the same episode. The accepted future resolution vocabulary remains conceptually `SAME / NEW / UNRESOLVED`, but episode-continuity inference/resolution is out of scope here.

No universal time-gap rule may be introduced.

### 4. NativeListing

`NativeListing` represents a HullQ-hosted listing appearance and must remain a distinct identity from both PhysicalBoat and MarketEpisode.

For this boundary proof it must reference its MarketEpisode explicitly.

This slice does not implement:

- professional Organization ownership/publishing eligibility;
- draft/published state;
- price/status/media/contact data;
- persistence;
- public listing pages.

Those remain later capabilities.

### 5. ExternalMarketObservation

`ExternalMarketObservation` represents one source-specific external listing/market observation and must have its own HullQ identity plus explicit source identity and source-side listing/record key.

An external observation may remain **unresolved** with no MarketEpisode link.

If a MarketEpisode link is present, it must use the typed MarketEpisode identity and must not be inferred from a matching raw string alone.

No live source access, adapter, rights decision, dedup or automated resolution is authorized in this slice.

## Required behavior A — distinct typed identity namespaces

Implement the smallest immutable domain representation that makes the five accepted identity scopes explicit in code:

```text
BoatDesign reference
PhysicalBoat
MarketEpisode
NativeListing
ExternalMarketObservation
```

IDs/references must be type-distinct at runtime, not only type-checker annotations over interchangeable plain strings.

Required invariant:

> The same raw token used in two different identity namespaces does not make those identities equal or interchangeable.

Construction with a wrong identity kind must fail rather than silently accepting the raw value.

Do not introduce a generic global `Entity(id, type)` bag if that would allow accidental cross-kind substitution more easily than explicit types.

## Required behavior B — immutable explicit relationships

Use immutable/frozen domain value objects consistent with existing HullQ domain style.

At minimum the representation must support:

```text
PhysicalBoat -> optional BoatDesign reference
MarketEpisode -> PhysicalBoat
NativeListing -> MarketEpisode
ExternalMarketObservation -> optional MarketEpisode
```

It must also support these cardinality truths without special cases:

```text
one PhysicalBoat -> multiple MarketEpisodes
one MarketEpisode -> NativeListing + one or more external observations
one unresolved ExternalMarketObservation -> no MarketEpisode yet
```

Do not implement repositories or graph persistence merely to demonstrate these references.

## Required behavior C — truth-scope non-projection

This slice establishes identity relationships only.

It must not add a function or constructor that automatically copies technical BoatDesign/configuration facts into a PhysicalBoat, NativeListing or ExternalMarketObservation.

The owner-test/example must make the boundary visible: it may show an explicit BoatDesign reference, but physical/listing-specific technical facts remain absent unless a later capability introduces its own evidence-backed observation model.

The following implication is forbidden:

```text
PhysicalBoat references BoatDesign X
therefore
all BoatDesign X technical facts are true for this PhysicalBoat/listing
```

No new physical-listing technical truth semantics are invented here.

## Required behavior D — no identity resolution disguised as representation

This slice represents links; it does not decide them.

Do not implement:

- name/HIN/CIN/registration matching;
- fuzzy similarity;
- broker/location/year heuristics;
- cross-source dedup scoring;
- automatic same-vessel merge;
- automatic same-episode merge;
- source ranking/authority logic.

An unresolved external observation must remain representable without fabricating a PhysicalBoat/MarketEpisode link.

## Normative contract deliverable

Because this is a foundational domain boundary, implementation must add a compact normative contract:

```text
specs/MARKET_IDENTITY_CONTRACT.v0.1.md
```

The contract must record only the locked semantics in this slice; it must not expand into listing lifecycle, authorization, freshness, dedup algorithms, pricing, media or lead design.

Code/tests and this normative contract must agree atomically.

## Minimal owner-test surface

Provide one deterministic offline command, normally:

```text
uv run python scripts/inspect_market_identity_boundary.py
```

It must construct only synthetic/local example identities; no external network or production data is required.

The visible output must make at least the following inspectable:

```text
MARKETPLACE IDENTITY BOUNDARY

BoatDesignRef: ...
PhysicalBoat: ... -> BoatDesignRef ...
MarketEpisode A: ... -> PhysicalBoat ...
MarketEpisode B: ... -> PhysicalBoat ...
NativeListing: ... -> MarketEpisode A
ExternalObservation linked: ... -> MarketEpisode A
ExternalObservation unresolved: ... -> UNRESOLVED

RAW TOKEN COLLISION ACROSS KINDS: PRESERVED DISTINCT
DESIGN FACTS PROJECTED TO PHYSICAL/LISTING TRUTH: NO
BOUNDARY RESULT: PASS
```

Exact example IDs are implementation detail. The script must exercise the real domain objects, not print hard-coded PASS text without validating the relationships.

## Required tests

Focused tests must cover at least:

- every identity value object rejects an empty raw identifier;
- equal raw strings in different identity kinds remain non-equal/non-interchangeable;
- wrong-kind IDs passed to relationship constructors fail closed at runtime;
- PhysicalBoat may carry a valid BoatDesign reference or remain design-unresolved;
- two distinct MarketEpisodes can reference the same PhysicalBoat;
- a NativeListing references a MarketEpisode and cannot substitute a PhysicalBoat/BoatDesign/external-observation ID;
- an ExternalMarketObservation requires non-empty source identity and source-side listing/record key;
- an ExternalMarketObservation may remain unresolved with no MarketEpisode link;
- a resolved ExternalMarketObservation accepts only a MarketEpisode ID for that link;
- one MarketEpisode can be referenced by both one NativeListing and multiple distinct external observations without identity collapse;
- the domain representation contains no automatic BoatDesign -> physical/listing technical-fact projection path;
- the owner-test is deterministic and offline;
- existing canonical identity/configuration/search tests remain green.

Do not add tests for future lifecycle, publishing authorization, dedup matching, freshness, media, leads or referrals.

## In scope

- compact normative `MARKET_IDENTITY_CONTRACT.v0.1`;
- immutable typed marketplace identity primitives/references;
- minimal relationship-bearing domain value objects needed for the accepted identity chain;
- fail-closed runtime kind checks;
- deterministic synthetic owner-test command;
- focused unit/contract tests;
- only the smallest export/package changes needed to expose the new domain module.

## Explicitly out of scope

- PostgreSQL schema/migrations/repositories;
- API/FastAPI endpoints;
- Astro/React UI;
- Auth0 integration;
- Account/Organization/OrganizationMembership implementation;
- broker publishing eligibility/authorization;
- `BrokerageRequest` implementation;
- private-seller referral workflow;
- listing lifecycle/status;
- listing freshness/reconfirmation;
- ListingSnapshot/ListingEvent history;
- asking-price/history/Days-on-Market analytics;
- media upload/storage/quarantine;
- leads/contact routing;
- real broker inventory;
- external feeds/APIs/crawlers;
- source-rights research;
- physical-vessel dedup/resolution heuristics;
- MarketEpisode continuity resolution;
- Saved Search/monitoring/alerts;
- pricing/entitlements;
- SEO/public pages;
- transaction/escrow/closing.

## Deliverables

Expected bounded deliverables:

1. `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`;
2. one small domain module, normally `src/hullq/domain/market_identity.py`;
3. focused tests, normally `tests/unit/test_market_identity.py` and/or one contract test if needed;
4. `scripts/inspect_market_identity_boundary.py`;
5. this primary slice document updated to `REVIEW` on successful handoff.

Do not create persistence, API, frontend or marketplace-integration scaffolding as placeholders.

## Acceptance criteria

- [ ] Product execution checks remain `PASS` with no scope widening.
- [ ] A compact normative marketplace identity contract exists and contains no unapproved adjacent feature semantics.
- [ ] BoatDesign reference, PhysicalBoat ID, MarketEpisode ID, NativeListing ID and ExternalMarketObservation ID are distinct runtime identity kinds.
- [ ] Same raw token across different identity kinds remains distinct and cannot authorize cross-kind substitution.
- [ ] Wrong-kind relationship references fail closed at construction/runtime.
- [ ] PhysicalBoat can reference an existing BoatDesign identity without becoming or mutating that BoatDesign.
- [ ] PhysicalBoat may remain BoatDesign-unresolved without guessing.
- [ ] One PhysicalBoat can be represented with multiple MarketEpisodes.
- [ ] NativeListing remains a distinct identity and explicitly references a MarketEpisode.
- [ ] ExternalMarketObservation remains source-specific, distinct from NativeListing and may remain unresolved.
- [ ] One MarketEpisode can be referenced by both native and external appearances without collapsing those appearances into one entity.
- [ ] No automatic BoatDesign/configuration -> physical/listing technical-fact projection is introduced.
- [ ] No dedup/identity-resolution heuristic or MarketEpisode continuity inference is implemented.
- [ ] No persistence/API/auth/publishing/lifecycle/freshness/media/lead/referral/UI work is started.
- [ ] Owner command executes the real domain boundary and visibly reports `BOUNDARY RESULT: PASS` only after the required invariants are actually verified.
- [ ] Owner command is deterministic/offline and requires no credentials or network access.
- [ ] Repository validation, ruff, mypy and full test suite pass; project coverage remains >=90%.
- [ ] Exact-head CI and Manufacturer artifact reproducibility are green before review acceptance where those workflows apply.
- [ ] No SLICE-0041 or later capability is started automatically.

## Expected touch points

Expected new/modified paths are limited to:

- `docs/slices/SLICE-0040-marketplace-identity-truth-boundary.md`;
- `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`;
- `src/hullq/domain/market_identity.py`;
- `tests/unit/test_market_identity.py` and/or a narrowly justified contract test;
- `scripts/inspect_market_identity_boundary.py`;
- `src/hullq/domain/__init__.py` only if a minimal export is required by existing package conventions.

If implementation requires modifying existing canonical BoatDesign/configuration/search/persistence semantics, STOP and report the concrete blocker before widening scope.

## Validation

```text
uv run python scripts/inspect_market_identity_boundary.py
uv run python -m coverage run -m pytest
uv run python -m coverage report
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/validate_repository.py
```

## Stop conditions

Stop and report instead of inventing a solution when:

- an accepted higher-precedence artifact materially contradicts this slice boundary;
- representing the required identities would require changing existing canonical BoatDesign identity semantics;
- implementation requires a persistence schema or API to prove the identity boundary;
- professional publishing eligibility/Organization authorization becomes necessary to satisfy an acceptance criterion;
- a relationship cannot be represented without inventing dedup or episode-continuity policy;
- passing tests would require automatic promotion of design/configuration truth into physical/listing truth;
- scope pressure pulls Freshness, lifecycle, media, leads, referrals, Auth0 or UI into this slice.

## Status handoff rule

The implementation agent may recommend/set `IN_PROGRESS`, `BLOCKED` or `REVIEW` as appropriate, but MUST NOT mark this slice `DONE`.

`DONE` requires verified acceptance criteria, required remote/external checks, independent review, explicit Project Owner acceptance and closure under `CLAUDE.md`.

A successful implementation handoff therefore normally leaves this slice in `REVIEW`.

## Required completion report

Use the exact structure required by `docs/slices/SLICE_TEMPLATE.md`.

Keep the report concise. Include the exact final branch HEAD SHA, actual validation commands/results and unresolved findings. Do not start the next slice.