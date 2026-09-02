# SLICE-0040 — Marketplace Identity / Truth Boundary

**ID:** SLICE-0040  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** Native Marketplace Foundation — identity/truth boundary  
**Depends on:** SLICE-0039 terminal outcome accepted/closed; 2026-09-02 Architecture Rebaseline accepted/merged; `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md` controlling  
**Blocks:** later native-listing persistence, professional publishing eligibility, physical-vessel identity/dedup, listing lifecycle/freshness and market-observation integration

## Objective

Deliver exactly one inspectable domain capability:

> **Represent HullQ marketplace identities in code so BoatDesign reference, PhysicalBoat, MarketEpisode, NativeListing and ExternalMarketObservation remain structurally distinct; market appearances may remain unresolved until identity evidence exists, and linked appearances can reference a MarketEpisode only through the correct typed identity.**

This is the smallest executable marketplace identity boundary required by the accepted 2026-09-02 rebaseline. It does **not** build listing persistence, dedup, authorization, lifecycle, feeds or UI.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: typed marketplace identity separation plus explicit optional resolution links.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can run one deterministic offline command and inspect distinct identity namespaces, one PhysicalBoat with multiple MarketEpisodes, linked and unresolved market appearances, and a cross-kind raw-token collision that remains distinct.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The accepted reconciliation places the Marketplace Identity / Truth Boundary first after the architecture freeze. This slice stops before listing persistence, professional publishing eligibility, lifecycle/freshness, dedup, Auth0, media, leads, referrals, UI or source acquisition.

## Why this slice exists

The accepted architecture requires:

```text
BoatDesign
≠ PhysicalBoat
≠ MarketEpisode
≠ NativeListing
≠ ExternalMarketObservation
```

Later intake must also be able to create a NativeListing or ExternalMarketObservation **before** physical-vessel / MarketEpisode resolution is complete. Otherwise HullQ would be forced to invent identity merely to retain an appearance.

This slice therefore proves representation, not resolution.

## Controlling artifacts

Apply the post-SLICE-0039 precedence:

1. `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`;
2. `docs/PRIVATE_SELLER_POLICY_2026-09-02.md` where relevant;
3. `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`;
4. `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`;
5. `docs/PRODUCT_EXECUTION_PLAN_AMENDMENT_2026-09-01.md`;
6. non-conflicting older artifacts.

Retain strict truth, provenance, explicit `UNKNOWN`, configuration scope, source rights, ONE-CAPABILITY, VISIBLE-RESULT, slice isolation and exact-head review rules.

Existing immutable identity style in `src/hullq/domain/identity.py` may be reused, but existing Brand/Organization semantics must not be changed for convenience.

## Locked semantic boundary

### BoatDesign reference

Marketplace code may refer to an existing canonical BoatDesign ID, but this slice does not mint, merge, redefine or mutate BoatDesign records.

The marketplace-side BoatDesign reference must be runtime-distinct from every marketplace identity kind even when raw strings collide.

A PhysicalBoat may have a resolved BoatDesign reference or remain design-unresolved.

### PhysicalBoat

`PhysicalBoat` / `MarketVessel` is one specific vessel identity. It is not a BoatDesign, listing, market episode or observation.

One PhysicalBoat can participate in multiple MarketEpisodes over time.

No HIN/CIN/name/registration matching or ownership proof is implemented here.

### MarketEpisode

`MarketEpisode` is one sale/market episode for exactly one PhysicalBoat and must hold a typed PhysicalBoat reference.

Whether two periods are `SAME`, `NEW` or `UNRESOLVED` is a later resolution capability. No fixed time-gap rule may be introduced in this slice.

### NativeListing

`NativeListing` is a HullQ-hosted market appearance with its own identity.

It must support both states:

```text
UNRESOLVED -> no MarketEpisode link yet
RESOLVED   -> typed MarketEpisode link
```

This is an identity link only. It is **not** listing lifecycle/status. An unresolved identity link does not imply draft/inactive/stale, and a resolved identity link does not imply published/active.

This slice does not implement professional Organization ownership/publishing eligibility, price, status, media, contact data, persistence or public pages.

### ExternalMarketObservation

`ExternalMarketObservation` is one source-specific external market appearance with its own HullQ identity plus non-empty source identity and source-side listing/record key.

It must likewise support:

```text
UNRESOLVED -> no MarketEpisode link yet
RESOLVED   -> typed MarketEpisode link
```

No live source access, rights decision, adapter, dedup or automated resolution is authorized.

## Required behavior A — runtime-distinct identity kinds

Implement the smallest immutable representation for:

```text
BoatDesignRef
PhysicalBoatId
MarketEpisodeId
NativeListingId
ExternalMarketObservationId
```

These must be distinct at runtime, not merely static type aliases over interchangeable strings.

Hard invariant:

> Equal raw text in different identity kinds does not make the identities equal or interchangeable.

Wrong-kind references passed to domain constructors must fail closed.

Avoid a generic global `Entity(id, type)` bag if it weakens this guarantee.

## Required behavior B — immutable relationships and unresolved appearances

Use frozen/immutable domain value objects consistent with existing HullQ style.

Minimum relationship shape:

```text
PhysicalBoat -> optional BoatDesignRef
MarketEpisode -> PhysicalBoatId
NativeListing -> optional MarketEpisodeId
ExternalMarketObservation -> optional MarketEpisodeId
```

The model must naturally support:

```text
one PhysicalBoat -> multiple MarketEpisodes
one MarketEpisode -> one NativeListing + multiple external observations
unresolved NativeListing -> no invented MarketEpisode
unresolved ExternalMarketObservation -> no invented MarketEpisode
```

No repository/graph persistence is needed to prove this capability.

## Required behavior C — truth-scope non-projection

The new objects carry identity relationships only.

Do not add automatic copying/projection of BoatDesign or Configuration facts into PhysicalBoat, NativeListing or ExternalMarketObservation.

Forbidden implication:

```text
PhysicalBoat references BoatDesign X
therefore
BoatDesign X technical facts are physical/listing truth
```

No new physical-listing technical-fact model is invented in SLICE-0040.

## Required behavior D — representation is not resolution

Do not implement:

- HIN/CIN/name/registration matching;
- fuzzy similarity;
- broker/location/year heuristics;
- cross-source dedup scoring;
- automatic same-vessel merge;
- automatic same-episode merge;
- source authority/ranking;
- automatic resolution of NativeListing or ExternalMarketObservation.

Links used by the owner-test are explicitly constructed synthetic examples; the code under test must not infer them.

## Normative contract deliverable

Add:

```text
specs/MARKET_IDENTITY_CONTRACT.v0.1.md
```

It must contain only the locked identity semantics above. Do not expand it into lifecycle, freshness, authorization, dedup algorithms, media, leads, pricing or referral design.

Contract, code and tests must agree atomically.

## Minimal owner-test surface

Provide one deterministic offline command, normally:

```text
uv run python scripts/inspect_market_identity_boundary.py
```

It uses synthetic/local identities only and must visibly demonstrate something equivalent to:

```text
MARKETPLACE IDENTITY BOUNDARY

BoatDesignRef: ...
PhysicalBoat: ... -> BoatDesignRef ...
MarketEpisode A: ... -> PhysicalBoat ...
MarketEpisode B: ... -> PhysicalBoat ...
NativeListing linked: ... -> MarketEpisode A
NativeListing unresolved: ... -> UNRESOLVED
ExternalObservation linked: ... -> MarketEpisode A
ExternalObservation unresolved: ... -> UNRESOLVED

RAW TOKEN COLLISION ACROSS KINDS: PRESERVED DISTINCT
DESIGN FACTS PROJECTED TO PHYSICAL/LISTING TRUTH: NO
BOUNDARY RESULT: PASS
```

The script must exercise and verify the real domain objects; it may not print hard-coded PASS text without checking the invariants.

## Required tests

Focused tests must cover at least:

- every identity value object rejects empty identifiers;
- equal raw strings across identity kinds remain distinct;
- wrong-kind relationship references fail at runtime;
- PhysicalBoat supports a valid BoatDesignRef and an unresolved BoatDesign mapping;
- two distinct MarketEpisodes can reference one PhysicalBoat;
- NativeListing can remain unresolved;
- a resolved NativeListing accepts only MarketEpisodeId for its link;
- ExternalMarketObservation requires non-empty source identity and source-side record key;
- ExternalMarketObservation can remain unresolved;
- a resolved ExternalMarketObservation accepts only MarketEpisodeId;
- one MarketEpisode can be referenced by native and multiple external appearances without identity collapse;
- no automatic BoatDesign -> physical/listing technical-fact projection path is introduced;
- owner-test output is deterministic/offline;
- existing canonical identity/configuration/search tests remain green.

Do not add future lifecycle, authorization, dedup, freshness, media, lead or referral tests.

## In scope

- compact normative marketplace identity contract;
- immutable runtime-distinct identity value objects;
- minimal relationship-bearing domain records;
- optional MarketEpisode links for unresolved/resolved appearances;
- fail-closed runtime kind checks;
- deterministic offline owner-test;
- focused unit/contract tests;
- minimal package export changes only if required.

## Explicitly out of scope

- PostgreSQL schema/migrations/repositories;
- FastAPI/API endpoints;
- Astro/React UI;
- Auth0;
- Account/Organization/OrganizationMembership;
- broker publishing eligibility;
- `BrokerageRequest` / referral flow;
- listing lifecycle/status;
- freshness/reconfirmation;
- ListingSnapshot/ListingEvent;
- price/history/Days-on-Market;
- media;
- leads/contact routing;
- real broker inventory;
- external feed/API/crawler work;
- source-rights research;
- physical-vessel dedup/resolution;
- MarketEpisode continuity resolution;
- Saved Search/monitoring/alerts;
- pricing/entitlements;
- SEO/public pages;
- transaction/escrow/closing.

## Deliverables

1. `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`;
2. normally `src/hullq/domain/market_identity.py`;
3. normally `tests/unit/test_market_identity.py` plus only narrowly necessary contract tests;
4. `scripts/inspect_market_identity_boundary.py`;
5. this slice document updated to `REVIEW` on successful handoff.

Do not create persistence/API/frontend/integration scaffolding as placeholders.

## Acceptance criteria

- [x] Product execution checks remain `PASS` with no scope widening.
- [x] Compact normative market-identity contract exists without adjacent feature semantics.
- [x] BoatDesignRef, PhysicalBoatId, MarketEpisodeId, NativeListingId and ExternalMarketObservationId are distinct runtime identity kinds.
- [x] Equal raw tokens across different identity kinds remain distinct/non-interchangeable.
- [x] Wrong-kind relationship references fail closed.
- [x] PhysicalBoat can reference BoatDesign without becoming/mutating BoatDesign and may remain design-unresolved.
- [x] One PhysicalBoat can have multiple MarketEpisodes.
- [x] NativeListing is a distinct identity, may remain MarketEpisode-unresolved and, when resolved, accepts only a typed MarketEpisode link.
- [x] ExternalMarketObservation is source-specific, may remain unresolved and, when resolved, accepts only a typed MarketEpisode link.
- [x] One MarketEpisode can be referenced by native and external appearances without collapsing appearance identities.
- [x] No automatic BoatDesign/configuration -> physical/listing truth projection is introduced.
- [x] No dedup/identity-resolution or episode-continuity inference is implemented.
- [x] No persistence/API/auth/publishing/lifecycle/freshness/media/lead/referral/UI work is started.
- [x] Owner command verifies the real objects and reports `BOUNDARY RESULT: PASS` only if required invariants hold.
- [x] Owner command is deterministic/offline and requires no credentials/network.
- [x] Repository validation, ruff, mypy and full test suite pass; project coverage remains >=90%.
- [ ] Exact-head CI and Manufacturer artifact reproducibility are green before review acceptance where applicable. — NOT VERIFIED locally; requires remote CI observation on the exact final HEAD.
- [x] No SLICE-0041 or later work starts automatically.

## Expected touch points

Expected implementation paths are limited to:

- `docs/slices/SLICE-0040-marketplace-identity-truth-boundary.md`;
- `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`;
- `src/hullq/domain/market_identity.py`;
- `tests/unit/test_market_identity.py` and/or one narrowly justified contract test;
- `scripts/inspect_market_identity_boundary.py`;
- `src/hullq/domain/__init__.py` only if existing conventions require a minimal export.

If implementation requires modifying existing canonical BoatDesign/configuration/search/persistence semantics, STOP before widening scope.

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

Stop and report when:

- a higher-precedence accepted artifact materially contradicts this boundary;
- existing BoatDesign identity semantics would need modification;
- persistence/API is required merely to prove identity separation;
- professional publishing eligibility becomes necessary to pass this slice;
- relationship representation would require inventing dedup or episode-continuity policy;
- tests could pass only by projecting design/configuration truth into physical/listing truth;
- scope pressure pulls lifecycle, Freshness, media, leads, referrals, Auth0 or UI into SLICE-0040.

## Status handoff rule

The implementation agent may recommend/set `IN_PROGRESS`, `BLOCKED` or `REVIEW`, but MUST NOT mark this slice `DONE`.

`DONE` requires verified acceptance criteria, required external checks, independent review, explicit Project Owner acceptance and closure under `CLAUDE.md`.

## Required completion report

Use the exact structure in `docs/slices/SLICE_TEMPLATE.md`. Include exact final branch HEAD, actual validation results and unresolved findings. Do not start the next slice.