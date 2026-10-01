# Broker Sale / Outcome Close-out Contract v0.1

**Status:** ACCEPTED FOR SLICE-0074 READINESS  
**Scope:** professional NativeListing sale/outcome recording and close-out

## 1. Objective

Allow an authorized broker to explicitly record a sale/outcome for an Organization-owned NativeListing without conflating sale truth with lifecycle/freshness.

## 2. Controlling decisions

This contract implements owner-accepted D25 and D28 from `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` and REQ-BROKER-006.

## 3. Core invariants

1. WITHDRAWN alone never means SOLD.
2. Sale/outcome truth is explicit.
3. A SOLD report is publisher-scoped provenance-bearing truth, not automatic global MarketEpisode truth.
4. Achieved sale price is never inferred from asking price.
5. `recorded_at` is distinct from `sold_date`.
6. Corrections are explicit superseding revisions; history is immutable.
7. Recording SOLD on ACTIVE atomically records the outcome and transitions lifecycle ACTIVE → WITHDRAWN.
8. Recording SOLD on already-WITHDRAWN records the outcome while lifecycle remains WITHDRAWN.
9. Another Organization's listing for the same MarketEpisode is never auto-withdrawn.
10. Sale/outcome state is distinct from freshness and publication/current-public eligibility.

## 4. Required outcome identity / provenance

Each outcome revision must retain enough durable provenance to identify:

- NativeListing;
- publishing Organization;
- recorder Account;
- recorded_at;
- outcome kind;
- superseded/current revision relationship or explicit current head.

Where safely available, retain:

- resolved MarketEpisode at recording time;
- PhysicalBoat identity;
- optional originating Lead;
- optional responsible broker/member reference.

No optional linkage may be fabricated.

## 5. Initial outcome vocabulary

The owning implementation must support at least:

```text
SOLD
```

The implementation may support additional explicit non-sale close outcomes only if they are already unambiguous under accepted semantics and do not create a generalized CRM pipeline. Ordinary WITHDRAWN lifecycle remains separate and is not duplicated as an outcome.

## 6. SOLD fields

For SOLD:

- `sold_date`: optional;
- achieved amount: optional;
- achieved currency: required iff achieved amount is present;
- originating Lead: optional and must belong to the same Organization/listing context;
- responsible broker/member: optional and must be authorized/current where the implementation uses membership identity.

Unknown/unavailable values remain absent/unknown; the UI must not force fabricated values.

## 7. Concurrency and idempotency

Outcome mutation must be race-safe.

Required behavior:

- immutable revision append;
- explicit current outcome head;
- exact optimistic concurrency using expected current head/version;
- retry-safe operation identity or equivalent deterministic idempotency;
- reused operation identity with different payload conflicts;
- stale expected-head write conflicts rather than overwrites.

## 8. Authorization / tenancy

Only an authenticated account with current authorized access to the publishing Organization and the accepted broker role/MFA requirements may mutate outcome truth.

Foreign/unknown NativeListings remain non-enumerating.

Origin/CSRF/no-store/noindex rules follow the existing Broker Workspace boundary.

## 9. Lifecycle atomicity

For SOLD on ACTIVE:

```text
validate auth + tenancy + outcome payload + concurrency
→ append SaleOutcome revision
→ advance outcome head
→ append/record accepted lifecycle transition ACTIVE→WITHDRAWN
→ commit atomically
```

No commit-and-compensate sequence is allowed.

For SOLD on WITHDRAWN:

```text
append outcome revision + advance outcome head
→ lifecycle remains WITHDRAWN
```

DRAFT SOLD recording is rejected in v0.1 unless an existing accepted decision explicitly requires otherwise.

## 10. Read model / broker UX

The Broker Workspace must expose:

- current outcome status;
- recorded timestamp;
- optional sold date;
- optional achieved amount/currency;
- optional originating Lead reference where authorized;
- optional responsible broker context where supported;
- explicit close-out action for eligible listings;
- conflict/error state without silent overwrite.

The UI must make clear that closing as SOLD is distinct from ordinary Withdraw.

## 11. Public/Search behavior

A successful SOLD-on-ACTIVE operation withdraws the listing through the accepted lifecycle authority. Existing current-public eligibility then suppresses it through normal lifecycle rules.

Do not add a separate Search exclusion mechanism.

No new technical Search criterion is introduced.

## 12. MarketEpisode global outcome boundary

A publisher SOLD report does not create canonical global `ResolvedMarketEpisodeOutcome` truth in this slice.

Different publishers may report contradictory outcomes. Resolution of global episode truth remains a separate future evidence-based capability.

## 13. Lead linkage

When `originating_lead_id` is supplied:

- the Lead must exist;
- it must belong to the same Organization;
- it must reference the same NativeListing;
- foreign/mismatched Lead identity fails closed.

No lead must be invented merely because a sale is recorded.

## 14. Required retained proof

Retained real PostgreSQL + FastAPI + built Broker Workspace proof must demonstrate at least:

1. authorized ACTIVE listing close as SOLD;
2. lifecycle becomes WITHDRAWN atomically;
3. current outcome is readable;
4. optional sold date/achieved price are preserved exactly when supplied;
5. asking price is not copied into achieved price when omitted;
6. SOLD on already-WITHDRAWN succeeds without lifecycle rewrite;
7. foreign Organization access is non-enumerating;
8. stale expected-head conflict;
9. idempotent retry;
10. operation-id payload collision conflict;
11. mismatched originating Lead rejection;
12. second Organization listing for same MarketEpisode is untouched;
13. public listing disappears only through ordinary lifecycle/current-public semantics;
14. correction/superseding revision preserves prior outcome history.

## 15. Validation ownership

During implementation/amendment:

- local affected/focused tests;
- relevant PostgreSQL tests;
- targeted retained proof.

Final candidate:

- push exact HEAD;
- GitHub Actions performs authoritative complete regression.

No routine local full-suite run is required.

## 16. Scope exclusions

No payment, bulk import, engagement analytics, global MarketEpisode outcome resolution, owner-direct sale flow, generalized CRM/deal pipeline or new Search criterion.
