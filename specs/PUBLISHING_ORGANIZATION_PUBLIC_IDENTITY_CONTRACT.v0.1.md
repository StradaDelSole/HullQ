# HullQ Publishing Organization Public Identity Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Owning slice:** SLICE-0063 — Publishing Organization Public Identity  
**Broker requirement:** REQ-BROKER-023  
**Depends on:** accepted MarketplaceOrganization actor directory; public NativeListing read boundary; Broker Workspace authorization boundary  
**Normative language:** BCP 14 semantics apply to uppercase MUST/SHOULD/MAY.

## 1. Purpose

This contract defines exactly one capability:

> the existing authoritative publishing MarketplaceOrganization has a bounded human-readable public display identity that is visible consistently in the authorized Broker Workspace and on every public NativeListing, independent of optional listing claims.

It does not create a second Organization entity, a broker profile product, media upload, logo asset management or Organization self-service administration.

## 2. Identity boundary

The stable professional publishing identity remains:

```text
MarketplaceOrganizationId
```

Hard:

```text
public_display_name != Organization ID
public_display_name != verified legal identity
public_display_name != Brand/Marque identity
```

The display name is mutable presentation metadata on the same existing MarketplaceOrganization principal.

Changing it MUST NOT:

- change `MarketplaceOrganizationId`;
- change NativeListing IDs or canonical URLs;
- change listing ownership;
- mutate NativeListing immutable creation content;
- create an offer revision;
- change lifecycle/freshness;
- change Search eligibility/ranking;
- imply legal/KYB verification.

## 3. Persistence

The existing `marketplace_organizations` row MUST carry one bounded non-empty:

```text
public_display_name
```

No second publisher identity table is authorized.

### 3.1 Migration

Existing rows MUST receive a deterministic local backfill without network/external lookup.

Accepted compatibility backfill:

```text
public_display_name = organization_id
```

The resulting persisted value MUST be non-empty.

The schema SHOULD enforce bounded non-empty data at the persistence boundary.

### 3.2 Internal provisioning

Existing internal/test Organization provisioning MUST support an explicit human-readable display name.

No public Organization-profile edit API is authorized by this slice.

## 4. Display-name validation

v0.1 MUST:

- accept ordinary Unicode broker/Organization names;
- preserve meaningful punctuation and corporate suffixes;
- reject empty/whitespace-only values;
- enforce a bounded maximum length;
- reject control-character input that cannot be safely presented;
- treat the value as plain text, never trusted HTML.

The implementation MAY trim leading/trailing whitespace at the write boundary, but MUST NOT normalize away legitimate internal punctuation, capitalization or corporate suffixes merely for branding aesthetics.

## 5. Public NativeListing identity projection

For every readable public NativeListing, FastAPI MUST expose explicit publishing Organization identity independent of VAT/tax or other optional claim presence.

Required facts:

```text
publishing_organization_id
publishing_organization_display_name
```

A nested equivalent is acceptable.

The ID is authoritative identity. The display name is current presentation metadata.

## 6. Actor-directory resolution

When the listing's `publishing_organization_id` resolves to a current `marketplace_organizations` row:

```text
display_name = current public_display_name
```

Public listing reads MAY reflect a later Organization display-name change without mutating the NativeListing itself.

This is expected: publisher presentation metadata is not immutable listing truth.

## 7. Legacy/unresolved Organization compatibility

Historical/synthetic NativeListings may carry accepted publishing Organization IDs that predate the actor directory and have no corresponding `marketplace_organizations` row.

0063 MUST NOT turn such an otherwise-readable listing into not-found solely because display metadata is missing.

For that case:

```text
display_name = publishing_organization_id
```

is the accepted bounded compatibility fallback.

The API MUST still expose the exact authoritative publishing Organization ID.

## 8. Public web behavior

The public listing page MUST visibly render the publishing Organization identity for every successfully rendered public listing.

Hard:

- rendering MUST NOT depend on VAT/tax claim presence;
- rendering MUST NOT depend on PhysicalBoat claims;
- display name MUST be rendered as text/escaped content;
- display name MUST NOT participate in the NativeListing canonical URL;
- display name changes MUST NOT create redirect/slug behavior;
- page remains deliberately noindex under the accepted 0049 SEO contract.

Minimum presentation:

```text
Listed by {publishing_organization_display_name}
```

Equivalent clear wording is allowed.

Opaque Organization ID MAY also be shown, but MUST NOT be the only normal human-facing identity when a real display name is available.

## 9. Broker Workspace behavior

Authorized Broker Workspace Organization choices/context MUST expose the current Organization display name.

Authorization remains exclusively based on:

```text
current authenticated Account
+ exact Organization ID
+ current Membership / roles / MFA
```

Display name MUST NOT be accepted from a client as an authorization selector.

The stable Organization ID SHOULD remain visible where operationally useful.

## 10. Branding preservation

REQ-BROKER-023 prohibits deliberately erasing legitimate broker branding merely to make HullQ appear unbranded.

For v0.1:

- Organization display-name branding MUST be preserved as plain text;
- legitimate punctuation/corporate suffixes MUST NOT be intentionally stripped;
- HTML/script input MUST remain inert/escaped;
- HullQ MUST NOT replace a specific available publisher identity with a generic "Broker" label.

There is currently no accepted listing-media upload/transformation pipeline in HullQ. This slice MUST NOT invent one.

Future media implementation remains bound by:

> compliant broker-provided logos/watermarks are not removed solely because they are broker branding; rights, security, privacy, quarantine, EXIF-removal and accepted media normalization may still transform/reject media for their own legitimate reasons.

## 11. Non-enumeration / privacy

Broker Workspace authorization behavior remains unchanged.

A user MUST NOT gain access to Organization context merely by knowing a display name.

No public Organization directory/search endpoint is introduced.

The public listing exposes only the publisher identity already attached to an accepted public listing plus its bounded current display label.

## 12. Security

Display-name values:

- MUST be treated as untrusted plain text;
- MUST be safely escaped in Astro;
- MUST NOT be injected through `set:html` or equivalent raw HTML;
- MUST NOT carry session/auth/MFA data;
- MUST NOT alter CSP/CORS/session boundaries.

## 13. Tests

At minimum cover:

### Persistence

- migration/backfill gives every existing MarketplaceOrganization row a non-empty display name;
- explicit human-readable display name persists/re-reads exactly within accepted normalization;
- empty/whitespace-only/control-character/over-limit input is rejected;
- Organization ID/category/eligibility semantics remain unchanged.

### Broker Workspace

- broker context includes display name for current authorized Organization;
- multiple Organizations retain their own names;
- unauthorized/foreign Organization behavior remains non-enumerating;
- display name is never used as the authorization key.

### Public listing API

- current actor-directory display name is returned;
- public identity is returned whether VAT claim is present or absent;
- actor-directory display-name change is reflected without NativeListing mutation;
- unresolved legacy Organization falls back to exact Organization ID;
- DRAFT/WITHDRAWN/stale/missing/incomplete behavior remains unchanged.

### Web

- public ACTIVE page visibly renders publisher display name outside optional VAT block;
- malicious HTML/script-like display name renders inert/escaped;
- page remains self-canonical/noindex;
- broker workspace visibly renders current Organization display name;
- no direct DB access in Astro.

### Non-regression

- publishing eligibility unchanged;
- NativeListing immutable content/hash/idempotency unchanged;
- professional draft ownership/recovery unchanged;
- Search result semantics unchanged.

## 14. Retained proof

Required retained real PostgreSQL 18 + FastAPI + built Astro proof MUST demonstrate at least:

1. migrate/seed an eligible MarketplaceOrganization with a human-readable display name;
2. render an authorized Broker Workspace Organization surface and verify that name;
3. create/reuse a public ACTIVE current listing for that Organization;
4. omit VAT/tax claim in at least one representative case;
5. fetch FastAPI public listing and prove exact Organization ID + display name;
6. fetch built Astro public listing and prove the display name is visibly rendered despite absent VAT claim;
7. use a safe malicious-text fixture and prove it is escaped/inert;
8. update only the Organization display name;
9. prove the same NativeListing ID/URL now renders the new display name with no listing mutation/lifecycle transition/offer revision;
10. prove a legacy/unresolved publishing Organization ID remains publicly readable and uses exact ID fallback;
11. prove DRAFT/WITHDRAWN/stale/unknown public-read behavior remains unchanged.

## 15. Governance effect

Before acceptance:

```text
REQ_BROKER_023_STATUS = PENDING
```

Only after exact-head review, required gates, explicit Project Owner acceptance and canonical acceptance closure may the register advance to:

```text
REQ_BROKER_023_STATUS = IMPLEMENTED
```

This status means HullQ has implemented explicit publishing Organization identity and current textual branding preservation.

It does not mean media upload/logo asset management exists. Future media work MUST preserve the no-branding-erasure invariant.

The Broker Workspace Launch Gate remains `NOT_READY` until all other applicable gate evidence is complete.

## 16. Explicitly deferred

Not part of SLICE-0063:

- logo upload/storage;
- media/gallery pipeline;
- broker watermark transformation;
- public broker profile page;
- Organization slug;
- self-service profile editing;
- legal-name verification/KYB;
- website/contact/social fields;
- office hierarchy;
- draft promotion/publication;
- leads/CRM;
- analytics;
- payments;
- Search changes;
- SEO/indexation expansion;
- production pilot/launch.

## 17. Acceptance summary

Accepted v0.1 boundary:

```text
existing MarketplaceOrganizationId
+ bounded current public_display_name
→ clear current publisher identity in Broker Workspace
→ clear current publisher identity on every public NativeListing
→ no dependency on optional VAT/listing claims
→ no second Organization identity
→ no marketplace/listing/Search truth mutation
```
