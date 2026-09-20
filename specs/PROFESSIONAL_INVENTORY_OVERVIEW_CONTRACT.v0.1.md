# HullQ — Professional Inventory Overview Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Owning slice:** SLICE-0060 — Authenticated Professional Inventory Overview  
**Controlling product direction:** `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`  
**Broker requirements:** `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`  
**Access foundation:** `specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md`  
**Marketplace truth foundation:** accepted SLICE-0043/0045/0049/0052

## 1. Purpose

This contract adds one professional Broker Workspace capability:

> Show an authenticated Account the current NativeListing inventory of one explicitly selected professional Organization for which that Account currently has authorized workspace access.

It is read-only. It does not create, edit, publish, withdraw, reconfirm or otherwise mutate inventory.

## 2. Authorization boundary

Canonical inventory route:

```text
/broker/organizations/{organization_id}/inventory
```

The server-side read MUST reuse the accepted SLICE-0053 session and Organization authorization boundary.

For every request:

1. validate the current HullQ session;
2. read current OrganizationMembership truth from PostgreSQL;
3. apply existing Organization workspace authorization/MFA semantics;
4. only after authorization succeeds, read inventory for that exact Organization.

A stale session token MUST NOT substitute for current membership truth.

Unknown Organization and unauthorized existing Organization MUST remain externally non-enumerating, matching the existing workspace boundary.

If the existing access boundary returns MFA-required for the membership, inventory access MUST return the same bounded MFA-required outcome.

No new role vocabulary or authorization shortcut is introduced.

## 3. Inventory ownership semantics

Organization inventory membership is determined only by the durable NativeListing creation envelope:

```text
native_listings.publishing_organization_id == requested authorized organization_id
```

Do not infer ownership from:

- current user email;
- Auth0 claims;
- broker listing reference;
- BoatDesign;
- MarketEpisode;
- public page URL;
- client-supplied ownership flags.

A listing belonging to another Organization MUST never appear.

## 4. Read model

Each inventory item MUST identify at least:

- `native_listing_id`;
- current lifecycle state;
- broker listing reference when present;
- durable listing created timestamp;
- current offer state:
  - amount + currency, or
  - POA, or
  - explicit no-current-offer;
- current freshness/reconfirmation state where it exists;
- current last-confirmed timestamp where it exists;
- whether the accepted current public listing read resolves;
- public listing navigation only when that public read actually resolves.

The authorized inventory surface MAY include additional already-accepted current listing metadata if it remains factual and does not duplicate another truth model.

## 5. Lifecycle semantics

Use the existing accepted lifecycle vocabulary exactly:

```text
DRAFT
ACTIVE
WITHDRAWN
```

Do not infer:

- SOLD from WITHDRAWN;
- publication from offer existence;
- freshness from lifecycle;
- ACTIVE from public URL construction.

The UI may display lifecycle state to the authorized Organization user.

## 6. Offer semantics

The overview reads only the accepted current offer head.

If a current offer exists, preserve exact stored semantics:

- AMOUNT: exact amount + original currency;
- POA: price on application;
- location fields where included by the selected projection.

If no current offer exists, show an explicit bounded absent state.

Do not:

- convert currency;
- infer market value;
- infer negotiation room;
- reconstruct superseded revisions as current.

## 7. Freshness semantics

Freshness remains independent of lifecycle.

Where current accepted freshness state exists, expose the exact accepted state and last-confirmed timestamp.

Where it does not exist or is not applicable to the item, show a bounded absent/not-applicable state rather than inventing confirmation.

Do not duplicate freshness decision logic in Astro/TypeScript.

## 8. Public-link semantics

A public link may be shown only when the existing accepted current public listing-read boundary resolves that NativeListing as public/current.

The overview MUST NOT assume:

```text
ACTIVE == currently public
```

if other accepted public-read conditions can make the public read unavailable.

DRAFT and WITHDRAWN items must never receive a fabricated public link.

## 9. Deterministic ordering and bounded pagination

The inventory response MUST use one deterministic order:

```text
created_at DESC
then native_listing_id ASC
```

The read MUST be bounded and keyset-paginated rather than loading an unbounded Organization inventory.

v0.1 contract:

- default page size: 50;
- maximum page size: 100;
- page size outside the accepted positive range fails validation rather than silently becoming unbounded;
- continuation uses a server-issued opaque cursor representing the last accepted sort key;
- continuation preserves the exact Organization filter and deterministic ordering;
- invalid/malformed cursors fail as a bounded client error and never weaken Organization isolation;
- response exposes `next_cursor` only when another page exists;
- no total-count query is required by v0.1.

New listings created after page 1 need not be injected into an already-started continuation sequence; restarting from page 1 obtains the newest current view.

No revenue, payment, performance, freshness urgency, inferred quality or buyer-demand ranking may alter this order.

A later user-controlled sort/filter capability is separate.

## 10. Private web boundary

The inventory surface is authenticated Organization workspace data and MUST remain:

- `noindex`;
- `private, no-store`;
- absent from public sitemap/hreflang discovery;
- free of inventory IDs in unrelated public metadata.

The browser URL contains only the explicit Organization workspace identity and normal route structure.

## 11. Presentation boundary

Astro/TypeScript may:

- request the authorized inventory read model from FastAPI;
- render factual state;
- render public links only when supplied as public/current;
- link back to the Organization workspace.

Astro/TypeScript MUST NOT:

- query PostgreSQL directly;
- infer Organization ownership;
- recalculate authorization;
- infer lifecycle/freshness/publication;
- expose other-Organization inventory;
- mutate listing state.

## 12. Empty/error states

Authorized Organization with zero NativeListings:

- render an ordinary empty inventory state;
- do not treat it as an authorization failure.

Authentication/authorization/MFA outcomes remain distinct from:

- authorized empty inventory;
- infrastructure/service failure.

Service failure MUST NOT be presented as “no listings”.

## 13. Persistence and supporting index boundary

SLICE-0060 creates no new domain/application persistence:

- no inventory table;
- no broker preference row;
- no inventory cache as source of truth;
- no analytics/telemetry event requirement;
- no new marketplace identity.

The read model is a projection over current accepted state.

Because current `native_listings` persistence has no index on `publishing_organization_id`, implementation is expected to add one Alembic-managed supporting B-tree index aligned to the Organization filter and deterministic keyset order, conceptually:

```text
(publishing_organization_id, created_at DESC, native_listing_id ASC)
```

The exact PostgreSQL/Alembic spelling may vary if equivalent planner behavior is proved. This index is performance/access-path infrastructure only; it MUST NOT change listing truth, lifecycle, ownership or identity semantics.

## 14. Broker mandatory-register boundary

SLICE-0060 does not by itself mark any of REQ-BROKER-022 through REQ-BROKER-029 `IMPLEMENTED`.

Specifically it does not complete:

- REQ-BROKER-023 branding preservation;
- REQ-BROKER-024 connectivity-resilient draft recovery.

The Broker Workspace Launch Gate remains `NOT_READY`.

## 15. Tests and retained proof

At minimum cover:

### Authorization/isolation

- unauthenticated request;
- authorized active membership;
- revoked/inactive membership after prior login;
- unknown Organization;
- unauthorized existing Organization;
- privileged membership without MFA;
- no cross-Organization inventory leakage.

### Inventory truth

- zero-listing Organization;
- multiple listings in deterministic order;
- page-size bounds;
- multi-page keyset continuation with no duplicate/cross-Organization item;
- malformed cursor rejection;
- DRAFT item;
- ACTIVE item;
- WITHDRAWN item;
- current AMOUNT offer;
- current POA offer;
- no-current-offer state;
- current freshness state where present;
- no/absent freshness where applicable;
- only genuinely public/current item gets public navigation.

### Web/private boundary

- private/no-store and noindex;
- Organization inventory route is protected;
- service failure remains distinct from empty inventory;
- Organization workspace exposes a clear inventory navigation action;
- safe rendering of broker reference/current factual text.

### Retained vertical proof

A deterministic PostgreSQL + FastAPI + built Astro proof MUST demonstrate at minimum:

1. one authenticated Account with an authorized Organization;
2. a second Organization not authorized to that Account or separate from the selected Organization;
3. selected Organization owns enough representative NativeListings to exercise at least two pages, including DRAFT, ACTIVE and WITHDRAWN states;
4. another Organization owns a listing that never appears in selected inventory;
5. keyset continuation returns deterministic non-overlapping pages and never escapes the Organization filter;
6. lifecycle/offer/freshness facts are current;
7. public link exists only for the item accepted by current public read;
8. revoked/unauthorized access fails closed;
9. empty authorized Organization is distinct from unauthorized/service failure;
10. the supporting Organization/sort-key index exists after migration;
11. finish with:

```text
PROFESSIONAL INVENTORY OVERVIEW RESULT -> PASS
```

CI must execute the retained proof in the normal PostgreSQL/web integration path.

## 16. Explicitly deferred

Not part of v0.1 / SLICE-0060:

- listing create/intake;
- listing edit;
- publish/withdraw/reconfirm controls;
- pre-market professional draft model;
- client-side draft recovery/autosave;
- media;
- broker profile/logo/branding completion;
- leads/contact/CRM;
- sale/outcome workflow;
- analytics/reporting;
- Search-fit/exclusion/demand insight;
- bulk import/export;
- payments/entitlements;
- owner-direct publication;
- buyer account persistence;
- Saved Search/monitor/alerts;
- third Search criterion.

## 17. Acceptance summary

Accepted v0.1 boundary:

```text
current authenticated Account
→ current explicit Organization authorization
→ Organization-owned NativeListing projection
→ current lifecycle + offer + freshness + public-link facts
→ private factual inventory overview
→ no writes / no new persistence
```
