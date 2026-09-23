# HullQ — Professional Listing Draft Workspace Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Owning slice:** SLICE-0061 — Authenticated Professional Listing Draft Workspace  
**Controlling product direction:** `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`  
**Broker requirements:** `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`  
**Access foundation:** `specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md`  
**Owner-direct reference boundary:** `specs/OWNER_DIRECT_LISTING_WORKSPACE_CONTRACT.v0.1.md`  
**Marketplace truth foundation:** accepted SLICE-0040–0052 and SLICE-0060

## 1. Purpose

This contract adds one professional Broker Workspace capability:

> A currently workspace-authorized Account whose exact current matching ACTIVE OrganizationMembership contains `PUBLISHER` may create, list, reopen, read and update private incomplete professional listing drafts owned by one explicitly selected professional Organization.

The draft is pre-market workflow state.

It is **not** a NativeListing, PhysicalBoat, MarketEpisode, offer revision, lifecycle transition, freshness confirmation or public/Search-visible listing.

## 2. Identity boundary

Introduce a distinct identity kind:

```text
ProfessionalListingDraftId
```

Hard invariant:

```text
ProfessionalListingDraftId
!= OwnerDirectListingDraftId
!= NativeListingId
!= PhysicalBoatId
!= MarketEpisodeId
```

Equal raw text across identity kinds must not make them interchangeable.

A professional draft ID MUST NOT be accepted by an API/persistence function expecting another identity kind.

## 3. Ownership and authorization

### 3.1 Authoritative ownership

Professional draft ownership is the persisted:

```text
owner_organization_id
```

The draft also stores `created_by_account_id` for audit.

The creator Account does not become a permanent private owner separate from the Organization.

### 3.2 Current authorization on every request

For list/read/create/update:

1. validate the current HullQ signed session;
2. load current requested Organization and current OrganizationMembership from PostgreSQL;
3. apply existing Broker Workspace non-enumeration and MFA behavior;
4. require `PUBLISHER` in that exact current matching ACTIVE membership for draft-authoring actions;
5. do **not** require `OrganizationPublishingEligibility == ELIGIBLE` for private pre-market draft authoring;
6. only then may the draft operation continue.

This deliberately reuses current accepted semantics including:

- matching Account;
- matching Organization;
- ACTIVE membership;
- `PUBLISHER` role for draft authoring;
- MFA where required by the existing Broker Workspace access boundary.

The existing `evaluate_native_listing_publishing_eligibility()` MUST NOT be repurposed as the private-draft permission decision. Its normative contract answers whether an Account may publish a public `NativeListing`, and therefore includes the Organization publishing-eligibility gate. For 0061, `ELIGIBLE`, `UNVERIFIED` and `INELIGIBLE` publishing states do not alter whether already-authorized `PUBLISHER` members may retain private draft work. Any later draft-to-marketplace promotion/publication capability MUST re-apply the accepted public NativeListing publishing-eligibility decision and fail closed when it is not ALLOWED.

No new role or provider claim becomes an authorization input.

### 3.3 Non-enumeration and tenant isolation

A draft belonging to another Organization MUST never be returned or mutated.

Unknown draft and foreign-Organization draft must use the same bounded not-found outcome after the selected Organization access boundary succeeds.

Unknown/unauthorized Organization behavior remains externally non-enumerating as already accepted.

## 4. Shared Seller field semantics

The v0.1 professional draft common payload uses exactly the accepted owner-direct v0.1 common keys:

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

Every field remains optional; an empty draft is valid.

The exact value semantics remain aligned with the accepted owner-direct contract:

- trimmed non-empty strings where applicable;
- build year integer shape as already accepted;
- asking-price mode exactly `AMOUNT` or `POA`;
- positive finite decimal-string amount, never binary-float truth;
- amount absent when POA;
- currency exactly three uppercase ASCII letters;
- country exactly two uppercase ASCII letters;
- unknown keys fail closed.

These are still **draft input claims**, not accepted marketplace truth.

### 4.1 Shared implementation primitive

Implementation MUST NOT create a second inconsistent copy of the nine common field validators.

It must either:

- extract/reuse a channel-neutral common draft payload parser/serializer used by both owner-direct and professional draft boundaries; or
- reuse an already-existing channel-neutral primitive that mechanically proves identical semantics.

The existing owner-direct public API, persistence behavior and tests must remain unchanged from the caller's perspective.

### 4.2 SLICE-0065 professional-only offer-input extension

SLICE-0065 adds exactly one professional-only pre-market offer input outside the nine shared owner-direct/professional common keys:

```text
listing_offer.broker_description
```

This does **not** change `ACCEPTED_DRAFT_PAYLOAD_KEYS` or OwnerDirectListingDraft vocabulary.

Professional create/read/update MUST accept and round-trip the field under the exact wire key above. Omission remains valid while the professional draft is incomplete. When present, it must be a trimmed non-empty plain-text string. No placeholder/default/derived broker description may be generated.

The field remains private ProfessionalListingDraft state until a later explicit marketplace-promotion capability. Professional draft save MUST NOT create or mutate a NativeListing offer revision merely because broker_description is present.

## 5. Professional-only draft metadata

A professional draft MAY carry:

```text
broker_listing_reference
```

v0.1 semantics:

- optional;
- when present, trimmed non-empty string;
- mutable while the object remains a professional draft;
- not a NativeListing identity;
- not proof of external marketplace identity;
- no cross-Organization lookup/ownership inference may be based on it.

No other professional-only metadata is authorized by v0.1.

## 6. Persistence boundary

0061 may introduce one dedicated professional-draft table/aggregate.

Conceptual durable fields:

```text
professional_listing_draft_id
owner_organization_id
created_by_account_id
broker_listing_reference nullable
payload
version
created_at
updated_at
```

Required constraints:

- stable primary draft ID;
- foreign-key or equivalent referential integrity to authoritative Organization and Account tables;
- version starts at 1;
- version increments exactly once per successful update;
- deterministic timestamps;
- Organization-scoped read indexes sufficient for bounded list operations.

The exact JSONB/column split is implementation detail if the contract is preserved.

No migration or semantic rewrite of existing owner-direct draft rows is required.

## 7. Create/read/list/update semantics

Canonical API family:

```text
GET  /api/broker/organizations/{organization_id}/drafts
POST /api/broker/organizations/{organization_id}/drafts
GET  /api/broker/organizations/{organization_id}/drafts/{draft_id}
PUT  /api/broker/organizations/{organization_id}/drafts/{draft_id}
```

### POST

- authorization from §3 is required;
- absent body or empty object may create an empty draft;
- valid bounded initial fields may be supplied;
- server mints `ProfessionalListingDraftId`;
- owner Organization and creator Account come only from server-authorized context;
- successful create returns persisted version 1.

### GET collection

- returns only the selected authorized Organization's drafts;
- deterministic order: `updated_at DESC, professional_listing_draft_id ASC`;
- default page size 50;
- maximum page size 100;
- bounded keyset continuation;
- malformed cursor fails as bounded client error;
- no unbounded list or mandatory total count.

### GET item

- own Organization draft -> 200;
- foreign/unknown draft -> identical not-found behavior.

### PUT

- request carries full bounded v0.1 draft state plus `expected_version`;
- current expected version -> success and version increment;
- stale version -> 409 conflict with no mutation;
- invalid/unknown field -> 400 with no mutation;
- foreign/unknown draft -> same not-found behavior;
- no partial field acceptance after validation failure.

## 8. CSRF and browser-write boundary

Cookie authentication alone is insufficient for draft writes.

Every state-changing browser request MUST use an explicit same-origin write defense equivalent to the accepted owner-direct boundary:

1. exact normalized `Origin` matches configured HullQ web origin;
2. require a non-simple fixed HullQ request header, for example:
   `X-HullQ-Requested-With: professional-listing-draft-v1`;
3. no permissive credentialed CORS.

Missing/mismatched Origin or missing/wrong fixed header -> fail closed before mutation.

If Astro proxies writes, it must preserve/forward the browser Origin rather than replacing an untrusted Origin with a trusted one. FastAPI remains authoritative for authentication, authorization, validation and concurrency.

## 9. Browser surface

Required private Astro routes:

```text
/broker/organizations/{organization_id}/drafts
/broker/organizations/{organization_id}/drafts/{draft_id}
```

Collection surface:

- accessible from the accepted Organization workspace/inventory area;
- list current Organization drafts only;
- create a new empty/partial draft;
- bounded pagination;
- clear `Draft — not public` language.

Draft edit surface:

- render only an authorized Organization draft;
- edit/save v0.1 fields;
- show authoritative saved version/update result;
- stale-save conflict is visible and never silently overwritten;
- foreign/unknown draft is non-enumerating.

The UI MUST NOT expose Publish, Withdraw, Reconfirm, media, Search-fit or public-preview behavior in this slice.

## 10. Privacy, caching and indexation

Professional draft data is private Organization workspace data.

All draft API/page responses:

- `Cache-Control: private, no-store`;
- page responses include `X-Robots-Tag: noindex`;
- draft payload is not placed into public metadata/sitemaps/hreflang;
- no third-party tracker/subresource is added by this slice;
- authentication/session secrets are never rendered or logged.

## 11. No marketplace promotion

Professional draft create/read/update/list operations MUST NOT create or mutate:

- `physical_boats`;
- `market_episodes`;
- `native_listings`;
- NativeListing lifecycle transitions;
- NativeListing offer revisions/current head;
- NativeListing freshness confirmations;
- public listing state;
- Search eligibility/index state.

There is no draft-to-NativeListing promotion endpoint in v0.1.

The draft may contain values that later become candidate inputs for an explicit promotion capability, but 0061 MUST NOT silently treat them as accepted marketplace truth.

## 12. Owner-direct non-regression

0061 MUST preserve:

- `OwnerDirectListingDraftId` identity;
- owner-direct Account ownership;
- owner-direct routes/API shapes;
- optimistic versioning;
- owner-direct CSRF behavior;
- private/no-store/noindex boundary;
- no-publication semantics.

Extracting a shared field validator is allowed only if focused regression tests prove owner-direct wire and validation behavior unchanged.

## 13. Broker mandatory-register boundary

0061 does not by itself mark any of REQ-BROKER-022 through REQ-BROKER-029 `IMPLEMENTED`.

Especially:

- REQ-BROKER-023 remains PENDING;
- REQ-BROKER-024 remains PENDING because v0.1 does not include recoverable client-side work through ordinary connectivity interruption.

The Broker Workspace Launch Gate remains `NOT_READY`.

## 14. Tests and retained proof

At minimum cover:

### Authorization / tenant isolation

- unauthenticated request;
- authorized ACTIVE membership with `PUBLISHER`;
- missing/inactive membership;
- active membership without `PUBLISHER`;
- `UNVERIFIED`/`INELIGIBLE` publishing state does not destroy private draft-authoring capability but remains non-publishable under the existing public NativeListing contract;
- privileged membership without MFA;
- membership/role revocation after prior login;
- cross-Organization draft access attempt;
- unknown Organization and unknown draft bounded failure.

### Payload / concurrency

- empty create;
- partial create;
- all v0.1 common fields;
- professional-only broker_description present/absent and round-tripped;
- broker reference present/absent;
- owner-direct common-field validation parity;
- invalid/unknown field rejection;
- POA/amount conditional rule;
- current-version update increments once;
- stale expected version returns conflict and no overwrite;
- safe rendering of untrusted draft text.

### List behavior

- zero drafts;
- multiple drafts deterministic `updated_at DESC, draft_id ASC`;
- page-size bounds;
- multi-page keyset continuation;
- malformed cursor rejection;
- no cross-Organization leakage.

### Write security

- valid same-origin write succeeds;
- missing Origin fails;
- foreign Origin fails;
- missing/wrong fixed request header fails;
- failed CSRF/authorization/validation writes zero rows.

### Marketplace non-promotion

Prove draft operations create/mutate none of the marketplace truth tables/states listed in §11.

### Retained vertical proof

One deterministic PostgreSQL 18 + FastAPI + built Astro proof must demonstrate at minimum:

1. real OIDC/session login for a workspace-authorized Account whose current membership contains `PUBLISHER`;
2. selected Organization creates a private draft;
3. partial draft survives reload/list/read;
4. valid update increments version;
5. stale update returns conflict without overwriting;
6. second Account/Organization cannot observe or mutate the draft;
7. membership/role revocation changes the next authorization result;
8. invalid CSRF request fails with no mutation;
9. draft pages are private/no-store/noindex and clearly not public;
10. marketplace truth row/state counts remain unchanged by draft work;
11. existing owner-direct retained proof still passes;
12. existing professional inventory retained proof still passes;
13. finish with:

```text
PROFESSIONAL LISTING DRAFT WORKSPACE RESULT -> PASS
```

CI must execute the retained proof in the normal PostgreSQL/web integration path.

## 15. Explicitly deferred

Not part of v0.1 / SLICE-0061:

- professional draft promotion to marketplace identities (which must re-apply public NativeListing publishing eligibility);
- NativeListing edit;
- publish/withdraw/reconfirm controls;
- client-side/offline connectivity recovery;
- media;
- broker branding/profile completion;
- duplicate/clone/relist;
- Search-fit diagnostics;
- inventory export/import;
- leads/contact/CRM;
- sale/outcome;
- analytics/reporting;
- payments;
- owner-direct publication;
- buyer persistence/Saved Search;
- third Search criterion.

## 16. Acceptance summary

Accepted v0.1 boundary:

```text
current signed Account
→ current explicit Organization authorization
→ current matching ACTIVE membership + `PUBLISHER` draft-authoring role gate
→ Organization-owned ProfessionalListingDraft
→ private partial save/resume/update with optimistic versioning
→ no marketplace promotion
```
