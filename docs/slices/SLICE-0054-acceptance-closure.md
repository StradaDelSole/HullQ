# SLICE-0054 — Acceptance closure

**Slice:** SLICE-0054  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #201  
**Accepted implementation HEAD:** `7b9b1f45bba36b082646a349170e3d2058a1461b`  
**Implementation merge commit:** `35c1309824996a7ebb339e735769e26f1c8186d8`  
**Independent exact-head ACCEPT review:** `5236370205`  
**Owner acceptance:** explicitly recorded 2026-09-17

## Accepted capability

SLICE-0054 adds HullQ's first authenticated owner-direct/private-seller pre-market workspace vertical:

```text
authenticated HullQ Account
→ private OwnerDirectListingDraft
→ create / list / reopen / update
→ persisted incomplete pre-market work state
```

A private seller does not require a professional Organization or Membership. Ownership is derived from the authenticated HullQ Account/session; the client does not supply the owner AccountId.

The accepted identity boundary is:

```text
OwnerDirectListingDraftId
!= NativeListingId
!= PhysicalBoatId
!= MarketEpisodeId
```

The draft is a private work object, not marketplace truth and not the `DRAFT` lifecycle state of a NativeListing.

## Ownership, concurrency and browser security

Accepted behavior includes:

- create, list, reopen/read and update only the authenticated Account's own drafts;
- unknown and foreign draft access collapse to the same non-enumerating external behavior;
- server-generated opaque draft identity;
- optimistic versioning with stale-write conflict protection;
- bounded owner-direct login return path: exact `/sell/direct` or `/sell/direct/...` descendants only;
- mutating browser requests require explicit Origin validation plus the non-simple HullQ request header;
- authenticated owner-direct browser surfaces are private, `no-store` and `noindex`;
- the existing professional Broker Workspace access vertical remains non-regressed.

The accepted v0.1 payload remains deliberately bounded and permits incomplete draft persistence. Applicable string fields use normative trimmed-string semantics.

## Non-promotion boundary

Owner-direct draft operations do not create or promote marketplace/public state. Retained evidence covers no mutation caused by the draft workflow to:

```text
physical_boats
market_episodes
native_listings
native_listing_offer_revisions
native_listing_offer_heads
native_listing_publication_transitions
native_listing_freshness_confirmations
```

The current Search implementation reads canonical marketplace state rather than a separate materialized public Search index. Because the owner-direct draft does not instantiate or mutate the relevant marketplace/publication/freshness state, it cannot become public Search inventory inside SLICE-0054.

## Independent review and amendments

The original implementation exact head was:

```text
9af3398115d78c901f87cbe7fbee01cb225390f4
```

Independent review found three contract-level defects:

1. accepted strings were checked with `strip()` but the untrimmed original value was retained;
2. the owner-direct login return-path prefix check admitted sibling/prefix-confusion paths such as `/sell/directevil`;
3. the retained non-promotion proof covered marketplace identity tables but not the existing NativeListing offer/fact and public Search-affecting durable state.

Amendment 1 exact head:

```text
2529e4614397009d6d5d26233b94cda87f86036a
```

Amendment 1 corrected all three findings: canonical trimmed-string persistence/serialization, segment-bounded return paths, and expanded non-promotion evidence across the actual canonical offer/fact/public-state tables.

A second review found that the SLICE-0054 retained vertical existed but was not wired into CI, while the local amendment environment lacked usable PostgreSQL credentials for that proof. Amendment 2 therefore added the retained owner-direct proof to the existing PostgreSQL 18 CI job without changing product/domain/API behavior.

Final accepted exact head:

```text
7b9b1f45bba36b082646a349170e3d2058a1461b
```

Independent exact-head review returned `ACCEPT`, review ID `5236370205`. The Project Owner explicitly accepted that exact implementation on 2026-09-17.

## Exact-head verification

Remote verification on exact accepted HEAD `7b9b1f45bba36b082646a349170e3d2058a1461b`:

```text
CI run 35225968759 → SUCCESS
Manufacturer artifact reproducibility run 35225968931 → SUCCESS
```

The PostgreSQL 18 CI integration job executed and passed both retained authenticated workspace verticals:

```text
SLICE-0053 authenticated Broker Workspace access proof → PASS
SLICE-0054 authenticated Owner-Direct Draft Workspace proof → PASS
```

The exact-head CI also passed repository contract validation, formatting, lint, type check, cross-platform tests, web quality/build/tests, dependency audit and the full PostgreSQL-backed suite/coverage gate.

PR #201 merged the accepted implementation to `main` as:

```text
35c1309824996a7ebb339e735769e26f1c8186d8
```

## Scope retained / explicitly deferred

SLICE-0054 deliberately does **not** implement:

- marketplace admission or publication;
- phone verification;
- right-to-list attestation;
- strong identity verification;
- documentary `Sale Authority Verified` evidence;
- representation-conflict handling;
- media operations;
- enquiries/leads/CRM;
- broker referral;
- sale/outcome workflow;
- Search eligibility, ranking or a new Search criterion;
- delete/archive workflow;
- payments or subscriptions;
- external production marketplace data or a production pilot.

No seller verification state promotes technical vessel facts. No owner-direct payment may buy truth, Search eligibility or organic position.

## Trigger-gate state after acceptance

SLICE-0054 adds no technical native Search criterion and does not activate external production marketplace data, production-pilot or public-launch triggers.

The accepted trigger state remains:

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 1
WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056
WORKFLOW_REASSESSMENT_STATUS: NOT_DUE

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED

BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

SLICE-0054 does not satisfy any pending Broker Workspace mandatory commitment merely by providing the separate private-seller draft lane.

## PROJECT_STATE freshness closure

This closure advances canonical state atomically to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0054
PROJECT_STATE_QUEUE_SLICE:    0055
```

`SLICE-0055` is only the next queue number. **This closure does not select a SLICE-0055 capability and does not authorize implementation.**

Before selecting the next capability, HullQ will perform the planned post-SLICE-0054 product/repository reconciliation. No non-repository product discussion is converted into a normative requirement by this closure.

## Product execution checkpoint

HullQ now has three bounded product-side foundations:

```text
Buyer
→ public listing
→ concrete-yacht truth
→ deterministic technical native Search
→ evidence-backed freshness

Professional seller
→ external authentication
→ HullQ Account
→ Organization/Membership/roles
→ tenant-safe + MFA-gated authorization
→ protected Broker Workspace landing

Owner-direct seller
→ HullQ Account
→ private owner-direct draft
→ create / save / list / reopen / update
→ no marketplace/public/Search promotion
```

The next capability must be selected from actual repository/product state after the planned reconciliation; this closure allocates no capability beyond queue number `0055`.

## Closure decision

```text
SLICE-0054 = OWNER_ACCEPTED
```

Implementation is merged. Closure becomes canonical only after this closure PR passes repository validation/CI, independent exact-head closure review and guarded merge. `FINISH_SLICE.bat` may run only after that closure merge.