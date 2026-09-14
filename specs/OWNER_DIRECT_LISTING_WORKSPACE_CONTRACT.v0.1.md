# HullQ — Owner-Direct Listing Draft Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Selected capability:** SLICE-0054 — Authenticated Owner-Direct Listing Draft Workspace  
**Primary requirement:** `REQ-PRIVATE-022`  
**Supporting requirements:** `REQ-PRIVATE-001`, `REQ-PRIVATE-003`, `REQ-PRIVATE-005`, `REQ-PRIVATE-012`, `REQ-PRIVATE-023`, `REQ-PRIVATE-024`  
**Controlling direction:** `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`

## 1. Purpose

This contract defines the first owner-direct write capability without weakening the accepted professional marketplace path.

One authenticated HullQ Account may create and work on private sale drafts before HullQ has implemented the later owner-direct publication gate.

The core boundary is:

```text
OwnerDirectListingDraftId
!= NativeListingId
!= PhysicalBoatId
!= MarketEpisodeId
```

An owner-direct draft is mutable private workspace state. It is **not marketplace inventory**.

## 2. Hard non-promotion rule

Creating or updating an owner-direct draft MUST NOT create, mutate or infer any of the following:

- `PhysicalBoat`;
- `MarketEpisode`;
- `NativeListing`;
- NativeListing offer revision;
- NativeListing lifecycle/freshness state;
- marketplace PhysicalBoat/offer fact observation or resolution;
- Search candidate/eligibility state;
- public listing route;
- seller verification status;
- right-to-list attestation;
- broker Organization or membership.

Draft values are user-entered work-in-progress. They are not canonical or resolved marketplace truth merely because HullQ persisted them.

A later explicitly selected admission/publication capability must own any transformation from draft input to market identities/claims and must preserve provenance. It MUST NOT reinterpret `OwnerDirectListingDraftId` as `NativeListingId`.

## 3. Account and authorization boundary

The existing SLICE-0053 HullQ browser session is the authentication primitive.

The authoritative draft owner is always:

```text
verified session.account_id
```

Organization membership is neither required nor consulted for owner-direct draft ownership.

Hard rules:

1. no valid HullQ session -> `401`;
2. create binds the new draft to `session.account_id` server-side;
3. any caller-supplied owner/account identity is rejected or ignored and MUST NOT determine ownership;
4. read/list/update queries are scoped server-side to `session.account_id`;
5. an unknown draft ID and a draft owned by another Account are indistinguishable on direct read/update (`404`);
6. a professional Organization membership does not grant access to another Account's owner-direct draft;
7. the current broker Organization authorization path remains unchanged.

No MFA requirement is introduced for ordinary private draft editing in this slice.

## 4. Login return-path extension

The current login-state allowlist accepts `/broker...` only.

SLICE-0054 MAY extend the same internal-path allowlist to:

```text
/sell/direct
/sell/direct/...
```

It MUST NOT introduce arbitrary absolute redirects, scheme-relative redirects or caller-controlled external hosts.

At minimum regression tests MUST prove:

- `/broker` still works;
- `/broker/...` still works;
- `/sell/direct` works;
- `/sell/direct/...` works;
- `https://evil.example/...`, `//evil.example/...`, unrelated absolute/relative prefixes and encoded redirect tricks do not escape the accepted internal prefixes.

## 5. Draft identity and persistence

SLICE-0054 introduces one dedicated persistence aggregate/table for owner-direct drafts.

Required durable properties:

```text
draft_id
owner_account_id
payload
version
created_at
updated_at
```

Constraints:

- `draft_id` is a server-generated opaque HullQ ID with no market-truth semantics;
- `owner_account_id` references the durable HullQ Account identity, not Auth0 `sub`, email or phone;
- `payload` is bounded by §6 and must reject unknown keys;
- `version` is a positive monotonically increasing integer used for optimistic concurrency;
- timestamps are server-generated timezone-aware instants;
- no nullable/proxy `publishing_organization_id` is introduced;
- no FK from the draft to `native_listings`, `physical_boats` or `market_episodes` is required in this slice.

A JSON/JSONB payload is acceptable here because the record is explicitly mutable pre-market workspace state, **provided** the API/domain validator enforces the finite v0.1 key set and value shapes below. It is not permission for arbitrary unvalidated JSON or for canonical marketplace truth to move into a schemaless blob.

## 6. v0.1 draft payload

The v0.1 payload may contain only these accepted marketplace-topic identifiers:

```text
physical_boat.marketed_brand_claim
physical_boat.model_designation_claim
physical_boat.build_year
physical_boat.boat_name
listing_offer.asking_price_mode
listing_offer.asking_price_amount
listing_offer.currency
listing_offer.location_country
listing_offer.location_region
```

They are reused as **draft input keys only**. Persisting them here does not instantiate marketplace claim-authority/resolution semantics.

### 6.1 Incomplete drafts are valid

Every field is optional for **draft save**.

The `REQUIRED_RESPONSE`/conditional requiredness in `MARKETPLACE_FIELD_REGISTRY.v0.1.json` remains an eventual marketplace-admission/completeness concern. SLICE-0054 MUST NOT require a seller to invent missing data simply to save work.

An empty newly-created draft is valid.

### 6.2 Validation when a value is present

When present, values must satisfy these bounded shapes:

- `physical_boat.marketed_brand_claim`: trimmed non-empty string;
- `physical_boat.model_designation_claim`: trimmed non-empty string;
- `physical_boat.build_year`: integer value, not boolean; no guessed year is generated;
- `physical_boat.boat_name`: trimmed non-empty string;
- `listing_offer.asking_price_mode`: exactly `AMOUNT` or `POA`;
- `listing_offer.asking_price_amount`: positive finite decimal represented without binary-float truth semantics;
- `listing_offer.currency`: exactly three uppercase ASCII letters; this is syntax validation, not independent currency/legal verification;
- `listing_offer.location_country`: exactly two uppercase ASCII letters; this is syntax validation, not independent geographic verification;
- `listing_offer.location_region`: trimmed non-empty string.

Conditional draft rule:

```text
asking_price_mode = POA
→ asking_price_amount MUST be absent/null
```

For an incomplete draft with `asking_price_mode = AMOUNT`, amount and currency MAY still be absent until later editing/admission. HullQ must show that the draft is incomplete rather than inventing those values.

No broker-specific narrative field (`broker_summary`, `broker_description`) is renamed or reused for a private seller in this slice.

## 7. Optimistic concurrency

Silent stale overwrite is forbidden.

Semantics:

```text
create draft
→ version = 1

update draft with expected_version = N
AND stored version = N
→ atomically persist new payload
→ version = N + 1
→ update updated_at

update draft with expected_version = N
AND stored version != N
→ 409 conflict
→ zero mutation
```

The version comparison and update must be one atomic persistence decision. A pre-read followed by an unconditional update is insufficient.

This is not offline/autosave recovery and does not satisfy Broker `REQ-BROKER-024`.

## 8. FastAPI boundary

FastAPI remains the sole application/domain API boundary.

Required HTTP surface:

```text
GET  /api/owner-direct/drafts
POST /api/owner-direct/drafts
GET  /api/owner-direct/drafts/{draft_id}
PUT  /api/owner-direct/drafts/{draft_id}
```

No DELETE, publish, submit-for-review, verification or referral endpoint is authorized in this slice.

Behavior:

### `GET /api/owner-direct/drafts`

- authenticated only;
- returns only the current Account's drafts;
- sufficient metadata to render the private draft index, including draft ID, version, created/updated timestamps and bounded summary fields already present in payload;
- deterministic ordering, newest `updated_at` first with a stable tie-breaker.

### `POST /api/owner-direct/drafts`

- authenticated only;
- creates one draft owned by `session.account_id`;
- optional initial payload follows §6;
- returns `201` with the authoritative persisted draft and version 1.

### `GET /api/owner-direct/drafts/{draft_id}`

- authenticated only;
- own draft -> `200`;
- foreign or unknown -> identical `404` shape.

### `PUT /api/owner-direct/drafts/{draft_id}`

- authenticated only;
- request carries full bounded payload plus `expected_version`;
- own current version -> `200`, version increments;
- foreign/unknown -> `404`;
- stale version -> `409` with no mutation;
- invalid field/key/value -> `400` with no mutation.

The API must never accept an Organization ID or Account ID as an authorization substitute for the signed session.

## 9. CSRF and browser-write boundary

Cookie authentication alone is not a sufficient write authorization story.

Every state-changing owner-direct draft request (`POST`, `PUT`) MUST have an explicit browser CSRF defense. The accepted v0.1 mechanism is:

1. require an `Origin` header whose exact normalized origin matches the configured HullQ web origin;
2. require a non-simple HullQ request header such as `X-HullQ-Requested-With: owner-direct-draft-v1`;
3. do not enable permissive credentialed CORS for the draft API.

Missing/mismatched Origin or missing/wrong HullQ request header -> fail closed (`403`) before mutation.

If Astro uses a server-side presentation/proxy endpoint for local/deployment topology reasons, it MUST forward the browser's original Origin for FastAPI validation rather than replacing an untrusted Origin with a trusted one. The proxy may add the fixed HullQ request header only for its bounded draft action. FastAPI remains authoritative for authentication, ownership, field validation and concurrency.

Tests must include at least one cross-origin/form-style negative case and one valid same-origin mutation case.

## 10. Browser surface

Required private Astro surfaces:

```text
/sell/direct
/sell/direct/{draft_id}
```

`/sell/direct`:

- unauthenticated -> login path that returns to `/sell/direct` after successful authentication;
- authenticated -> list only the current Account's drafts and provide `Start a draft`;
- zero Organization memberships is a valid state.

`/sell/direct/{draft_id}`:

- renders only an owned draft;
- lets the user edit/save the bounded §6 fields;
- shows the authoritative saved version/update result;
- stale-save conflict is visible and must not be silently overwritten;
- foreign/unknown draft uses one non-enumerating not-found state.

Both surfaces MUST visibly state the equivalent of:

> **Draft — not public**

There is no Publish button or wording implying the draft is listed, verified, Search-visible or approved.

Astro may format/forward values but must not become the authoritative field validator, owner-authorizer or concurrency engine.

## 11. Privacy / caching / indexation

Owner-direct draft data is private workspace data.

For all draft API/page responses:

- `Cache-Control: private, no-store`;
- page responses: `X-Robots-Tag: noindex`;
- no third-party analytics/tracker/subresource is introduced by this slice;
- no draft payload is placed in public URLs, logs or error messages beyond bounded identifiers needed for diagnostics;
- authentication/session tokens are never rendered into HTML or browser-readable script state.

## 12. Professional-path non-regression

SLICE-0054 MUST NOT change the accepted meaning of:

- `evaluate_native_listing_publishing_eligibility`;
- `publishing_organization_id` on existing professional NativeListing rows;
- broker Organization/Membership role authorization;
- broker privileged-role MFA rules;
- current NativeListing lifecycle/freshness;
- public listing eligibility;
- Search classification/order.

A private draft must not be created by fabricating a professional Organization or membership.

## 13. Retained end-to-end proof

SLICE-0054 must retain one deterministic PostgreSQL 18 + FastAPI + built Astro proof using the accepted local OIDC/JWKS test issuer and browser-style session behavior.

The proof must demonstrate at minimum:

1. authenticate Account A with **zero professional memberships**;
2. browser reaches `/sell/direct` after login;
3. Account A creates an empty or partial draft;
4. Account A saves valid bounded values;
5. reload/list/read returns the durable saved values/version from PostgreSQL;
6. Account A updates with the current version and version increments;
7. stale expected version returns conflict and does not overwrite;
8. Account B cannot read or update Account A's draft and sees the same direct-object not-found behavior as an unknown ID;
9. invalid/tampered session cannot access drafts;
10. cross-origin/missing-CSRF-header mutation fails closed;
11. the draft remains private/no-store/noindex at the browser surface;
12. no new row is created in `physical_boats`, `market_episodes`, `native_listings`, NativeListing offer revision/fact tables or public Search state as a consequence of draft operations;
13. existing Broker Workspace retained proof still passes.

The proof must not fake authorization by injecting an account ID outside the signed session.

## 14. Explicitly deferred

Not part of v0.1 / SLICE-0054:

- phone verification;
- right-to-list attestation;
- baseline fraud/risk scoring;
- ID/selfie/liveness verification;
- Sale Authority verification;
- representation conflict / duplicate-sale resolution;
- creation of PhysicalBoat/MarketEpisode/NativeListing from a draft;
- public listing publication;
- Search inclusion/ranking;
- listing freshness/reconfirmation;
- media/photo/document upload;
- seller narrative field redesign;
- broker referral;
- seller-to-broker conversion;
- payments/verification monetization;
- escrow/transaction flows;
- delete/archive workflow;
- autosave/offline recovery/general draft framework.

Each requires a later explicit capability/contract where applicable.