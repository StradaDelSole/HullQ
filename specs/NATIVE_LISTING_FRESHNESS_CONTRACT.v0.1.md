# HullQ — NativeListing Freshness / Reconfirmation Contract v0.1

**Status:** READY CONTRACT — controls SLICE-0052 implementation when merged  
**Scope:** manual/operator-assisted native professional listings only  
**Relationship to lifecycle:** freshness is a separate state dimension; this contract does not add or reinterpret lifecycle states  
**Normative requirements:** `specs/NATIVE_LISTING_FRESHNESS_REQUIREMENTS.v0.1.md`

## 1. Purpose

HullQ already has durable/public `NativeListing` lifecycle and buyer-facing native-inventory Search. Those accepted paths currently gate current-market visibility on `lifecycle == ACTIVE`, while the accepted marketplace architecture states:

```text
ACTIVE does not automatically mean CURRENTLY CONFIRMED
STALE != SOLD
DISAPPEARED != SOLD
```

This contract adds the smallest production freshness/reconfirmation capability needed to stop an indefinitely old `ACTIVE` listing from continuing to appear as current inventory.

It does not add broker authentication, alerts, scheduling, feed-driven freshness, `SOLD`, `ARCHIVED`, republish, price history or a generic monitoring framework.

## 2. Hard state separation

The accepted lifecycle remains exactly:

```text
DRAFT
ACTIVE
WITHDRAWN
```

SLICE-0052 adds freshness vocabulary only:

```text
CONFIRMED
DUE_FOR_CONFIRMATION
STALE
UNKNOWN
```

Hard invariants:

```text
LifecycleState != FreshnessStatus
STALE does not mutate lifecycle to WITHDRAWN
STALE does not imply SOLD
UNKNOWN does not imply withdrawn, sold or unavailable
reconfirmation does not create a lifecycle transition
```

`ACTIVE` continues to mean that the listing is in the published lifecycle state. After this contract, `ACTIVE` alone no longer proves current-market eligibility: buyer visibility additionally requires admissible freshness under §7. This narrows the current-market read/Search predicate without rewriting lifecycle history or adding a new lifecycle state.

Freshness is evaluated only for an `ACTIVE` NativeListing. DRAFT/WITHDRAWN listings remain non-public under the existing lifecycle rules and do not gain public visibility through freshness state.

## 3. Manual native freshness policy v1

The production policy introduced by this contract is named:

```text
MANUAL_NATIVE_V1
```

Its exact timing is:

```text
confirmation TTL = 30 days
grace period     = 7 days
stale boundary   = 37 days after effective confirmation
```

For an exact timezone-aware UTC `as_of` and effective `confirmed_at`:

```text
confirmed_at <= as_of < confirmed_at + 30 days
    -> CONFIRMED

confirmed_at + 30 days <= as_of < confirmed_at + 37 days
    -> DUE_FOR_CONFIRMATION

as_of >= confirmed_at + 37 days
    -> STALE
```

If there is no admissible confirmation evidence, freshness is `UNKNOWN`.

If a stored/effective confirmation timestamp is later than the evaluation `as_of`, evaluation MUST fail closed to `UNKNOWN`; it MUST NOT manufacture a negative age or treat future evidence as current confirmation.

Production timestamps are UTC. Tests MUST exercise the exact 30-day and 37-day boundaries, not approximate day counts.

A later policy change is a versioned product-policy change; implementation MUST NOT silently mutate `MANUAL_NATIVE_V1` constants to change historical semantics.

## 4. Confirmation evidence

Freshness is evidence-backed. The effective confirmation time is the latest admissible timestamp from:

1. the accepted immutable `DRAFT -> ACTIVE` publication transition for that NativeListing; and
2. any later successful explicit NativeListing reconfirmation event introduced by this contract.

The original publication transition is accepted as the initial confirmation evidence because publishing is an explicit authorized assertion that the listing is ready to enter the current market. This does not mean lifecycle and freshness are the same state dimension.

### 4.1 Existing ACTIVE listings

Migration/deployment MUST NOT reset an existing ACTIVE listing to "fresh now" merely because SLICE-0052 is deployed.

For a pre-SLICE-0052 ACTIVE listing:

```text
recorded DRAFT -> ACTIVE transition occurred_at
-> initial confirmed_at
-> current status derived from its real age under MANUAL_NATIVE_V1
```

If an ACTIVE row has no admissible publication-transition evidence, its freshness is `UNKNOWN` and it is excluded from current-market buyer surfaces until an authorized explicit reconfirmation succeeds.

### 4.2 Reconfirmation event

One successful reconfirmation MUST append an immutable audit record containing at least:

```text
FreshnessConfirmationId
NativeListingId
actor AccountId
publishing MarketplaceOrganizationId
occurred_at
```

`occurred_at` is system/database recorded; a caller MUST NOT be able to backdate or future-date confirmation by supplying an arbitrary timestamp.

A caller-supplied stable `FreshnessConfirmationId` MUST make an exact retry idempotent:

```text
same id + same immutable envelope -> ALREADY_EXISTS
same id + different immutable envelope -> CONFLICT
```

For idempotency/collision comparison, the caller-controlled immutable envelope is exactly the NativeListing/principal identity being reconfirmed; the system-generated `occurred_at` is **not** part of that comparison. An exact retry MUST retain the original persisted `occurred_at` rather than generating a new semantic event or conflicting merely because wall-clock time advanced.

The earlier record is never rewritten.

No separate mutable freshness current-head record is required by this contract. Effective freshness is derived from immutable publication/reconfirmation evidence plus the policy and `as_of`; implementation MUST NOT introduce a current-head/version chain merely to mimic FieldResolution or offer-revision machinery when no conflicting mutable fact is being resolved.

## 5. Reconfirmation authorization

Reconfirmation uses the same accepted professional publisher trust boundary as publication/withdrawal.

It succeeds only when all applicable conditions hold:

```text
NativeListing exists
AND lifecycle == ACTIVE
AND explicit AccountId supplied
AND explicit OrganizationMembership supplied
AND explicit candidate MarketplaceOrganization supplied
AND candidate Organization == NativeListing publishing Organization
AND accepted publishing-eligibility evaluator returns ALLOWED
```

Denied, cross-Organization, missing, DRAFT, WITHDRAWN, conflicting confirmation-ID reuse or otherwise invalid attempts MUST append no confirmation event and MUST NOT mutate lifecycle or listing facts.

This contract does not persist a general Account/Organization/Membership directory and does not integrate Auth0. The existing operator-assisted principal input remains the bounded execution mechanism until a later authenticated broker capability owns that gap.

## 6. Concurrency and transaction safety

A successful reconfirmation result MUST mean its immutable event is durably committed.

Implementation MUST preserve the repository's accepted transaction-ownership pattern: do not return success from a nested savepoint that still depends on an unrelated caller transaction later committing.

Concurrent valid reconfirmations may both be true events; they MUST NOT corrupt each other or lifecycle state. The effective confirmation time is the greatest admissible event/publication timestamp. Equal timestamps are semantically equivalent for freshness classification; deterministic audit ordering MAY use the stable confirmation ID as a tie-breaker.

An authorization failure or persistence failure MUST leave zero partial reconfirmation state.

## 7. Buyer-facing current-market eligibility

Current-market eligibility is stricter than lifecycle eligibility:

```text
ACTIVE
AND freshness in {CONFIRMED, DUE_FOR_CONFIRMATION}
-> may remain on current buyer surfaces

ACTIVE
AND freshness in {STALE, UNKNOWN}
-> MUST be suppressed from current buyer surfaces
```

Suppression does not alter lifecycle/history and does not infer `SOLD` or `WITHDRAWN`.

### 7.1 Public listing route

`GET /api/listings/{NativeListingId}` and `/listings/{NativeListingId}` MUST return current listing content only for:

```text
ACTIVE + CONFIRMED
ACTIVE + DUE_FOR_CONFIRMATION
```

For `ACTIVE + STALE` or `ACTIVE + UNKNOWN`, the public current-listing route MUST fail closed to the same ordinary not-found class used for other non-current/non-public listing states; it MUST NOT expose stale offer content as current inventory.

For visible listings the public projection MUST include at least:

```text
freshness_status
last_confirmed_at
```

`DUE_FOR_CONFIRMATION` MUST be buyer-visible as such; the grace period MUST NOT be rendered as if the listing were still fully confirmed.

Existing `noindex` behavior remains unchanged.

### 7.2 Native-inventory Search

SLICE-0051 Search MUST admit only current-market-eligible listings.

`STALE` and `UNKNOWN` ACTIVE listings are excluded before technical listing classification. They MUST NOT be relabeled as technical `INSUFFICIENT_DATA`, because their exclusion is inventory freshness, not missing `draft_max` truth.

A `DUE_FOR_CONFIRMATION` listing may remain in Search during the seven-day grace period, but every returned match MUST carry its freshness status and effective `last_confirmed_at` so the web surface can disclose the due state.

The due-state disclosure MUST be rendered coherently on all five existing public Search locale surfaces (`en`, `de`, `fr`, `pt`, `es`). The canonical freshness enum/value remains language-neutral; only presentation text is localized.

This slice adds **no new technical Search criterion** and does not change `draft_max` qualification, FieldResolution, exact Decimal, configuration, PhysicalBoat contradiction or confirmed-match semantics.

## 8. Time evaluation boundary

Freshness must be testable deterministically.

Domain/application freshness evaluation MUST accept an explicit timezone-aware UTC `as_of`/clock boundary rather than hard-wiring wall-clock reads deep inside qualification logic. Production HTTP paths may obtain current UTC time at the application boundary and pass it inward.

Tests and retained proof MUST be able to evaluate the same persisted listing at exact synthetic times without sleeping or rewriting audit timestamps.

## 9. Operator-assisted reconfirmation entry point

SLICE-0052 MUST provide a bounded operator-executable reconfirmation entry point over the real application/persistence path. It may be a dedicated repository script rather than a public HTTP write endpoint.

The entry point MUST require explicit listing/principal inputs, exercise the accepted eligibility evaluator and print/return a mechanically distinct outcome. It MUST NOT accept `authorized=true`, a raw Organization-ID-only bypass or an arbitrary confirmation timestamp.

No browser broker workspace is required by this contract.

## 10. Required retained proof

A PostgreSQL 18 -> FastAPI -> Astro retained proof MUST demonstrate at least:

```text
publish
-> ACTIVE + CONFIRMED
-> public listing visible
-> matching Search result visible

exact +30d
-> DUE_FOR_CONFIRMATION
-> still visible with due disclosure

exact +37d
-> STALE
-> absent from public current-listing content
-> absent from Search
-> lifecycle remains ACTIVE

successful authorized reconfirmation
-> CONFIRMED again
-> listing and Search visibility restored
```

The proof MUST also show:

- pre-existing ACTIVE freshness derives from the historical publication transition rather than deployment time;
- ACTIVE with no admissible confirmation evidence becomes `UNKNOWN` and is suppressed;
- cross-Organization/denied reconfirmation writes zero rows;
- DRAFT/WITHDRAWN reconfirmation is rejected without a confirmation row;
- an exact reconfirmation retry is idempotent and conflicting confirmation-ID reuse fails closed;
- `STALE` never creates `SOLD`/`WITHDRAWN` lifecycle history;
- the existing `draft_max` technical result for an otherwise identical confirmed listing remains unchanged.

## 11. Explicit non-goals

SLICE-0052 MUST NOT implement or silently decide:

- Auth0 integration or authenticated broker UI;
- persisted general actor directory;
- email/push reminders or automated alerts;
- a scheduler/background job merely to advance freshness status;
- OQ-006 alert cadence or cache-TTL policy;
- feed-driven freshness/source-health semantics;
- `WITHDRAWN -> ACTIVE` republish;
- `SOLD` or `ARCHIVED` lifecycle states;
- price/status history intelligence;
- SavedQuery/Monitor/Alert persistence;
- media;
- a second technical Search criterion;
- generic all-field Search/FieldResolution infrastructure;
- broad/indexable SEO.

Freshness state is derived at evaluation time from immutable evidence plus `MANUAL_NATIVE_V1`; no scheduled mutation is required for time to move a listing from CONFIRMED to DUE/STALE behavior.
