# HullQ Professional Inventory Lifecycle Controls Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Owning slice:** SLICE-0064 — Professional Inventory Lifecycle Controls  
**Depends on:** accepted Broker Workspace access; Organization inventory overview; NativeListing lifecycle; NativeListing freshness; public NativeListing read  
**Normative language:** BCP 14 semantics apply to uppercase MUST/SHOULD/MAY.

## 1. Purpose

This contract defines exactly one capability:

> an authenticated, currently authorized professional publisher can publish, withdraw or reconfirm an already-existing NativeListing owned by the selected MarketplaceOrganization from the private Broker Workspace, using the existing accepted lifecycle/freshness truth.

It does not create NativeListings, promote ProfessionalListingDrafts, edit offers, add media or introduce new lifecycle states.

## 2. Existing truth is authoritative

SLICE-0064 MUST reuse, not reinterpret:

- `evaluate_native_listing_publishing_eligibility()`;
- `publish_native_listing()`;
- `withdraw_native_listing()`;
- `reconfirm_native_listing()`;
- current Broker Workspace session/Organization/Membership/MFA lookup;
- current Organization inventory read projection;
- public listing/current-market freshness resolution.

Hard:

```text
HTTP/UI control != new lifecycle model
HTTP/UI control != new freshness model
HTTP/UI control != new authorization model
```

## 3. Supported operations

v0.1 supports exactly:

```text
PUBLISH    DRAFT -> ACTIVE
WITHDRAW   ACTIVE -> WITHDRAWN
RECONFIRM  ACTIVE -> immutable freshness confirmation
```

No other transition is authorized.

Especially:

```text
WITHDRAWN -> ACTIVE  NOT IMPLEMENTED
DRAFT -> WITHDRAWN   NOT IMPLEMENTED
WITHDRAWN -> SOLD    NOT IMPLEMENTED
ACTIVE -> SOLD       NOT IMPLEMENTED
```

## 4. Authorization and tenant isolation

Every operation MUST use:

```text
current signed HullQ Account
+ exact selected MarketplaceOrganization
+ exact current OrganizationMembership
+ accepted Broker Workspace MFA boundary
+ accepted public NativeListing publishing-eligibility evaluator
+ persisted NativeListing publishing Organization ownership
```

The caller MUST NOT supply:

- an `authorized=true` flag;
- publishing eligibility;
- membership roles;
- listing ownership;
- actor AccountId;
- publishing OrganizationId separate from the route-selected Organization.

Unknown NativeListing and a NativeListing owned by another Organization MUST be externally non-enumerating after the selected Organization boundary succeeds.

A display name MUST NOT be used as an authorization selector.

## 5. Publishing eligibility

The existing evaluator remains authoritative.

Therefore a lifecycle/freshness write fails closed when any accepted condition fails, including:

- no current membership;
- Account mismatch;
- Organization mismatch;
- inactive membership;
- missing PUBLISHER role;
- Organization UNVERIFIED;
- Organization INELIGIBLE.

SLICE-0064 MUST NOT weaken those rules merely because the listing already exists.

## 6. MFA

The current Broker Workspace MFA/step-up requirement remains a prerequisite to the privileged browser write surface.

A session that would receive `MFA_REQUIRED` for the Organization workspace MUST NOT mutate lifecycle or freshness state.

## 7. CSRF / browser-write boundary

Every state-changing browser request MUST use the accepted same-origin defense:

1. exact normalized browser `Origin` matches configured HullQ web origin;
2. one fixed non-simple request header identifies the professional inventory-state client;
3. cookie authentication alone is insufficient;
4. no permissive credentialed CORS.

Suggested header:

```text
X-HullQ-Requested-With: professional-inventory-lifecycle-v1
```

Missing/foreign Origin or missing/wrong fixed header MUST fail before mutation.

## 8. Transaction boundary

Existing persistence functions require an IDLE connection so they can own and commit a top-level PostgreSQL transaction.

The application layer MUST NOT run authorization queries and then accidentally invoke the persistence mutation inside the still-open implicit read transaction.

Before the accepted mutation primitive is called, prior read/authorization transaction state on that connection MUST be safely completed, or a fresh IDLE connection MUST be used.

A successful API result MUST mean the accepted persistence primitive has durably committed its lifecycle transition / freshness event.

## 9. Publish semantics

Publish invokes the existing `publish_native_listing()` semantics only.

Required preconditions remain:

- listing exists;
- selected Organization owns it;
- current lifecycle is DRAFT;
- publishing eligibility is ALLOWED;
- publication completeness succeeds:
  - non-null MarketEpisode;
  - existing MarketEpisode;
  - existing PhysicalBoat;
  - current NativeListing offer head.

Outcomes MUST preserve existing distinctions including incomplete listing and current-state conflict.

On successful publish:

- one existing lifecycle transition `DRAFT -> ACTIVE` is appended;
- publication itself provides accepted freshness confirmation evidence;
- buyer visibility is determined only by existing public-read/freshness rules;
- no new offer, PhysicalBoat, MarketEpisode or claim revision is created.

## 10. Withdraw semantics

Withdraw invokes existing `withdraw_native_listing()` semantics only.

Required:

- listing exists;
- selected Organization owns it;
- current lifecycle is ACTIVE;
- publishing eligibility is ALLOWED.

Successful withdraw:

```text
ACTIVE -> WITHDRAWN
```

and appends the accepted immutable publication-transition evidence.

Withdrawal MUST NOT:

- mark SOLD;
- infer a sale;
- create sale/outcome data;
- delete listing/offer/claim history;
- create a republish path.

## 11. Reconfirm semantics

Reconfirm invokes existing `reconfirm_native_listing()` semantics only.

Required:

- listing exists;
- selected Organization owns it;
- lifecycle is ACTIVE;
- publishing eligibility is ALLOWED;
- caller supplies one stable bounded reconfirmation operation identity.

The HTTP request SHOULD use a canonical UUID string as the operation identity and map it to `FreshnessConfirmationId`.

A genuine retry with the identical operation identity and identical listing/principal envelope MUST retain the accepted idempotent outcome.

Conflicting reuse of the same operation identity MUST fail closed.

Reconfirming MUST NOT mutate lifecycle state.

## 12. API boundary

Preferred Organization-scoped API family:

```text
POST /api/broker/organizations/{organization_id}/inventory/{native_listing_id}/publish
POST /api/broker/organizations/{organization_id}/inventory/{native_listing_id}/withdraw
POST /api/broker/organizations/{organization_id}/inventory/{native_listing_id}/reconfirm
```

Equivalent paths MAY be used if the exact Organization + NativeListing scope is explicit.

Publish/withdraw need no domain payload beyond the route identities.

Reconfirm carries only the bounded operation/confirmation identity required by §11.

The response MUST use mechanically distinct result codes/fields rather than a single ambiguous boolean.

## 13. Browser behavior

The existing private Organization inventory page is the required v0.1 action surface.

Minimum controls:

```text
DRAFT:
  Publish

ACTIVE:
  Withdraw
  Reconfirm

WITHDRAWN:
  no republish control
```

Controls MAY be conditionally hidden based on the current rendered factual state for usability, but server authorization and state checks remain mandatory.

After any successful action the browser MUST show freshly read server state, not a client-invented lifecycle/freshness result.

Failures MUST be visible and must not silently pretend success.

## 14. Required visible outcomes

At minimum distinguish:

- published;
- withdrawn;
- reconfirmed / exact retry accepted;
- authentication required;
- MFA required;
- publishing denied;
- listing not found / foreign Organization as one non-enumerating shape;
- incomplete listing;
- current-state conflict;
- invalid reconfirm operation identity;
- service failure.

The UI MAY translate exact domain reason codes into concise text but MUST NOT merge materially distinct outcomes into a false success.

## 15. Privacy / caching / indexation

All Broker Workspace mutation responses/pages remain private Organization data:

- `Cache-Control: private, no-store` where applicable;
- private pages remain `noindex`;
- no auth/session/MFA secret is rendered or logged;
- no new third-party tracker is introduced.

## 16. No creation / promotion / offer editing

SLICE-0064 MUST NOT create or mutate:

- ProfessionalListingDraft payload/state except ordinary existing independent use;
- PhysicalBoat identity;
- MarketEpisode identity;
- NativeListing creation envelope;
- NativeListing offer revisions/current head;
- PhysicalBoat claim revisions;
- media;
- lead/outcome/analytics state.

This is lifecycle/freshness control for already-existing NativeListings only.

## 17. Search / public behavior

SLICE-0064 adds no Search criterion.

Search/public consequences occur only through existing accepted rules:

- successful publish + current freshness may make a listing publicly/current-market eligible;
- successful withdraw removes it through lifecycle eligibility;
- successful reconfirm may restore an ACTIVE stale listing to current-market eligibility;
- failed operations change nothing.

No web code may independently calculate current-market eligibility.

## 18. Tests

At minimum cover:

### Authorization

- unauthenticated;
- unknown/unauthorized Organization;
- MFA required;
- ACTIVE membership missing PUBLISHER;
- inactive/revoked membership;
- Organization UNVERIFIED;
- Organization INELIGIBLE;
- foreign listing under otherwise authorized Organization;
- exact own Organization listing succeeds when all preconditions hold.

### Publish

- complete own DRAFT -> ACTIVE;
- incomplete DRAFT -> bounded failure, zero transition;
- ACTIVE publish attempt -> state conflict;
- WITHDRAWN publish attempt -> state conflict;
- publication creates exactly one accepted transition;
- publication creates no offer/PhysicalBoat/MarketEpisode/claim revision;
- buyer/public state is read from existing public-read/freshness path.

### Withdraw

- own ACTIVE -> WITHDRAWN;
- DRAFT/WITHDRAWN withdraw -> state conflict;
- withdrawal never creates SOLD/outcome state;
- public listing becomes unavailable through existing lifecycle rule.

### Reconfirm

- own ACTIVE reconfirm succeeds;
- exact retry with same operation ID is idempotent;
- conflicting operation-ID reuse fails closed;
- DRAFT/WITHDRAWN reconfirm rejected;
- stale ACTIVE reconfirm becomes CONFIRMED under existing freshness policy;
- lifecycle remains ACTIVE;
- public/Search behavior reuses existing current-market predicate.

### CSRF

- valid same-origin + fixed header succeeds;
- missing Origin fails;
- foreign Origin fails;
- missing/wrong fixed header fails;
- failed CSRF writes zero lifecycle/freshness rows.

### Tenant isolation / non-enumeration

- foreign listing and unknown listing expose the same bounded not-found shape;
- no other Organization's state can be mutated.

### Non-regression

- professional draft + recovery unchanged;
- broker inventory read behavior unchanged except action affordances;
- public publisher identity unchanged;
- owner-direct workspace unchanged;
- Search criterion count/semantics unchanged.

## 19. Retained proof

Required real PostgreSQL 18 + real local OIDC/JWKS + FastAPI + built Astro proof MUST demonstrate at least:

1. real login into an authorized PUBLISHER Organization with MFA;
2. representative complete own DRAFT NativeListing visible in inventory;
3. browser/API Publish -> ACTIVE and public visibility according to accepted public read;
4. unauthorized/foreign listing publish attempt writes nothing;
5. own ACTIVE listing Withdraw -> WITHDRAWN and public read disappears;
6. no SOLD/outcome state is created;
7. representative stale ACTIVE listing is absent from public current-market content;
8. browser/API Reconfirm with stable operation ID -> CONFIRMED and public visibility restored;
9. exact reconfirm retry is idempotent;
10. DRAFT/WITHDRAWN reconfirm fails with no confirmation row;
11. CSRF failure writes nothing;
12. membership/PUBLISHER/MFA/eligibility revocation changes the next action result;
13. inventory page shows only state-appropriate controls and freshly read result;
14. owner-direct and professional draft retained proofs still pass;
15. finish with:

```text
PROFESSIONAL INVENTORY LIFECYCLE CONTROLS RESULT -> PASS
```

## 20. Governance effect

SLICE-0064 does not change any REQ-BROKER-022…030 register status.

It advances evidence for Broker Workspace Launch Gate §2 but does not make the gate PASS.

The gate remains `NOT_READY`.

## 21. Explicitly deferred

Not part of SLICE-0064:

- draft promotion/listing creation;
- PhysicalBoat/MarketEpisode identity decision;
- boat-name marketplace persistence expansion;
- broker-description draft expansion;
- offer/price/detail edit;
- republish/relist;
- SOLD/outcome;
- media;
- leads/CRM;
- analytics;
- export/import;
- Search-fit;
- payments;
- production pilot/launch.

## 22. Acceptance summary

Accepted v0.1 boundary:

```text
current signed Account
+ selected authorized Organization
+ current membership/MFA
+ accepted public publishing eligibility
+ existing Organization-owned NativeListing
→ Publish DRAFT -> ACTIVE
OR Withdraw ACTIVE -> WITHDRAWN
OR Reconfirm ACTIVE freshness
→ existing lifecycle/freshness/public/Search truth only
```
